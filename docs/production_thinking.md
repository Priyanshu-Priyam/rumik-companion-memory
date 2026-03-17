# Production Thinking

This covers how the memory-augmented companion system would behave in production, with real users, real latency budgets, and real privacy requirements.

---

## Latency

**Current system budget** (per message):

| Stage | Expected p50 | Expected p95 | Notes |
|---|---|---|---|
| Extraction (write phase) | 300ms | 600ms | Single LLM call to parse user message for facts |
| Memory store write | 5ms | 15ms | SQLite insert/update |
| Vector store write | 20ms | 50ms | ChromaDB upsert |
| Hybrid retrieval | 25ms | 60ms | SQLite keyword + ChromaDB ANN in parallel |
| Ranking | 2ms | 5ms | In-memory scoring |
| Policy application | <1ms | <1ms | Pure logic, no I/O |
| Prompt construction | <1ms | <1ms | String formatting |
| Response generation | 500ms | 1200ms | LLM generation call |
| **Total** | **~850ms** | **~1900ms** | |

The extraction call is the critical latency concern. In production, two strategies:

1. **Fire-and-forget extraction**: Run extraction asynchronously after sending the response. The user gets a reply in ~500ms, and the memory update happens in the background. The next turn picks it up. This trades one-turn-delayed memory for halved latency.

2. **Batch extraction**: Extract facts from the last N turns every K messages rather than every turn. Reduces LLM calls by 60-80% while keeping memory fresh enough for most use cases.

For the read path (retrieval → generation), the bottleneck is the single LLM generation call. ChromaDB retrieval at <100K facts per user is sub-50ms. SQLite queries are sub-10ms. The system is I/O-bound on LLM inference, not on memory operations.

---

## Cost

**Per-message cost breakdown** (Claude Sonnet at current Bedrock pricing):

| Component | Input tokens (est.) | Output tokens (est.) | Cost per message |
|---|---|---|---|
| Extraction call | ~800 | ~200 | ~$0.004 |
| Response generation | ~1500 (prompt + history + facts) | ~300 | ~$0.008 |
| LLM judge (eval only) | ~1200 | ~150 | ~$0.005 |
| **Total per message** | | | **~$0.012** |

At 50 messages/day per active user: ~$0.60/user/day, ~$18/user/month.

**Cost reduction levers**:

- **Smaller model for extraction**: Use Haiku for fact extraction (simpler structured output task), Sonnet for generation. Saves ~60% on extraction costs.
- **Caching**: Cache the system prompt skeleton and user fact block. Bedrock prompt caching can reduce input token costs by 80% for repeated prompt prefixes.
- **Async extraction batching**: Extract every 3-5 turns instead of every turn. Saves 60-80% on extraction costs.
- **Tiered generation**: Use Haiku for simple acknowledgments ("accha", "okay"), Sonnet for complex queries requiring memory recall. An intent classifier (also Haiku) routes messages. Potential 40-50% overall cost reduction.

---

## Scale

**Per-user storage**:

| Store | Size per user (1K facts) | Notes |
|---|---|---|
| SQLite (facts + entities) | ~100KB | Grows linearly with fact count |
| ChromaDB (embeddings) | ~4MB | 384-dim embeddings, grows linearly |
| Conversation history (if stored) | ~500KB/month | At 50 messages/day |

**Scaling architecture**:

- **SQLite → PostgreSQL**: At ~10K users, migrate from per-user SQLite files to a shared PostgreSQL instance with user_id partitioning. The schema is already designed for this — every query is scoped by `user_id`.
- **ChromaDB → Managed vector DB**: At scale, move to Pinecone, Weaviate, or pgvector (to stay in PostgreSQL). Namespace per user. The `VectorStore` abstraction already supports this swap — it exposes `add_fact`, `query`, `remove_user`.
- **Horizontal scaling**: The memory pipeline is stateless per-request (reads from DB, writes to DB). Multiple API servers can serve requests concurrently. The only coordination needed is write-before-read ordering within a single user's message processing.
- **Rate limiting**: Per-user rate limits prevent abuse. Token counting (already implemented via tiktoken) enables per-user cost caps.

---

## Observability

**What to monitor**:

1. **Retrieval quality metrics**:
   - Average retrieval score per query (trending down = embedding drift or fact staleness)
   - Number of facts retrieved vs. facts used in response (high ratio = retrieval is noisy)
   - Queries with zero retrievals (potential memory gaps)

2. **Memory health metrics**:
   - Facts per user (distribution, growth rate)
   - Correction chain length (long chains = confused memory)
   - Stale fact ratio (facts with `valid_until` in the past that haven't been cleaned up)
   - Extraction failure rate (LLM returns unparseable JSON)

3. **Response quality signals**:
   - User satisfaction proxies: message length trending down, session length trending down, explicit negative feedback
   - Fabrication detection: flag responses where the LLM mentions facts not in the retrieved set (post-hoc audit)
   - Sensitivity leak audit: log when high/intimate facts appear in responses

4. **System health**:
   - LLM call latency (p50, p95, p99)
   - Bedrock throttle/retry rates
   - Memory store write latency
   - Error rates per pipeline stage

**Implementation**: Each pipeline stage in `ImprovedEngine.chat()` already returns structured debug data (retrieved facts, extractions, manager actions, withheld count). In production, this would feed into a structured logging pipeline (e.g., CloudWatch Structured Logs or Datadog) with dashboards for the metrics above.

---

## Rollback Strategy

**What can go wrong and how to recover**:

1. **Bad extraction model update**: A new extraction model starts misinterpreting facts (e.g., marking corrections as new facts).
   - **Detection**: Monitor correction chain creation rate. Sudden spike = extraction regression.
   - **Rollback**: The extraction model is specified by `model_id` in config. Revert to previous model ID. Facts extracted by the bad model can be identified by `conversation_id` range and cleaned up.

2. **Corrupted fact store**: A bug writes malformed facts or breaks supersession chains.
   - **Detection**: Integrity checks on supersession chains (no cycles, all referenced facts exist).
   - **Rollback**: Every fact has a `created_at` timestamp. Facts created after the corruption event can be reverted. The SQLite WAL (write-ahead log) provides point-in-time recovery for recent corruption.

3. **Policy regression**: A prompt change causes the companion to leak sensitive information.
   - **Detection**: Post-hoc audit comparing responses against sensitive fact set.
   - **Rollback**: Prompt templates are versioned. Revert to previous template. The policy layer is pure code (no learned parameters), so rollback is instantaneous.

4. **Full system rollback**: Brain B is performing worse than Brain A in production.
   - **Strategy**: The `CompanionBrain` interface allows hot-swapping between Brain A and Brain B per user. A/B testing with gradual rollout. If Brain B regresses, switch affected users back to Brain A without data loss — Brain A doesn't use the structured memory store, so it's independent.

---

## Privacy and Deletion

**Data stored per user**:

- Entities (name, aliases, type) — in SQLite, partitioned by `user_id`
- Facts (predicates, values, metadata) — in SQLite, partitioned by `user_id`
- Fact embeddings — in ChromaDB, filtered by `user_id` metadata
- Conversation history — in session state (not persisted in current implementation)

**Deletion implementation** (already built):

```python
# Full user deletion — single call
brain.reset(user_id="rohan")

# This calls:
# 1. MemoryStore.clear_user(user_id) → DELETE FROM facts/entities WHERE user_id = ?
# 2. VectorStore.remove_user(user_id) → ChromaDB delete with user_id filter
```

Both stores support complete, immediate deletion by `user_id`. No orphaned embeddings, no leftover fact references.

**Privacy principles**:

1. **User isolation is architectural**: Every query, every write, every retrieval is scoped by `user_id`. There is no code path that can access another user's data. This is enforced at the storage layer (SQL WHERE clauses, ChromaDB metadata filters), not just the application layer.

2. **Sensitivity is metadata**: Facts have a `sensitivity` field (`none`, `moderate`, `high`, `intimate`) that controls disclosure policy. This is separate from storage — sensitive facts are stored (the user shared them and wants the companion to remember) but gated from unprompted disclosure.

3. **No training on user data**: The system uses a frozen LLM via API. User facts are never sent to model fine-tuning. They appear only in per-request prompts and are not retained by the LLM provider beyond the request.

4. **Audit trail**: Every fact has `conversation_id`, `created_at`, and `source` (user_stated vs inferred). A user can request an export of all stored facts about them, trace each fact to the conversation where it was extracted, and request selective deletion.

5. **Right to be forgotten**: The `reset()` method provides full deletion. For selective deletion ("forget that I told you about X"), the memory manager can mark specific facts as `retracted` (soft delete) or permanently remove them (hard delete). The current implementation supports both.
