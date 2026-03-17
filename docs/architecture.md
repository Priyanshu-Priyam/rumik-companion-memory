# Memory System Design

## where the idea started

before writing any code, i sat with the question: what does a companion actually remember?

my first instinct was that everything is a person. not "person" in the human sense — person as in a node in someone's life that they have an internal relationship with. your dog is a person. your hamster is a person. your school friend, your girlfriend, your city. each one is a P — P1, P2, P(n) — and each one carries the same kind of structure because they're all building blocks of the same thing: someone's life.

i split each P into two halves. internal relationships — things that belong to the entity itself. a user's name, their religion, where they live, their weight. and external relationships — connections between entities. "Divya is my girlfriend," "Gagan works at Marriott," "Spark is my hamster." each relationship type, whether internal or external, carries its own feature set. an internal relationship like "user name" has properties: who gave it, has it always been the same, what's the current value. an external relationship like "Divya is my girlfriend" has: when did it start, what's the nature of it, what's the maturity status.

and then on top of all this, every relationship has an evolution graph — a trace of how it changed over time, a summary of transitions with reasons. Divya went from crush to girlfriend. weight went from 110 to 92 to 88. Rocky was the nickname, now it's Daredevil. the evolution graph preserves the full story.

i also thought about the CRUD ordering — what happens when a message comes in? listen, read, update, decide, check status, write, fetch? maybe a loop that runs until all operations settle, like how cursor calls subagents. this felt like the most complex part.

## where the idea broke

the internal/external split looked elegant on paper. but when i started mapping real examples to it, i realized the distinction doesn't carry meaningful utility at the scale i'm building.

consider: "mera naam Rohan hai" and "Divya meri girlfriend hai." one is internal (self-attribute), one is external (relationship). but operationally, they're the same thing — a predicate-value pair attached to an entity, with metadata about source, confidence, time, and sensitivity. the internal/external taxonomy creates a hierarchy that the system then has to navigate for every operation, but it doesn't change what the system actually *does* with the information. both get stored, both get retrieved, both get corrected the same way.

the evolution graph idea was good but also over-structured. tracking "Divya: crush → girlfriend, reason: user explicitly corrected" as a first-class graph is essentially the same as a chain of fact records where each new one points to the one it replaced. the graph is implicit in the data — you don't need a separate structure for it.

so i collapsed the whole thing. everything is an Entity (the node) and a Fact (the edge, reified with metadata). the internal/external distinction lives in the predicate — `name` vs `girlfriend` — not in the schema. the evolution graph lives in the `supersedes` chain. the feature sets live in the metadata fields. same information, flatter structure, dramatically simpler operations.

the philosophical core survived: everything is a person, every person has the same shape, every fact about every person carries the same kind of metadata. the implementation just got leaner.

---

## the data model

### entities

entities are the nodes. people, pets, places, organizations — anything the user has a relationship with.

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

the `user_id` on every entity means isolation is structural, not a filter. there is no world in which user A's entities leak into user B's queries.

### facts

facts are reified triples — subject-predicate-object, but the object is just the `value` field, and the subject is the `entity_id`. all the nuance lives in the metadata.

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

the fields that matter most:

- **`supersedes`** — this is the evolution graph, flattened into a linked list. Rocky → Daredevil. crush → girlfriend. 110 → 92 → 88. you can walk the chain backwards to reconstruct the full history.
- **`valid_from` / `valid_until`** — temporal awareness without separate tables. "weight was 110 in January, 92 in February, 88 now" is three facts with non-overlapping validity windows.
- **`status`** — `current`, `stale`, `corrected`, `retracted`. the lifecycle of a fact, not just its current value.
- **`sensitivity`** — `none`, `moderate`, `high`, `intimate`. this drives the disclosure policy downstream.
- **`source`** — `user_stated`, `inferred`, `guessed`. a fact the user explicitly said carries more weight than something the system inferred.

---

## the eight memory types

the assignment requires eight distinct memory types. i implement all of them through combinations of fields on a single Fact record, not through separate schemas or tables.

| memory type | how it's encoded |
|---|---|
| user-stated facts | `source = user_stated` |
| inferred facts | `source = inferred` |
| guessed facts | `source = guessed`, `confidence < 0.5` |
| corrected facts | `status = corrected`, `supersedes` points to the replacement |
| stale facts | `status = stale`, `valid_until` is set |
| sensitive facts | `sensitivity ∈ {moderate, high, intimate}` |
| atomic facts | `memory_form = atomic` |
| summaries | `memory_form = summary` |

this means the system never has to ask "what type of memory is this?" as a routing decision. every fact is queryable with the same interface; the metadata tells you how to handle it.

---

## what gets stored, what doesn't

**stored**: explicit user statements, entity relationships, corrections with full supersession chain, temporal values with validity windows, emotional context summaries, sensitivity classifications.

**not stored**: exact conversation transcripts (too much data — summarize instead), system-internal reasoning traces, live timestamps or real-world clock values, anything the user explicitly asks to forget.

the line is: if it helps the companion know the user better, store it. if it's operational noise, don't.

---

## how corrections work

this is the part the assignment cares about most, so i'll walk through the exact mechanics for each of the six cases provided.

**"Rocky school mein tha, ab se Daredevil yaad rakhna"**
find the fact where `entity=self, predicate=nickname, value=Rocky`. set its `status=corrected`. create a new fact: `predicate=nickname, value=Daredevil, supersedes=old_fact_id`. the chain preserves history — Rocky existed, Daredevil replaced it.

**"Divya pehle meri crush thi, but ab meri girlfriend hai"**
find the fact `entity=Divya, predicate=relationship, value=crush`. set `status=corrected`. create new fact: `value=girlfriend, supersedes=old`. both facts remain in the database. if the user later asks "Divya kaun hai?", retrieval returns the current fact. if they ask "Divya pehle kya thi?", the chain is there.

**"Spark hamster hai, mera rat alag hai, uska naam Pixel hai"**
this is entity disambiguation — the hardest correction type. update the existing Spark entity's type from rat to hamster. create a new entity "Pixel" with type=rat. correct the old fact linking Spark to rat. this requires the extractor to understand that one message is making two entity-level changes simultaneously.

**"Mera weight pehle 110 tha, last month 92 tha, aur ab 88 hai"**
three temporal facts. `value=110, valid_until=past, status=stale`. `value=92, valid_from=past, valid_until=recent, status=stale`. `value=88, valid_from=recent, status=current`. retrieval serves only the current value unless the user explicitly asks about history.

**"Pehle shaam ko tea aur burger, ab green tea aur makhana"**
old routine fact: `status=stale`. new routine fact: `status=current`. the user explicitly said "old routine yaad rakh sakti ho" — so the stale fact stays accessible, not retracted.

**"Rakesh pehle captain tha, ab Arjun hai"**
correct Rakesh's role from captain to friend. create or update Arjun's role to captain. Rakesh's old captain fact stays in the chain as history.

---

## how retrieval works

i use hybrid retrieval — SQLite for structured lookup (exact predicate matches, entity resolution) and ChromaDB for semantic search (finding facts relevant to a vague query like "mere doston ke baare mein bata").

the ranking formula:

```
score = relevance × 0.4 + recency × 0.3 + confidence × 0.2 + source_weight × 0.1
```

where:
- **relevance**: cosine similarity from ChromaDB (0-1)
- **recency**: time decay on `created_at`
- **confidence**: the fact's confidence score
- **source_weight**: `user_stated = 1.0`, `inferred = 0.7`, `guessed = 0.3`

all retrieval is filtered by `user_id` and `status = current`. stale and corrected facts are only included when explicitly requested (temporal queries, correction history).

the honest limitation: when the user sends something emotionally vague ("mood off hai"), relevance scores are low for everything, so recency and confidence dominate. everything scores similarly and the retriever returns too much. this is the retrieval dilution problem i document in the failure analysis — it's a known gap that needs a query intent classifier to fix properly.

---

## sensitive memory policy

four levels, four strategies.

| level | strategy | example |
|---|---|---|
| `none` | recall directly | "tera hamster Spark hai na?" |
| `moderate` | recall if contextually relevant | weight journey — mention when user brings up fitness |
| `high` | summarize presence, don't dump details | "haan tune kuch personal cheezein share ki thi" |
| `intimate` | only surface if user explicitly asks | self-harm history, trauma — never volunteer |

the policy runs after retrieval and before response generation. it takes the ranked facts, checks each one's sensitivity against the conversational context, and either passes it through, rewrites it at a higher abstraction level, or drops it entirely. the LLM never sees the raw intimate fact unless the user is explicitly asking about it.

this is one place where the internal/external distinction from my original design almost mattered — you could argue that health-related facts (internal) should have different gating than relationship-conflict facts (external). but in practice, sensitivity is about the *content*, not the *category*. a user's weight journey and a user's breakup story both need the same careful handling.

---

## the pipeline

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

the critical constraint: **writes settle before reads**. if the user says "Divya ab meri girlfriend hai, uske baare mein bata" — the correction must be stored before retrieval serves the response. otherwise the system calls Divya a crush in the same breath the user corrected it. this is the CRUD ordering question i was wrestling with early on — listen, read, update, decide, check, write, fetch — and the answer turned out to be simpler than i expected: write first, then read, then generate.

the extraction step is LLM-powered with a regex fallback. the extractor gets the user message plus recent conversation history, and returns structured JSON — fact type, entity, predicate, value, old value (for corrections), sensitivity level. if the LLM returns empty for a non-trivial message, it retries once. if it still fails, a regex layer catches common patterns like names and cities. this three-layer approach (LLM → retry → regex) exists because i found that extraction is the most fragile step — a single missed extraction means a fact never enters memory, and the companion "forgets" something the user just said.

the uncertainty policy is anti-fabrication. the companion can only reference facts from its memory store or from the active conversation history. if it doesn't know, it says so honestly. "yaar, ye mujhe yaad nahi, bata na?" — not "tell me more about that!"

---

## the limitation of a linear chain — and where this goes next

the supersession chain is a linked list. each fact points to the one it replaced. Rocky → Daredevil. crush → girlfriend. 110 → 92 → 88. it's clean and it works well for simple, sequential corrections.

but a real user's memory isn't a sequence of corrections. it's a web of related, overlapping, context-dependent things that resist being flattened into a single chain.

consider "favorite food." a user might say:
- "mujhe biryani bahut pasand hai" (general preference)
- "ghar pe pasta banata hoon mostly" (home cooking context)
- "jab stressed hota hoon, maggi hi perfect hai" (emotional context)
- "Sunday ko Domino's se order karta hoon" (routine context)

none of these correct each other. they're all simultaneously true. if i store them as a chain — each one superseding the previous — i lose information with every write. the chain tells me the last thing the user said about food, but it doesn't tell me *why* each fact exists or how the facts relate to each other. i've flattened four distinct truths into a sequence.

and there's a second problem. the chain can only say one thing about the relationship between two facts: "this one replaced that one." but facts can be related in more ways than that. a correction is one relationship. a specialization is another ("biryani in general" → "biryani specifically at home"). a contextual variant is another (same predicate, different emotional state). a temporal branch is another (still do both, but one is "now" and one is "used to").

**the data structure is losing information it was built to carry.**

---

## branching: the next build

the insight is simple: **the structure itself should carry meaning**. a linear linked list carries temporal information — this came after that. a branching structure can carry richer relational information — this is a variant of that, this is a specialization of that, these two things coexist rather than compete.

i want to move from a linear supersession chain to a fact DAG (directed acyclic graph). each node is a fact. edges are typed relationships between facts. the type of edge carries the semantic meaning.

```
                    [food: biryani]          ← general preference node
                    /              \
  [food: biryani @ home]    [food: biryani @ restaurant]   ← contextual branches
                                    |
                    [food: Domino's pizza @ Sunday]         ← temporal specialization
```

```
              [relationship: crush]          ← original fact
                      |
              [relationship: girlfriend]     ← correction (supersedes)
                      |
              [relationship: ex]             ← future correction
```

the correction chain becomes one specific type of edge. but now i can also have:

- **`contextual_variant`** — same predicate, different context. doesn't supersede, coexists.
- **`specialization`** — a child fact that narrows the parent. biryani (general) → biryani at home (specific).
- **`temporal_branch`** — "used to do X, still do X sometimes, but now mainly do Y." the branch is the "sometimes."
- **`parallel`** — two independent facts about the same entity that don't conflict and don't relate.

the schema change is surgical. instead of one `supersedes` field (single parent pointer), i'd add:

```sql
CREATE TABLE fact_edges (
    edge_id       TEXT PRIMARY KEY,
    from_fact_id  TEXT REFERENCES facts(fact_id),
    to_fact_id    TEXT REFERENCES facts(fact_id),
    edge_type     TEXT NOT NULL,  -- 'correction' | 'specialization' | 'contextual_variant' | 'temporal_branch'
    created_at    TIMESTAMP NOT NULL
);
```

the `facts` table stays exactly as it is. the edges live in a separate table. this means the current linear chain still works — `correction` edges are exactly the current `supersedes` pointer, just reified. the upgrade is backwards compatible.

why does this matter for retrieval? right now, when i ask "what does the user like to eat?", the retriever returns one fact — the latest value in the chain. with a fact DAG, the retriever can return a cluster: the general preference node, plus its branches, weighted by the query context. if the user message is "ghar pe kya banate ho?", home-cooking branches score higher. if the message is "aaj stressed hoon," emotional-context branches score higher. the structure itself guides retrieval without needing a separate classifier for every query type.

it also helps with the "retrieval dilution" problem i documented in the failure analysis. right now, all facts at the same recency/confidence level score similarly and everything floods the context. with typed edges, i can retrieve "the root fact plus its most contextually relevant branch" rather than "all facts for this predicate." the graph traversal replaces the flat score threshold.

**i won't ship this in the current build** — the current linear chain is sufficient for the correction cases in the assignment, and i'd rather ship something that works cleanly than over-engineer early. but this is the natural next layer. the data model is already structured correctly (a fact table with a self-referential key). the migration is a new junction table and a traversal query. the philosophical foundation — everything is a person, every fact has the same shape — stays intact. the structure just gets richer edges.

---

## anti-patterns i deliberately avoided

| anti-pattern | why it fails | what i did instead |
|---|---|---|
| overwrite on correction | loses history, can't answer "pehle kya tha?" | supersession chain |
| flat retrieval | no ranking = irrelevant facts flood context | weighted hybrid ranking |
| eager entity merge | combines separate entities prematurely | explicit entity disambiguation |
| uniform sensitivity | all facts treated the same | 4-level gating policy |
| context-free facts | facts without origin lose meaning | `context_summary`, `conversation_id` |
| schema-per-type | explosion of tables and schemas | single Fact table with metadata |

---


