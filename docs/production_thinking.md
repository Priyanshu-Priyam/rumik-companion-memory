# Production Thinking



## latency

every message in Brain B goes through: extraction → write to store → retrieve → rank → build prompt → generate. two LLM calls (extraction + generation), two DB operations (SQLite + ChromaDB). the current p50 budget looks like this:

| stage | p50 | p95 | notes |
|---|---|---|---|
| extraction (write phase) | 300ms | 600ms | single LLM call |
| memory store write | 5ms | 15ms | SQLite insert/update |
| vector store write | 20ms | 50ms | ChromaDB upsert |
| hybrid retrieval | 25ms | 60ms | SQLite + ChromaDB in parallel |
| ranking | 2ms | 5ms | in-memory scoring |
| policy application | <1ms | <1ms | pure logic |
| prompt construction | <1ms | <1ms | string formatting |
| response generation | 500ms | 1200ms | LLM generation call |
| **total** | **~850ms** | **~1900ms** | |

the extraction call is the latency problem. it adds 300-600ms to every turn — and most messages don't contain new facts worth extracting. someone saying "haha sahi bol raha hai" doesn't need a fact extraction call. the extraction budget is being spent on turns that return empty arrays.

two practical fixes:

**fire-and-forget extraction** — send the response first, run extraction asynchronously. user gets a reply in ~500ms. memory updates land before the next turn. the cost is one-turn-delayed memory for anything important said in the current message. acceptable for most conversations, not acceptable if the user just shared something they expect to be recalled in the same turn.

**selective extraction** — run a cheap intent classifier first (a single Haiku call). 
if the message looks like a factual disclosure, extract. if it looks like a reaction or filler, skip. this cuts extraction calls by 60-70% without meaningful memory loss.

for the read path, the bottleneck is the generation call. ChromaDB retrieval at <100K facts per user is sub-50ms. SQLite queries are sub-10ms. the system is LLM-inference-bound, not memory-bound. that changes when the fact DAG ships — graph traversal over a large fact store adds meaningful DB time — but at current scale it's not the constraint.

---

## cost

every message runs two LLM calls. at Bedrock Sonnet pricing:

| component | input tokens (est.) | output tokens (est.) | cost per message |
|---|---|---|---|
| extraction call | ~800 | ~200 | ~$0.004 |
| response generation | ~1500 | ~300 | ~$0.008 |
| **total per message** | | | **~$0.012** |

at 50 messages/day per active user, that's ~$0.60/user/day, ~$18/user/month. that's a lot for a companion app where the value proposition is daily engagement over months.

the levers:

**model tiering** — use Haiku for extraction (structured output task, doesn't need Sonnet's reasoning quality) and Sonnet for generation. Haiku costs ~5x less. extraction is ~30% of total cost. switching extraction to Haiku cuts that slice by ~80%, reducing total cost by ~25%.

**prompt caching** — the system prompt is mostly stable across turns for a given user: persona instructions + memory block. Bedrock prompt caching reduces input token costs by 80% for repeated prompt prefixes. the companion persona and static memory block are the perfect candidates. the only dynamic part is the retrieved facts for each turn, which is a small fraction of the full prompt.

**tiered generation** — route simple responses (acknowledgments, one-word reactions, "accha okay") to Haiku and complex memory-recall or correction queries to Sonnet. an intent classifier (another Haiku call) adds ~$0.001 but saves ~$0.006 on generation for the 40-50% of turns that are simple. net saving: ~25-30% on generation costs.

**batched extraction** — extract every 3-5 turns instead of every turn. memory freshness drops slightly but cost drops significantly. most conversational exchanges across 3 turns produce 0-1 new facts anyway.

combined, these bring cost down to ~$5-8/user/month — roughly in line with what a consumer companion product can support at mid-tier pricing.

---

## scale

the current stack (SQLite + ChromaDB on local disk) is intentionally simple. it's the right choice for a prototype and a submission. but the migration path matters.

**per-user storage** at 1K facts:
- SQLite (facts + entities): ~100KB
- ChromaDB (384-dim embeddings): ~4MB
- grows linearly with fact count

the schema was built for this migration. every table has `user_id` as a partition key. every query is scoped by `user_id`. moving to PostgreSQL at ~10K users is a schema-compatible migration — no application code changes, just a connection string swap and an index on `user_id`. the `MemoryStore` abstraction already handles this.

ChromaDB → managed vector DB (Pinecone, Weaviate, or pgvector if staying in PostgreSQL) is also a clean swap. the `VectorStore` class exposes `add_fact`, `query`, `remove_user`. the internals are hidden. at scale, you swap the implementation, not the interface.

horizontal scaling is straightforward. the memory pipeline is stateless per-request — it reads from DB, writes to DB, and produces a response. multiple API servers can serve concurrent requests without coordination. the only constraint is write-before-read ordering within a single user's message: extraction must settle before retrieval serves the response. that's enforced within the request lifecycle, not across servers.

the fact DAG (the branching model from the architecture doc) adds one consideration at scale: graph traversal queries become more expensive as the fact graph grows deep. the `fact_edges` table will need indexes on `from_fact_id` and `to_fact_id`, and traversal depth should be bounded. not a blocking problem — just something to plan for when the DAG ships.

---

## observability

the debug data is already there. every message through Brain B returns a structured dict: extracted facts, extraction errors, retrieval scores, manager actions, withheld count, policy decisions, system prompt. in production, this feeds a structured logging pipeline.

what i'd monitor:

**retrieval health** — average retrieval score per query (trending down = embedding drift or fact staleness), facts retrieved vs facts the LLM actually references in the response (high ratio = noisy retrieval), queries returning zero facts (potential memory gaps). retrieval is the first place things go wrong silently.

**memory health** — facts per user (distribution + growth rate), correction chain length (long chains signal confused memory — a user who's been correcting the same fact repeatedly has a problem we haven't solved), stale fact ratio (facts past `valid_until` that haven't been cleaned up), extraction failure rate (LLM returned unparseable JSON).

**response quality signals** — session length trending down is the canary. users who find the companion useful come back. users who feel unheard or gaslighted drop off. explicit negative feedback ("ye galat hai," "tune mujhe yeh kabhi nahi bola") is the clearest signal, but it requires the companion to recognize and log it. fabrication audit — flag responses where the LLM mentions something not in the retrieved fact set — catches the hardest failures that users might not explicitly complain about.

**sensitivity audit** — log when high or intimate facts appear in responses, tagged with whether the user explicitly asked for them. this is the one observability gap that has regulatory implications, not just product implications.

---

## rollback

four things that can go wrong in production, and how to recover:

**bad extraction model update** — a new model version starts misinterpreting facts. corrections are stored as new facts, creating contradictory states. detection: monitor correction chain creation rate. sudden spike = extraction regression. rollback: `BEDROCK_MODEL_ID` is a config value. revert it. facts extracted by the bad model are identifiable by `conversation_id` range and can be cleaned up or soft-deleted.

**corrupted fact store** — a bug writes malformed facts or breaks supersession chains. detection: integrity checks on supersession chains (no cycles, all referenced facts exist). these can run as a background job. rollback: every fact has `created_at`. facts after the corruption event can be reverted. SQLite's write-ahead log provides point-in-time recovery for recent windows.

**policy regression** — a prompt change causes sensitive information to surface unprompted. detection: post-hoc audit comparing responses against the user's sensitive fact set. rollback: prompt templates are versioned in the codebase. revert the commit. the policy layer is pure code with no learned parameters — rollback is instantaneous.

**brain regression** — Brain B performs worse than Brain A for a cohort of users. the `CompanionBrain` interface was built for exactly this. A/B testing is structural: both brains are registered, traffic splits by user ID, rollback is a config change. Brain A doesn't use the structured memory store, so switching back doesn't corrupt anything. the stores persist for when Brain B resumes.

---

## privacy and deletion

the data we store per user: entities (name, type, aliases), facts (predicates, values, full metadata), fact embeddings. no conversation transcripts — those exist in session state and aren't persisted.

full deletion is a single call:

```python
brain.reset(user_id="rohan")
# DELETE FROM facts/entities WHERE user_id = ?
# ChromaDB delete with user_id metadata filter
```

both stores support immediate, complete deletion. no orphaned embeddings, no leftover fact references. this is a design constraint i kept from the start — multi-user isolation has to be architectural, not just a filter. it means deletion is clean by construction.

five principles i held to:

**isolation is structural** — every query, every write, every retrieval is scoped by `user_id` at the storage layer. SQL WHERE clauses, ChromaDB metadata filters. there is no code path that can access another user's data. a bug in the application layer can't produce a cross-user leak because the store won't return it.

**sensitivity is metadata, not exclusion** — sensitive facts are stored. the user shared them and wants to be known. the sensitivity field (`none`, `moderate`, `high`, `intimate`) controls disclosure policy at retrieval time, not storage time. storing the fact but gating its disclosure is the correct model. deleting it means the companion forgets something the user chose to share, which is its own kind of failure.

**no training on user data** — the system uses a frozen LLM via API. user facts appear only in per-request prompts. they are not retained by the model provider beyond the request window and are never used for fine-tuning.

**audit trail** — every fact has `conversation_id`, `created_at`, and `source`. a user can ask: what do you know about me, where did you learn it, when. each fact traces to the turn where it was extracted. selective deletion — "forget that i told you about X" — is a `status = retracted` update on specific fact IDs, not a full reset.

**right to be forgotten** — `reset()` is full deletion. selective deletion is soft (`retracted`) or hard (`DELETE`). both are implemented. if a user says "forget everything," it's immediate. if they say "forget what i said about my weight," the extractor identifies the predicate, the manager retracts the relevant facts, and the next turn acts as if that information was never shared.

---

##

the system as built is not production-ready. it's production-shaped. the data model is right. the isolation guarantees are real. the deletion story is clean. the migration path to PostgreSQL and a managed vector store is clear and low-risk.

what it's missing for actual production: fire-and-forget extraction, model tiering, prompt caching, a proper observability pipeline, and the fact DAG for retrieval quality at scale. none of these are architectural rewrites. they're the next layer on top of a foundation that was built to support them.


