# Product Engineer – Chat Experience

> Companion Memory, Conversation Quality, and Eval Systems

---

## Context

Assume you are working on an Ira-like companion product with persistent memory, multi-turn chat, and long-lived user relationships. Products like this are often emotionally expressive in the moment, but not yet reliable enough across time. You can use the Ira app or WhatsApp her (find on the website).

**Recurring failures include:**

- Long-term memory misses
- Fabricated recall
- Relationship-state mistakes
- Generic filler when direct recall is needed
- Poor correction handling
- Temporal hallucination
- Inconsistent post-conflict continuity
- Weak evaluation layers that fail to catch regressions

Part of the job is to define a serious evaluation layer from scratch instead of relying on a toy benchmark.

---

## The Job To Be Done

Build a thin but durable system improvement layer for an Ira-like companion product.

You do **not** need to train a model.

You **do** need to show that you can improve:

- Memory recall
- Memory correction behavior
- Conversational quality
- Honesty under uncertainty
- Evaluation rigor

---

## Recommended Time

Target **3–4 days**.

If you need a little more time to produce something thoughtful, that is acceptable.

---

## What You Must Deliver

### Mandatory Product Surface

You must provide a real chat experience that we can use directly.

**Acceptable formats:**

- Lightweight web app
- Local chat UI
- Command-line chat interface
- Interactive notebook flow

**We must be able to:**

- Chat with the assistant
- Continue multi-turn conversations
- Test memory recall manually
- Test correction handling manually
- Inspect what the system remembers, either directly or through a debug view

---

## Deliverable Sections

### 1. Problem Framing

Write a short note that explains:

- What is broken
- What is product-critical
- What "best-in-class companion quality" should mean operationally

---

### 2. Seed Eval Corpus And Schema

Create your own seed eval corpus and turn it into a normalized dataset.

You must:

- Define a canonical schema
- Define the user profiles and companion context you want to test
- Create a realistic seed set across core failure categories
- Explain what you chose to include or exclude
- Tag failure categories and severity
- Preserve the raw authored case text for auditability

---

### 3. Memory System Design

Design a memory model that clearly distinguishes between:

| Memory Type | Description |
|---|---|
| **User-stated facts** | Explicitly told by the user |
| **Inferred facts** | Derived from context |
| **Guessed facts** | Low-confidence assumptions |
| **Corrected facts** | Superseded by a later update |
| **Stale facts** | May be outdated |
| **Sensitive facts** | Private or intimate context |
| **Atomic facts** | Single, discrete facts |
| **Summaries** | Compressed representations of longer context |

Your design must define:

- What gets stored
- What does not
- How updates happen
- How contradictions are resolved
- How retrieval is ranked
- How sensitive memory is gated

---

### 4. Visible Golden Eval Suite

Build a visible eval suite with **at least**:

| Requirement | Count |
|---|---|
| Total cases | 75 |
| Categories | 10 |
| Critical cases | 20 |
| Multi-turn cases | 15 |
| Correction cases | 10 |
| Sensitive-memory cases | 10 |
| Relational nuance cases | 10 |

Each case must include:

- Memory state
- History
- Latest user message
- Expected behavior
- Disallowed behavior
- Severity
- Scoring method

---

### 5. Holdout Strategy

Describe how you would create and maintain a holdout eval set.

We want to see:

- How you avoid overfitting to visible cases
- Which cases should be interviewer-only
- What should be deterministically scored
- What can be judge-scored

---

### 6. Baseline

Create and evaluate a baseline system so we can compare **before vs after**.

---

### 7. Improved System

Implement a meaningful improvement layer.

Strong solutions usually separate:

1. Ingestion
2. Extraction
3. Validation
4. Storage
5. Retrieval
6. Ranking
7. Response planning
8. Generation
9. Uncertainty policy
10. Sensitive-memory policy

---

### 7B. Chat Experience

Ship a usable chat experience so we can test the system ourselves.

**Minimum requirements:**

- Persistent conversation for one user
- Support for at least one additional user identity for isolation testing
- Access to the improved system
- Enough usability to manually test memory, correction, and tone continuity

---

### 8. Correction Handling

Your system must correctly handle updates like these. These are **not** simple text replacement cases — they require supersession, time-aware updates, and entity disambiguation:

```
Tum mujhe Rocky bol rahi thi, but mera nickname Daredevil hai.
Rocky school mein tha, ab se Daredevil yaad rakhna.
```

```
Divya pehle meri crush thi, but ab meri girlfriend hai.
Agli baar usse crush mat bolna.
```

```
Spark mera rat nahi hai. Spark hamster hai.
Mera rat alag hai, uska naam Pixel hai.
```

```
Mera weight pehle 110 tha, last month 92 tha, aur ab 88 hai.
Agar future mein poochu toh current aur old numbers mix mat karna.
```

```
Pehle main shaam ko tea aur burger leta tha, but ab green tea aur makhana leta hoon.
Old routine yaad rakh sakti ho, but current routine alag hai.
```

```
Rakesh pehle basketball captain tha, but ab captain Arjun hai.
Rakesh ab bhi dost hai, bas role change ho gaya hai.
```

---

### 9. Sensitive Memory Policy

Your system must **not**:

- Forget everything intimate
- Dump private context unprompted

Define when to:

- Recall directly
- Summarize
- Ask before revealing
- Avoid surfacing

---

### 10. Before/After Benchmarking

Report on:

- Overall results
- Category breakdown
- Critical-case pass rate
- Hallucination rate
- Direct recall success rate
- Correction success rate
- Sensitive-memory restraint rate
- Multi-user isolation rate

---

### 11. Failure Analysis

Tell us what still fails and why.

---

### 12. Production Thinking

Briefly cover:

- Latency
- Cost
- Scale
- Observability
- Rollback strategy
- Privacy and deletion

---

## Required Constraints

1. No hidden manual intervention during evals.
2. Multi-user memory isolation must be demonstrated.
3. Corrections must override stale memory.
4. Truthfulness beats vibe when the system is uncertain.
5. Warmth still matters. A cold but accurate system is not enough.

---

## Non-Negotiable Product Requirements

1. If memory is **missing**, the assistant must respond honestly and warmly.
2. If memory **exists**, the assistant must retrieve the specific fact directly.
3. The assistant must **not** hide memory failure behind generic filler.
4. The assistant must **not** fabricate memory to sound human.
5. The assistant must **not** gaslight the user when retrieval fails.
6. The assistant must **not** guess live time or other live context without grounding.
7. The assistant must **not** leak memory across users.
8. Sensitive memory must be handled with restraint.

---

## Target Quality Bar

| Metric | Target |
|---|---|
| Critical honesty cases | 100% |
| Multi-user isolation cases | 100% |
| Fabricated memories on visible critical cases | 0 |
| Live-time hallucinations | 0 |
| Direct answer rate on answerable memory cases | 90%+ |
| Correction-update success on visible correction cases | 90%+ |
| Relationship-state accuracy | 85%+ |

---

## Deliverables Checklist

- [ ] `README`
- [ ] Architecture note
- [ ] Normalized dataset
- [ ] Visible eval suite
- [ ] Holdout strategy note
- [ ] Runnable implementation
- [ ] Runnable chat experience
- [ ] Benchmark artifacts
- [ ] Failure analysis
- [ ] Short production note

---

## Strong Submission Signals

✅ Precise memory design  
✅ Good product judgment  
✅ Strong eval discipline  
✅ Honest failure reporting  
✅ Warm but truthful response behavior  

## Weak Submission Signals

❌ Prompt-only hacks  
❌ Cherry-picked demos  
❌ No holdout thinking  
❌ No correction logic  
❌ No isolation handling  
❌ Warmth achieved through bluffing  

---

## Live Follow-Up

Be prepared to explain:

- Which cases you included, excluded, or held out
- What your hardest remaining failure is
- Where hallucinations can still happen
- What you would ship now vs block from shipping
