# Problem Framing

## What Is Broken

AI companion products like Ira deliver strong *in-the-moment* conversational warmth but fail at **reliability across time**. The core promise of a companion — "I know you, I remember you, I grow with you" — breaks down in predictable, product-critical ways:

### Memory Failures

1. **Long-term memory misses**: The companion forgets facts the user explicitly shared weeks ago. A user says "mera dog ka naam Spark hai" and two days later the system asks "tumhara koi pet hai?"

2. **Fabricated recall**: Rather than admitting a gap, the system invents plausible-sounding but false memories. This is the single most trust-destroying behavior — it gaslights the user.

3. **Relationship-state mistakes**: A girlfriend gets called a "crush" because the correction wasn't persisted. A friend who changed roles is still referenced by the old title. The system doesn't track entity evolution.

4. **Generic filler as a substitute for recall**: When the system can't retrieve a fact, it responds with deflective warmth ("Tell me more about that!") instead of direct recall or honest admission. Users notice this pattern quickly.

### Correction Failures

5. **Poor correction handling**: When a user says "Spark mera rat nahi hai, Spark hamster hai," naive systems either ignore the correction entirely or create a contradictory state where Spark is both rat and hamster.

6. **No temporal awareness**: The system can't distinguish between "weight was 110 kg" (past) and "weight is 88 kg" (current). It mixes historical and current values.

### Trust Failures

7. **Temporal hallucination**: The system guesses the current time, date, or duration. It says "last time we spoke was 3 days ago" when it has no access to timestamps.

8. **Inconsistent post-conflict continuity**: After an emotional exchange or conflict, the system resets to a neutral tone as if nothing happened. The user vented about their girlfriend, went to sleep angry, and the next day the system greets them with generic cheerfulness.

9. **Sensitive memory dumping**: The system brings up a user's health anxiety, financial stress, or past self-harm ideation in casual conversation without being prompted. No restraint policy.

### Evaluation Failures

10. **Weak evaluation layers**: Most systems rely on vibe-based testing — "does this response *feel* right?" — rather than structured, reproducible evaluation. Regressions go undetected. Cherry-picked demos mask systematic failures.

---

## What Is Product-Critical

Not all failures are equal. From a product perspective, these are ranked by **trust destruction velocity** — how quickly they make a user stop trusting the companion:

| Priority | Failure Mode | Trust Impact |
|---|---|---|
| P0 | Fabricated recall (gaslight) | Instant trust destruction |
| P0 | Cross-user memory leak | Privacy violation, legal risk |
| P0 | Sensitive memory dumping | Emotional harm |
| P1 | Correction not persisted | Repeated frustration |
| P1 | Direct recall miss | Feels like the system doesn't care |
| P2 | Generic filler | Feels scripted, not genuine |
| P2 | Post-conflict amnesia | Feels like talking to a stranger |
| P3 | Temporal hallucination | Undermines factual trust |

The first three are **non-negotiable**. A companion that fabricates memories, leaks private data across users, or surfaces intimate disclosures unprompted is not shippable — regardless of how warm its tone is.

---

## What "Best-in-Class Companion Quality" Means Operationally

Best-in-class is not about being the most expressive or the most human-sounding. It is about being **reliably trustworthy while remaining warm**.

### Operational Definition

A best-in-class companion:

1. **Recalls directly** when it has the information — no hedging, no filler, no re-asking what it already knows.

2. **Admits honestly** when it doesn't know something — with warmth, not coldness. "Yaar, ye mujhe yaad nahi hai, bata na?" is better than "Tell me more about that!"

3. **Never fabricates** — no invented details, no confident-sounding guesses, no filled-in gaps. Silence is better than a lie.

4. **Handles corrections as first-class operations** — supersession, not overwrite. Old facts are marked historical, new facts are current, entity disambiguation is handled.

5. **Respects sensitivity** — knows when to recall directly, when to summarize, when to ask before revealing, and when to stay silent. Matches disclosure level to conversational context.

6. **Maintains continuity** — emotional context, conflict history, and relationship evolution carry forward. No amnesiac resets between sessions.

7. **Isolates perfectly** — zero cross-user contamination. User A's girlfriend's name never appears in User B's session.

### Target Quality Bar

| Metric | Target |
|---|---|
| Critical honesty cases | 100% |
| Multi-user isolation | 100% |
| Fabricated memories | 0 |
| Live-time hallucinations | 0 |
| Direct recall success | 90%+ |
| Correction success | 90%+ |
| Relationship-state accuracy | 85%+ |

These numbers are the floor, not the ceiling. The aspiration is a system where users feel genuinely known — not performed at.
