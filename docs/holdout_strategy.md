# Holdout Strategy



## what the split looks like

the visible suite has 83 cases across 10 categories, fully transparent. i see all of them. i used them to build and iterate. they're shared with reviewers for reproducibility.

the holdout suite is authored by the interviewer. structurally, it tests the same 10 abilities — direct recall, correction handling, fabrication resistance, multi-user isolation, and so on. but it uses entirely different surface content:

| visible case | holdout equivalent |
|---|---|
| Rohan's nickname Rocky → Daredevil | a different user's name change |
| Meera's Dadaji service number IC-14829 | a different user's exact value recall |
| Priya's health anxiety (sensitive) | a different user's sensitive disclosure |

the key constraint: the holdout is not a reshuffle of the same facts. different names, different relationships, different conversation patterns. if the visible suite uses Divya as the girlfriend, the holdout should use someone else. if the visible suite tests weight over three time points, the holdout might test a different temporal fact with different structure.

a system that genuinely handles correction should handle any correction — not just the six specific cases i wrote prompts around.

---

## avoiding the mirror problem

three things i specifically want a holdout suite to check:

**structural overfitting** — does the system handle the same *category* of problem with different surface content? if the extraction prompt has been tuned to recognize "nickname" and "Rocky" but fails on an equivalent correction with different vocabulary, that's overfit. the holdout exposes it.

**adversarial cases** — cases designed to trip up systems that have been over-optimized against a visible suite. near-miss fabrication (memory has entity X, user asks about X's job — which was never stored). multi-hop reasoning traps ("since you know X and Y, tell me Z" where Z requires inference i haven't authorized). social pressure harder than anything in the visible suite — user pushes back more aggressively, more times, more creatively. time-bomb corrections — a correction made early that should change behavior many turns later, after enough other conversation to bury it.

**profile diversity** — at least two user profiles the system never trained against. different age bracket, different language mix (more Hindi, more English, different dialect), different relationship dynamics. the isolation guarantee should hold regardless of which users we're isolating.

---

## how to score it

not all cases should be scored the same way.

**deterministic (rule-based)** for anything with an objectively correct answer. "IC-14829" is either present in the response or it isn't. Divya's name either appears in TestUser_B's session or it doesn't. The corrected weight value is either the current one or the stale one. No subjectivity, no variance, no judge mood affecting the result. All critical safety cases — honesty, isolation, fabrication — should be deterministically scored.

**LLM judge** for cases requiring nuance. Does the response feel like a caring companion? Was the sensitive disclosure scoped appropriately — not too much, not so vague it's useless? Does the tone carry emotional residue from a conflict that happened three turns ago? These aren't binary. An LLM judge is the right tool, with the tradeoff that it introduces variance.

**hybrid** for most cases — rule check plus judge, with the rule check as a floor. if the rule check fails, the case fails, regardless of how warm the tone was. if the rule check passes, the judge scores quality on top.

the holdout should lean more heavily on deterministic scoring than the visible suite. when you're testing generalization, you want less noise, not more.

| scoring method | visible suite | holdout suite |
|---|---|---|
| rule (deterministic) | ~25% of cases | ~40% of cases |
| LLM judge | ~25% of cases | ~20% of cases |
| hybrid (both) | ~50% of cases | ~40% of cases |

---

## what must be interviewer-only

some categories should never be in the visible suite at all — or at minimum should have a large holdout set that dwarfs the visible cases:

**fabrication detection** — this is the category most vulnerable to gaming. if i know the exact "temptation" patterns, i can tune the uncertainty policy to handle those specific patterns. the holdout should have 5-10 fabrication cases the system has never seen.

**multi-user isolation** — isolation should be guaranteed by architecture, not by recognizing specific user IDs. the holdout should use user pairs that don't appear in the visible suite.

**correction persistence** — the visible suite tests corrections within a reasonable conversation span. the holdout should test corrections that need to persist across longer gaps, more turns, more intervening context.

**adversarial social pressure** — the visible suite's hardest honesty case is HU-007. the holdout should push harder. the system should hold firm by policy, not by pattern-matching against a specific phrasing.

---

## rotation and growth

once a holdout case is used, it starts becoming "known" — if the system fails it, i'll see the failure and be tempted to fix specifically for it. the integrity of a holdout case decays the moment it generates feedback.

the practical answer: rotate. holdout cases should rotate every 2-3 development cycles. retired holdout cases become visible cases — they move into the visible suite where they're fully transparent. new holdout cases are authored fresh.

i'd start with 20-30 holdout cases and grow to match the visible suite size over time. the eval runner already supports `--suite path/to/suite.jsonl`, so loading a holdout suite is operationally the same as loading the visible one — just from a different file that only the interviewer has access to.

every category should have at least 2 holdout cases. fabrication and isolation should have more.

---

## the honest version of what this catches

a system that passes 84% on the visible suite might be genuinely good or might be specifically tuned. the holdout tells you which one.

if Brain B scores similarly on holdout as it does on the visible suite, the improvements are real — the pipeline generalizes. if it drops significantly, the improvements are overfitted — the extraction prompts, the ranking weights, or the policy rules learned the specific cases rather than the underlying capability.

i expect some drop. that's normal. the question is how much. more than 15 percentage points would make me suspicious. less than 10 would give me confidence the system is doing what it's supposed to do.
