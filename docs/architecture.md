# Architecture: Memory System Design

## Overview

This document describes the memory system architecture for an Ira-like AI companion. The design addresses eight distinct memory types, defines a two-table storage model (Entities + Facts), and implements a two-phase message processing pipeline (Write then Read).

---

## Memory Types

The assignment requires distinguishing between eight memory types. Our architecture maps each to a combination of `source`, `status`, `sensitivity`, and `memory_form` fields on the Fact model:

| Memory Type | Implementation |
|---|---|
| **User-stated facts** | `source = user_stated` |
| **Inferred facts** | `source = inferred` |
| **Guessed facts** | `source = guessed`, `confidence < 0.5` |
| **Corrected facts** | `status = corrected`, `supersedes` points to replacement |
| **Stale facts** | `status = stale`, `valid_until` set |
| **Sensitive facts** | `sensitivity ∈ {moderate, high, intimate}` |
| **Atomic facts** | `memory_form = atomic` |
| **Summaries** | `memory_form = summary` |

This approach avoids creating separate tables or schemas per type. A single `Fact` record carries all the metadata needed to distinguish any combination.

---

## Data Model

### Entities Table

Entities are the **nodes** in the user's knowledge graph — people, pets, places, organizations.

```sql
CREATE TABLE entities (
    entity_id       TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    entity_type     TEXT DEFAULT 'unknown',
    aliases         TEXT,   -- JSON array
    created_at      TIMESTAMP NOT NULL
);
```

### Facts Table

Facts are **reified triples** — subject-predicate-object with rich metadata.

```sql
CREATE TABLE facts (
    fact_id         TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    entity_id       TEXT REFERENCES entities(entity_id),
    predicate       TEXT NOT NULL,
    value           TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'user_stated',
    status          TEXT NOT NULL DEFAULT 'current',
    confidence      REAL NOT NULL DEFAULT 1.0,
    sensitivity     TEXT NOT NULL DEFAULT 'none',
    memory_form     TEXT NOT NULL DEFAULT 'atomic',
    supersedes      TEXT REFERENCES facts(fact_id),
    valid_from      TIMESTAMP,
    valid_until     TIMESTAMP,
    context_summary TEXT,
    conversation_id TEXT,
    created_at      TIMESTAMP NOT NULL
);
```

Key design decisions:

- **`supersedes`** creates a linked chain for correction history (Rocky → Daredevil)
- **`valid_from` / `valid_until`** handles temporal facts without separate tables
- **`user_id`** on every record enforces multi-user isolation at the data level
- **`status`** (`current` / `stale` / `corrected` / `retracted`) tracks lifecycle

---

## What Gets Stored vs. What Does Not

### Stored
- Explicit user statements ("mera naam Rohan hai")
- Entity relationships ("Divya meri girlfriend hai")
- Corrections with full supersession chain
- Temporal values with validity windows
- Emotional context summaries
- Sensitivity classifications

### Not Stored
- Exact conversation transcripts (too much data, summarize instead)
- System-internal reasoning traces
- Live timestamps or real-world clock values
- Anything the user explicitly asks to forget

---

## How Updates Happen

### New Fact
Create entity (if needed) → Create fact with `status=current`.

### Correction
1. Find existing fact matching the entity + predicate
2. Set old fact `status = corrected`
3. Create new fact with `supersedes` pointing to old fact
4. For entity disambiguation (Spark rat→hamster, new entity Pixel=rat): update existing entity + create new entity + create new fact

### Temporal Update
1. Set old fact `valid_until = now`, `status = stale`
2. Create new fact with `valid_from = now`
3. Historical values remain queryable (weight was 110, then 92, now 88)

### Retraction
User says "maine nahi kaha tha ki mujhe cooking pasand hai" → Set fact `status = retracted`.

---

## How Contradictions Are Resolved

1. **Same-message contradiction**: Last mention wins ("mera fav color blue hai... nahi nahi, green hai" → green)
2. **Cross-message correction**: Explicit correction creates supersession chain
3. **Source-weighted**: `user_stated` overrides `inferred` overrides `guessed`
4. **Recency-weighted**: More recent `user_stated` facts override older ones of the same predicate

---

## How Retrieval Is Ranked

Hybrid retrieval combines structured lookup (SQLite) with semantic search (ChromaDB):

```
score = relevance × 0.4 + recency × 0.3 + confidence × 0.2 + source_weight × 0.1
```

Where:
- **relevance**: semantic similarity to user's query (0-1)
- **recency**: time decay function on `created_at`
- **confidence**: the fact's confidence score
- **source_weight**: `user_stated=1.0`, `inferred=0.7`, `guessed=0.3`

All retrieval is filtered by `user_id` (isolation) and `status = current` (freshness).

---

## How Sensitive Memory Is Gated

Four sensitivity levels with corresponding disclosure strategies:

| Level | Strategy | Example |
|---|---|---|
| `none` | Recall directly | "Tera hamster Spark hai na?" |
| `moderate` | Recall if relevant | Weight journey mentioned when user brings up fitness |
| `high` | Summarize, don't dump | "Haan tune kuch personal cheezein share ki thi" |
| `intimate` | Ask before revealing | Self-harm history — only recall if user explicitly asks |

The sensitivity policy runs after retrieval and before response generation. It filters or reframes facts based on:
1. The sensitivity level of the fact
2. Whether the user explicitly asked about it
3. The emotional tone of the current conversation

---

## 10-Stage Pipeline

```
Message In
    │
    ├── WRITE PHASE ──────────────────────┐
    │   1. Ingestion (parse message)      │
    │   2. Extraction (identify facts)     │
    │   3. Validation (check conflicts)    │
    │   4. Storage (write to DB)           │
    │                                      │
    ├── READ PHASE ───────────────────────┤
    │   5. Retrieval (query relevant)      │
    │   6. Ranking (score + sort)          │
    │   7. Response Planning (what to say) │
    │   8. Generation (produce text)       │
    │                                      │
    ├── POLICIES ─────────────────────────┤
    │   9. Uncertainty Policy              │
    │  10. Sensitive Memory Policy         │
    │                                      │
    └─────────────────────────────────────┘
        │
    Response Out
```

**Critical ordering**: Writes settle before reads. If the user says "Divya ab meri girlfriend hai, uske baare mein bata" — the correction must be stored before retrieval serves the response. This prevents stale data in mixed store-and-query messages.

---

## Anti-Patterns Avoided

| Anti-Pattern | Why It Fails | Our Approach |
|---|---|---|
| Latest Wins (overwrite) | Loses history, can't answer "pehle kya tha?" | Supersession chain |
| Flat Retrieval | No ranking = irrelevant facts flood context | Weighted hybrid ranking |
| Eager Merge | Combines separate entities prematurely | Explicit entity disambiguation |
| Uniform Sensitivity | All facts treated the same | 4-level gating policy |
| Context-Free Facts | Facts without origin lose meaning | `context_summary`, `conversation_id` |
| Schema-Per-Type | Explosion of tables/schemas | Single Fact table with metadata |
