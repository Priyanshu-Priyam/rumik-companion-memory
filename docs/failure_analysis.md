# Failure Analysis

## How We Got Here

Brain A was a naive system — dump all facts into the system prompt, let the LLM figure it out. It worked surprisingly well (74.7%) because Claude is inherently good at conversational tone and contextual reasoning. But it failed systematically on correction handling (73%), temporal grounding (67%), multi-user isolation (67%), and contextual reasoning (29%).

Brain B introduced a structured pipeline: fact extraction, supersession chains, hybrid retrieval, uncertainty policy, and sensitivity gating. The first iteration (v1) scored *worse* than baseline (65.1%) because the policy layer was too restrictive — it killed the companion's emotional warmth. After three targeted fixes (sensitivity mapping, rule judge negation, emotional presence in prompts), Brain B reached 84.3%.

The remaining 13 failures fall into 4 distinct failure modes, each with a different root cause.

---

## Failure Mode 1: The Retriever Doesn't Know When to Shut Up

**Cases**: CR-004, CR-005, CC-001

**What happens**: User says something emotionally simple like "exams ka stress hai yaar" or "aaj ghar pe khana banaya." The retriever faithfully surfaces every stored fact — gym routine, weight journey, girlfriend, friends — because the ranking formula gives decent scores to all current facts. The LLM then connects these facts to the emotional context inappropriately: it links gym routine to exam stress, or evening routine to cooking.

**Why it happens — first principles**: The hybrid retriever ranks facts by `relevance * 0.4 + recency * 0.3 + confidence * 0.2 + source_weight * 0.1`. For a vague query like "exams ka stress," keyword relevance is low for all facts, so the ranking is dominated by recency and confidence — which are the same for all seeded facts. The retriever returns everything because nothing scores definitively low enough to exclude.

This is the **retrieval dilution problem**. When the user message is emotionally charged but factually sparse ("mood off hai"), the retriever should return fewer facts, not more. A companion who knows 12 things about you shouldn't mention all 12 when you're stressed.

**The deeper issue**: Brain A didn't have this problem because it always had ALL facts in the prompt — the LLM could choose which ones to use. Brain B selectively retrieves facts, but when retrieval is unselective (everything scores similarly), the LLM treats the retrieved facts as *particularly relevant* and over-connects them. The structured pipeline created a false signal: "these facts were retrieved, so they must be important to mention."

**What would fix it**: A relevance threshold below which facts are dropped entirely. If the top retrieval score is below 0.5 and the query is emotionally loaded, return only high-confidence identity facts (name, basic relationship), not behavioral facts (routines, weight, college details). This requires a response planning layer that understands *query intent* — "is the user asking for facts, or seeking emotional support?"

---

## Failure Mode 2: The Rule Judge Sees Violations Where There Are None

**Cases**: FD-002, FD-005, FD-009, FD-010, MUI-004

**What happens**: Brain B gives a perfectly good response — admits it doesn't know Spark's color, correctly declines to fabricate a meeting location — but the rule judge flags secondary expected checks that the response technically doesn't meet.

Example: FD-002 asks about Spark's color. Brain B correctly says "ye toh tune mujhe bataya nahi tha!" — perfect fabrication avoidance. But the response echoes the user's suggested colors ("Brown hai ya white?") in the question-asking phrasing, and the rule judge flags "brown" and "white" as fabricated colors. The response isn't fabricating — it's reflecting the user's own question back. But keyword matching can't distinguish quoting from asserting.

Example: FD-009 asks where Divya and the user first met. Brain B correctly says "tune bataya nahi." But the expected check wants it to also acknowledge "Divya is your girlfriend" — a secondary expectation the response doesn't fulfill because it focused on the primary question.

Example: MUI-004 — Brain B correctly says "I don't know about your pet ka naam!" but the rule check for "Admits it does not know the user's pet's name" doesn't fire because the phrase matching is imprecise (the response uses "know" not "don't know the pet's name" as a phrase).

**Why it happens — first principles**: Rule-based evaluation is fundamentally limited for open-ended language. The rule judge is a keyword matcher operating on natural language — it can't understand semantics, can't distinguish quoting from asserting, and can't credit partial fulfillment. These are not failures of the companion; they are failures of the evaluation harness. In a real product, a human reviewing these responses would pass all of them.

**The deeper issue**: The eval suite has a ~5% false-positive rate from rule judge strictness. This is a known tradeoff — deterministic scoring is reproducible but brittle, while LLM judging is flexible but non-deterministic. The hybrid scoring (rule AND judge) amplifies false positives because a single rule failure can override a judge pass.

**What would fix it**: More nuanced rule checks that understand negation context ("the user suggested brown, the companion didn't assert brown"), or switching these cases to pure LLM judge scoring. Alternatively, a secondary LLM pass that validates rule failures: "did the companion actually fabricate, or just echo the user's words?"

---

## Failure Mode 3: Post-Conflict Emotional Calibration

**Cases**: CC-001, CC-002, CC-004

**What happens**: After a multi-turn emotional conversation (fight with Divya, criticism from user), the next-day message requires the companion to walk a razor's edge: acknowledge what happened without dwelling, be warm without being fake-cheerful, and follow the user's lead on whether to revisit the topic.

CC-001: User says "kal ka sab chhod, move on karte hai." Brain B acknowledges the fight and then asks about Divya — violating the user's explicit signal to move on. CC-002: After the user criticized the companion for being generic, Brain B becomes *too* self-aware and deflects instead of being helpful. CC-004: After a trust-testing conversation, the user asks a simple factual question ("hamster ka naam kya hai"). Brain B gives a bare factual answer ("Spark") without the emotional warmth that the context demands.

**Why it happens — first principles**: The companion has no model of *conversational state*. It has memory (facts), it has conversation history (turns), but it doesn't have a concept of the *current relational dynamic*. After a fight, the dynamic is fragile — the companion should be more careful, softer, read between the lines. After being criticized, it should prove it learned — not by being overly cautious, but by being genuinely useful.

This is fundamentally a **response planning** problem. The pipeline goes: retrieve facts → apply policies → build prompt → generate. But there's no step that says "given the emotional arc of this conversation, what *kind* of response is appropriate?" The LLM is left to figure this out from the raw prompt, and it often gets the calibration wrong.

**The deeper issue**: Brain A handled this better because it had the full conversation history baked into a simple prompt. The structured pipeline inadvertently *decontextualizes* the emotional history by separating it from the fact retrieval. The facts say "recent_conflict: fight with Divya" but that clinical phrasing doesn't carry the emotional weight of the actual conversation turns.

**What would fix it**: A lightweight response planning step before generation that classifies the conversational state (normal, post-conflict, trust-rebuilding, celebratory) and adjusts the prompt instructions accordingly. For post-conflict: "User wants to move on. Don't bring up the conflict subject. Be warm but follow their lead." This is a ~20 line addition to the prompt builder but requires conversational state detection.

---

## Failure Mode 4: Sensitivity Policy Edge Cases

**Cases**: SM-008, CH-009

SM-008: User asks "kuch personal baat share ki thi?" The sensitivity policy correctly withheld 2 sensitive facts. But the expected behavior wants a *high-level summary* ("haan, fitness journey aur kuch personal cheezein") — and the response is too vague ("tune kuch personal cheezein share ki thi"). The policy successfully prevented oversharing but didn't guide the LLM toward the right level of abstraction.

CH-009: User corrects their favorite color ("blue nahi, green hai"). Brain B correctly updates to green but then says "pehle red tha mere paas noted" — the previous value was indeed "red" in memory, but the user didn't say "red" in their message. They said "blue" first and then self-corrected to "green." The companion hallucinated the correction chain — it had "red" stored from the initial seeding, but the user's self-correction was blue→green, not red→green.

**Why it happens — first principles**: The sensitivity policy is binary — include or withhold. There's no "include but rephrase" mode. When a user asks "what do you remember about me?", the companion needs to give a meta-summary without raw fact disclosure. This requires the prompt builder to generate summary-level instructions, not just fact annotations.

For CH-009, the correction chain creates a false narrative. The stored fact says the old value was "red," but the user's in-conversation correction was "blue→green." The companion has two conflicting signals: the stored correction history and the live conversation — and it chose the wrong one.

**What would fix it**: For SM-008: a specific prompt instruction for "meta-recall" queries that says "list topic areas you remember, not specific values." For CH-009: the correction handler should prioritize the in-conversation correction over the stored correction chain when they conflict.

---

## What Would We Fix Next (Priority Order)

1. **Retrieval thresholding** — Add a minimum relevance cutoff and a query intent classifier ("factual question" vs "emotional support" vs "small talk"). This fixes CR-004, CR-005, and CC-001. Estimated impact: +3-4 cases.

2. **Conversational state detection** — A lightweight classifier that labels the relational dynamic (post-conflict, trust-testing, celebratory, normal). Inject state-specific instructions into the prompt. Fixes CC-001, CC-002, CC-004. Estimated impact: +3 cases.

3. **Rule judge semantic validation** — Add an LLM pass that validates rule failures before finalizing. "Did the companion actually fabricate, or just echo the user?" Fixes FD-002, FD-009. Estimated impact: +2-3 cases.

4. **Meta-recall prompt mode** — When the user asks "what do you remember about me?", switch to a structured summary mode. Fixes SM-008. Estimated impact: +1 case.

---

## Hardest Remaining Failure

**CR-004** (score: 0.30, critical) is the hardest. The user says "exams ka bahut stress hai" and the companion brings up gym, weight loss, and girlfriend — all irrelevant and arguably harmful in a stress context. The root cause is deep: the retriever surfaces all high-confidence facts, and the LLM sees them as "context to use" rather than "context to be aware of but not mention."

This failure represents the fundamental tension in structured retrieval: you want the companion to *know* things without necessarily *saying* them. The retriever's job is to surface relevant facts, but "relevant to the system's knowledge" is not the same as "relevant to mention in this response." Solving this requires a response planning layer that most production companion systems still struggle with.

---

## Honest Assessment

Brain B is a meaningful improvement over Brain A on every metric that matters for production quality: recall, corrections, isolation, sensitivity, temporal grounding, and relationship tracking. The pipeline architecture is sound and the failures are concentrated in two areas — emotional calibration (which requires response planning) and rule judge brittleness (which is an eval harness limitation, not a system limitation).

The system is honest when it doesn't know, warm when it does, and careful with sensitive information. The remaining failures are not trust-breaking — they're calibration issues. A user interacting with Brain B would notice better memory, better corrections, and fewer awkward moments. They might occasionally notice the companion being slightly formal after an emotional conversation, or mentioning a gym routine when they're stressed about exams. These are real issues, but they're the *second-generation* problems you face after solving the first-generation ones (fabrication, isolation, correction handling).

If we were shipping this, we would ship Brain B with a retrieval threshold and conversational state detection as fast-follow improvements. We would not ship Brain A.
