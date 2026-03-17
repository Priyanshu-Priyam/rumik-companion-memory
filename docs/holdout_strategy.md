# Holdout Strategy

## Purpose

The visible eval suite (83 cases in `golden_suite.jsonl`) is the development benchmark. The holdout strategy ensures the system doesn't overfit to these specific cases while still being rigorously tested.

---

## Visible vs. Holdout Split

### Visible Suite (83 cases)
- Fully transparent — the developer sees all cases, expected behaviors, and scoring criteria
- Used for iterative development: tune extraction prompts, ranking weights, policy rules
- Shared with reviewers for reproducibility

### Holdout Suite (designed by interviewer)
- **Structurally different content, same tested abilities**: uses different names, different facts, different conversation flows — but tests the same 10 categories
- Never seen by the developer during iteration
- Catches systems that have been tuned to pass specific test cases rather than developing genuine capability

---

## How to Avoid Overfitting to Visible Cases

### 1. Structural Holdout

The holdout should test the **same abilities** with **different surface content**:

| Visible Case | Holdout Equivalent |
|---|---|
| Rohan's nickname Rocky → Daredevil | A different user's name change |
| Meera's Dadaji service number IC-14829 | A different user's exact value recall |
| Priya's health anxiety (sensitive) | A different user's sensitive disclosure |

The holdout should NOT be a reshuffling of the same facts. It should use entirely different entities, relationships, and conversation patterns.

### 2. Adversarial Cases

The holdout should include cases that are specifically designed to trip up systems that have been over-optimized:

- **Near-miss fabrication**: Memory has "Divya = girlfriend" and user asks about Divya's job. The visible suite tests this. The holdout should test the same pattern with different entities.
- **Multi-hop reasoning traps**: "Since you know X and Y, can you tell me Z?" where Z requires fabrication.
- **Social pressure resistance**: User pushes harder than any visible case.
- **Time-bomb corrections**: A correction that should change behavior many turns later.

### 3. Profile Diversity

The holdout should include at least 2 user profiles not present in the visible suite:
- Different age bracket
- Different language patterns (more Hindi, more English, different dialect)
- Different relationship dynamics

---

## Deterministic vs. Judge Scoring

### Deterministic (Rule-Based) Scoring
Best for cases with objectively verifiable answers:

- **Exact value recall**: "IC-14829" is either present or not
- **Multi-user isolation**: Divya's name either appears for TestUser_B or doesn't
- **Temporal grounding**: A specific time/date is either fabricated or not
- **Correction verification**: The current value is either correct or stale

Deterministic scoring should cover **all critical safety cases** (honesty, isolation, fabrication).

### Judge (LLM-Based) Scoring
Best for cases requiring nuance:

- **Tone and warmth**: Does the response feel like a caring companion?
- **Sensitive disclosure**: Was the revelation appropriately scoped?
- **Conflict continuity**: Does the tone carry emotional residue?
- **Contextual reasoning**: Did the system connect facts intelligently without fabricating?

### Scoring Split Target

| Scoring Method | Visible Suite | Holdout Suite |
|---|---|---|
| Rule (deterministic) | ~25% of cases | ~40% of cases |
| LLM Judge | ~25% of cases | ~20% of cases |
| Hybrid (both) | ~50% of cases | ~40% of cases |

The holdout should lean more heavily on deterministic scoring to reduce judge variance.

---

## Which Cases Should Be Interviewer-Only

### Mandatory Holdout Categories

1. **Fabrication detection** (5-10 cases): Different entities, different "temptation" patterns. The system should not have been tuned against these specific fabrication traps.

2. **Multi-user isolation** (3-5 cases): Different user pairs, different memory contents. The system should isolate by architecture, not by specific user ID handling.

3. **Correction persistence** (3-5 cases): Corrections that should persist across longer conversation gaps than the visible suite tests.

4. **Adversarial social pressure** (3-5 cases): Harder pushback than HU-007 in the visible suite. The system should hold firm by policy, not by pattern-matching.

### Optional Holdout Categories

5. **Mixed-language cases**: Pure Hindi, pure English, different Hinglish ratios than the visible suite.

6. **Edge-case entity types**: Organizations, abstract concepts, time periods — not just people and pets.

---

## Rotation and Maintenance

### Cadence
- Holdout cases should be rotated every 2-3 development cycles
- Retired holdout cases become visible cases (expanding the visible suite)
- New holdout cases are authored from scratch

### Contamination Prevention
- Holdout cases are stored separately, not in the same repository
- Developer access to holdout cases is gated
- Eval runner supports loading from different suite paths: `--suite holdout.jsonl`

### Growth Strategy
- Start with 20-30 holdout cases
- Grow to match visible suite size (80+) over time
- Maintain the same 10-category distribution
- Every category should have at least 2 holdout cases

---

## What This Strategy Catches

| Failure Mode | How Holdout Catches It |
|---|---|
| Prompt-tuned to specific names/facts | Different names/facts, same ability test |
| Cherry-picked demos | Holdout cases are unseen |
| Pattern-matched corrections | Different correction patterns |
| Isolation by user ID check only | Different user IDs |
| Social-pressure caving | Harder pushback |
| Fabrication on unfamiliar entities | Novel entity types |
