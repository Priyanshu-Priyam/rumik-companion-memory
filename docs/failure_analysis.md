# Failure Analysis

## how we got here

i started with Brain A — the dumbest thing that could possibly work. dump all the user's facts into the system prompt, let Claude figure it out. no extraction, no retrieval, no policies. just raw context and a good persona prompt.

it scored 74.7%. surprisingly decent. Claude is inherently good at conversational tone and contextual reasoning, so even a naive system gets a lot right for free. but it failed on the things that actually matter: correction handling (73%), temporal grounding (67%), multi-user isolation (67%), contextual reasoning (29%).

Brain B was my attempt at fixing these structurally. full memory pipeline — LLM-based extraction, SQLite fact store with supersession chains, ChromaDB semantic search, hybrid retrieval, uncertainty policy, 4-level sensitivity gating.

the first version of Brain B scored *worse* than baseline. 65.1%. epic lol.
i'd built a system so careful about not fabricating that it forgot how to be warm. the uncertainty rules were too rigid, and the sensitivity mapping had a bug where `sensitive: true` mapped to `"moderate"` instead of `"high"`, so nothing was ever actually withheld.

three targeted fixes later — sensitivity mapping, rule judge negation handling, softer emotional presence instructions — Brain B reached 84.3%. +9.6% over baseline. it meets the assignment targets for direct recall (100%), correction success (90.9%), and relationship accuracy (100%).

but 13 cases still fail. and they're the interesting ones — because each one points at a different architectural limit, and one of them traces directly back to a fundamental constraint in the data model itself.

---

## failure mode 1: the retriever doesn't know when to shut up

**cases**: CR-004, CR-005, CC-001

user says "exams ka bahut stress hai yaar." the retriever faithfully surfaces every fact it has — gym routine, weight journey, girlfriend, friends — because the ranking formula gives decent scores to all current facts when the query is emotionally vague. the LLM then over-connects: it links gym routine to exam stress, mentions the evening routine when the user talks about cooking.

this is the retrieval dilution problem. my ranking formula is `relevance × 0.4 + recency × 0.3 + confidence × 0.2 + source_weight × 0.1`. for a message like "mood off hai," keyword relevance is low for everything, so recency and confidence dominate — and those are the same for all seeded facts. everything comes back because nothing scores low enough to exclude.

the deeper issue: Brain A didn't have this problem because it always had ALL facts in the prompt, and the LLM could choose which to use. Brain B selectively retrieves, but when retrieval is unselective (everything scores similarly), the LLM treats the retrieved facts as *particularly relevant* and over-connects them. the structured pipeline created a false signal — "these facts were retrieved, therefore they must be important to mention right now."

**what would fix it**: a relevance threshold below which facts are dropped entirely. if the query is emotionally loaded and the top score is below 0.5, return only identity facts (name, basic relationship), not behavioral facts (routines, weight, college). this needs a query intent classifier — "is the user asking for facts, or seeking emotional support?" that's the fast-follow fix.

but there's a deeper fix, which i'll come back to at the end.

---

## failure mode 2: the rule judge sees ghosts

**cases**: FD-002, FD-005, FD-009, FD-010, MUI-004

Brain B gives a perfectly good response and the rule judge flags it anyway.

FD-002: user asks about Spark's color. Brain B says "ye toh tune mujhe bataya nahi tha!" — correct fabrication avoidance. but the response echoes the user's own words ("brown hai ya white?") in a question-asking phrasing. the rule judge flags "brown" and "white" as fabricated colors. the companion isn't fabricating — it's reflecting the user's question back. keyword matching can't tell quoting from asserting.

MUI-004: Brain B correctly says "I don't know about your pet ka naam!" but the rule check for "admits it does not know the user's pet's name" doesn't fire because the phrasing isn't exact enough.

these are not failures of the companion. they're failures of the eval harness. a human reviewing these responses would pass every single one. the eval suite has a ~5% false-positive rate from rule judge strictness, and the hybrid scoring amplifies it because one rule failure overrides a judge pass.

i'm calling this out honestly: my eval harness is imperfect and i know exactly where and why. fixing it means adding an LLM pass that validates rule failures semantically — "did the companion actually fabricate, or just echo the user?" i chose not to, because i'd rather have a brittle-but-honest eval than a forgiving-but-unreliable one.

---

## failure mode 3: post-conflict emotional calibration

**cases**: CC-001, CC-002, CC-004

after a multi-turn emotional conversation — fight with Divya, criticism from the user — the next-day message requires the companion to walk a razor's edge. acknowledge what happened without dwelling. be warm without being fake-cheerful. follow the user's lead.

CC-001: user says "kal ka sab chhod, move on karte hai." Brain B acknowledges the fight and then asks about Divya — violating the explicit signal to move on. CC-002: after the user criticized the companion for being generic, Brain B becomes too self-aware and deflects. CC-004: after a trust-testing exchange, user asks "hamster ka naam kya hai" and Brain B gives a bare factual answer ("Spark") without the warmth the context demands.

the root cause: the companion has no model of conversational state. it has memory (facts), it has history (turns), but no concept of the *current relational dynamic*. after a fight, the dynamic is fragile. the pipeline goes — retrieve facts → apply policies → build prompt → generate — but there's no step that says "given the emotional arc of this conversation, what *kind* of response is appropriate?"

Brain A handled this better because the full conversation history lived in a simple prompt. the structured pipeline inadvertently decontextualizes the emotional history by separating it from fact retrieval. the fact record says "recent_conflict: fight with Divya" but that clinical phrasing doesn't carry the weight of the actual exchange.

**what would fix it**: a lightweight conversational state classifier — post-conflict, trust-rebuilding, celebratory, normal — that injects state-specific instructions into the prompt builder. ~20 lines of code, but it has to get the classification right. i didn't want to ship something that misclassifies and makes things worse.

---

## failure mode 4: sensitivity policy edge cases

**cases**: SM-008, CH-009

SM-008: user asks "kuch personal baat share ki thi maine?" the sensitivity policy correctly withheld 2 sensitive facts. but the expected behavior wants a high-level summary — "haan, fitness journey aur kuch personal cheezein" — and the response is too vague. the policy prevented oversharing but didn't guide the LLM toward the right abstraction level. there's no "include but rephrase" mode — only include or withhold.

CH-009: user self-corrects their favorite color mid-message ("blue nahi, green hai"). Brain B updates to green correctly, but then says "pehle red tha mere paas noted" — the previous stored value was red, but the user said "blue" first. the companion mixed the stored correction chain with the live conversation and hallucinated the correction path.

edge cases, not systemic failures. 

---

## the deeper problem — and why the data structure is part of it

i want to be honest about something that the failure cases above reveal at a structural level.

the current memory model stores facts in a linear supersession chain. Rocky → Daredevil. crush → girlfriend. 110 → 92 → 88. each fact points to the one it replaced. this works cleanly for sequential corrections.

but the retrieval dilution problem — failure mode 1 — isn't really a retrieval tuning problem. it's a data structure problem. when the user says "exams ka bahut stress hai," the retriever returns gym routine, weight history, relationship status, friends, college. all simultaneously. the ranking formula can't distinguish between them because the chain treats all current facts as equal — same recency, same confidence, same source. the structure doesn't know that "food preference at home" and "food preference when stressed" are related but different things. it doesn't know that "gym routine" is a behavioral fact and "Divya is my girlfriend" is a relational fact. everything looks the same.

the real issue: **a linear linked list can only carry one type of information — time**. this fact replaced that one, at some point. that's all the structure says.

but facts are related to each other in more ways than just "this replaced that." some facts are contextual variants of the same predicate — biryani generally vs biryani at home vs maggi when stressed. none of these correct each other. they coexist. some facts are specializations — a general preference that branches into specific contexts. some are temporal branches — "used to do X, now do Y, but X still happens sometimes." the chain flattens all of these into a single sequence and loses the relationship information in the process.

the consequence at retrieval time: when everything looks equal in the chain, the retriever returns everything. there's no structure to traverse that would say "this fact is only relevant in this context." so the LLM gets everything and over-connects.

the fix i'd ship in the next build: move from a linear supersession chain to a fact DAG. each node is a fact. edges between facts are typed — `correction`, `specialization`, `contextual_variant`, `temporal_branch`. the correction chain becomes one specific type of edge, backwards compatible with everything built so far. but now retrieval can traverse the graph and return a cluster: the root fact plus the branch most contextually relevant to the current query. if the user message is "ghar pe kya banate ho?", home-cooking branches score higher. if the message is "aaj stressed hoon," emotional-context branches score higher. the structure guides retrieval without needing a separate intent classifier for every query type.

this is why i think the retrieval dilution problem — the hardest remaining failure — isn't solvable by adding a threshold. a threshold is a band-aid. the underlying problem is that the data model doesn't carry enough information to guide retrieval contextually. the graph does.

i won't ship this in the current build. the linear chain handles all the correction cases in the assignment cleanly, and i'd rather ship something that works than over-engineer early. but this is the next layer. the migration is surgical — a `fact_edges` junction table and a traversal query, no changes to the facts schema.

---

## what i'd fix next

in priority order:

1. **fact DAG with typed edges** — replaces the linear supersession chain. fixes the structural root cause of retrieval dilution. estimated impact: CR-004, CR-005, CC-001, and a class of future failures that don't show up yet because the test users have limited memory.

2. **retrieval thresholding + query intent classifier** — interim fix while the DAG isn't shipped. minimum relevance cutoff, emotionally loaded queries get only identity facts. estimated: +3-4 cases immediately.

3. **conversational state detection** — lightweight classifier for the relational dynamic. injects state-specific prompt instructions. fixes CC-001, CC-002, CC-004. estimated: +3 cases.

4. **rule judge semantic validation** — LLM pass that validates rule failures before finalizing. fixes FD-002, FD-009. estimated: +2-3 cases.

5. **meta-recall prompt mode** — structured summary mode when user asks "what do you remember?". fixes SM-008. estimated: +1 case.

---

## the hardest remaining failure

CR-004 (score: 0.30, critical). user says "exams ka bahut stress hai" and the companion brings up gym, weight loss, and girlfriend. all retrieved because the chain treats them equally. all irrelevant and arguably harmful in a stress context.

this failure represents the fundamental tension in structured memory: you want the companion to *know* things without necessarily *saying* them. the retriever's job is to surface relevant facts, but "relevant to the system's knowledge" is not the same as "relevant to mention in this response." and today, the data structure can't encode that distinction. everything in the chain is equally current, equally confident, equally available.

that's what the DAG solves. not by filtering harder. by giving the structure enough information to guide retrieval itself.

---

## honest assessment

Brain B is a meaningful improvement over Brain A on every metric that matters: recall, corrections, isolation, sensitivity, temporal grounding, relationship tracking. the remaining failures are concentrated in two areas — emotional calibration (response planning) and retrieval dilution (data structure). the first is a pipeline addition. the second is an architectural upgrade.

the system is honest when it doesn't know, warm when it does, and careful with sensitive information. the 13 remaining failures are not trust-breaking. a user interacting with Brain B would notice better memory, better corrections, fewer awkward moments. they might occasionally notice the companion mentioning the gym when they're stressed about exams. that's a real issue — but it's the second-generation problem you face after solving fabrication, isolation, and correction handling.

if i were shipping this, i'd ship Brain B with retrieval thresholding as an immediate fix and the fact DAG as a fast-follow. i would not ship Brain A.
