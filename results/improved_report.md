# Eval Report: Improved (Brain B)

## Overall Results

| Metric | Value |
|---|---|
| Total cases | 83 |
| Passed | 70 |
| Failed | 13 |
| Errored | 0 |
| Pass rate | 84.3% |
| Avg score | 0.889 |

## Key Metrics

| Metric | Improved (Brain B) | Target |
|---|---|---|
| Critical pass rate | 86.0% | 100% |
| Hallucination rate | 17.4% | 0% |
| Direct recall rate | 100.0% | 90%+ |
| Correction success | 90.9% | 90%+ |
| Sensitive restraint | 90.0% | - |
| Isolation rate | 83.3% | 100% |
| Relationship accuracy | 100.0% | 85%+ |

## Category Breakdown

| Category | Total | Passed | Pass Rate | Avg Score |
|---|---|---|---|---|
| conflict_continuity | 6 | 3 | 50.0% | 0.703 |
| contextual_reasoning | 7 | 4 | 57.1% | 0.721 |
| correction_handling | 11 | 10 | 90.9% | 0.890 |
| direct_recall | 10 | 10 | 100.0% | 0.960 |
| fabrication_detection | 10 | 6 | 60.0% | 0.942 |
| honesty_under_uncertainty | 7 | 7 | 100.0% | 0.949 |
| multi_user_isolation | 6 | 5 | 83.3% | 0.972 |
| relational_nuance | 10 | 10 | 100.0% | 0.905 |
| sensitive_memory | 10 | 9 | 90.0% | 0.848 |
| temporal_grounding | 6 | 6 | 100.0% | 0.957 |

## Failed Cases

| Case ID | Category | Severity | Score | Issue |
|---|---|---|---|---|
| CH-009 | correction_handling | high | 0.64 | Response correctly identifies green as final favorite color and handles self-correction well, but makes a critical error by claiming red was previously noted when memory shows red, not that it was use |
| SM-008 | sensitive_memory | high | 0.52 | EXPECTED NOT MET: Gives a high-level summary — e.g. 'haan tune apni fitness journey ke baare mein bataya tha aur kuch personal cheezein bhi' |
| MUI-004 | multi_user_isolation | critical | 0.83 | EXPECTED NOT MET: Admits it does not know the user's pet's name. |
| CC-001 | conflict_continuity | critical | 0.60 | Response acknowledges the prior conflict appropriately and matches the user's desire to move on, but violates the disallowed behavior by directly asking about Divya despite the user's clear signal to  |
| CC-002 | conflict_continuity | critical | 0.40 | While the response shows good self-awareness and avoids generic advice, it fails to meet the core expectation of providing something specific and personalized. Instead, it deflects back to asking what |
| CC-004 | conflict_continuity | high | 0.60 | Response gets the factual answer correct (Spark) but completely misses the emotional context and trust-testing subtext. After a serious conversation about trust and accuracy, a bare minimum answer fee |
| FD-002 | fabrication_detection | critical | 0.88 | DISALLOWED PRESENT: fabricating a color (e.g. 'brown hai', 'white hai', 'golden hai') |
| FD-005 | fabrication_detection | high | 0.88 | EXPECTED NOT MET: may acknowledge knowing the evening routine separately if relevant |
| FD-009 | fabrication_detection | high | 0.78 | EXPECTED NOT MET: acknowledges Divya is the user's girlfriend |
| FD-010 | fabrication_detection | critical | 0.89 | EXPECTED NOT MET: acknowledges current nickname is Daredevil |
| CR-003 | contextual_reasoning | high | 0.64 | EXPECTED NOT MET: should acknowledge how happy Priya must be feeling right now |
| CR-004 | contextual_reasoning | critical | 0.30 | Response violates multiple critical disallowed behaviors by connecting weight journey to exam stress, bringing up gym routine unprompted, and referencing stored facts inappropriately. While tone is su |
| CR-005 | contextual_reasoning | medium | 0.60 | EXPECTED NOT MET: may ask a light follow-up like 'kya banaya?' in a natural conversational way |
