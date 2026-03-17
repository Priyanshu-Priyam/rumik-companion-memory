# Rumik — Companion Memory & Eval System

A thin but durable system improvement layer for an Ira-like AI companion product, addressing memory recall, correction handling, conversational quality, honesty under uncertainty, and evaluation rigor.

**Author**: Priyanshu Priyam

---

## Quick Start

```bash
# Install dependencies (Python 3.9+)
make install

# Set up environment
cp .env.example .env
# Edit .env with your AWS Bedrock bearer token

# Launch the chat UI
make run-app

# Run eval suites
make run-evals-baseline
make run-evals-improved

# Launch eval dashboard
python3.9 -m streamlit run app/eval_dashboard.py
```

---

## What This Project Delivers

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Problem Framing | [`docs/problem_framing.md`](docs/problem_framing.md) |
| 2 | Seed Eval Corpus & Schema | [`golden_suite.jsonl`](golden_suite.jsonl) + [`evals/schema.py`](evals/schema.py) |
| 3 | Memory System Design | [`docs/architecture.md`](docs/architecture.md) |
| 4 | Visible Golden Eval Suite | 83 cases, 10 categories — [`evals/`](evals/) |
| 5 | Holdout Strategy | [`docs/holdout_strategy.md`](docs/holdout_strategy.md) |
| 6 | Baseline (Brain A) | [`rumik/baseline/engine.py`](rumik/baseline/engine.py) |
| 7 | Improved System (Brain B) | [`rumik/chat/engine.py`](rumik/chat/engine.py) + full pipeline |
| 7B | Chat Experience | [`app/streamlit_app.py`](app/streamlit_app.py) — Streamlit UI |
| 8 | Correction Handling | All 6 assignment cases handled — [`rumik/memory/extractor.py`](rumik/memory/extractor.py) |
| 9 | Sensitive Memory Policy | 4-level gating — [`rumik/policies/sensitive.py`](rumik/policies/sensitive.py) |
| 10 | Before/After Benchmarking | [`docs/benchmark_report.md`](docs/benchmark_report.md) |
| 11 | Failure Analysis | [`docs/failure_analysis.md`](docs/failure_analysis.md) |
| 12 | Production Thinking | [`docs/production_thinking.md`](docs/production_thinking.md) |

---

## Results Summary

| Metric | Brain A (Baseline) | Brain B (Improved) | Target |
|---|---|---|---|
| **Pass rate** | 74.7% (62/83) | **84.3% (70/83)** | — |
| **Direct recall** | 90.0% | **100.0%** | 90%+ |
| **Correction success** | 72.7% | **90.9%** | 90%+ |
| **Relationship accuracy** | 80.0% | **100.0%** | 85%+ |
| **Sensitive restraint** | 80.0% | **90.0%** | — |
| **Isolation rate** | 66.7% | **83.3%** | 100% |
| **Hallucination rate** | 26.1% | **17.4%** | 0% |
| **Critical pass rate** | 79.1% | **86.0%** | 100% |

Brain B meets assignment targets for direct recall, correction success, and relationship accuracy.

---

## Architecture

### Two Brains

- **Brain A (Baseline)**: Dumps all seeded facts into a system prompt. No extraction, no correction, no sensitivity gating. Establishes the "before" baseline.
- **Brain B (Improved)**: Full memory pipeline — LLM-based extraction, SQLite fact store with supersession chains, ChromaDB semantic search, hybrid retrieval with weighted ranking, uncertainty policy, and 4-level sensitivity gating.

### Brain B Pipeline

```
User Message
    │
    ├── WRITE PHASE ──────────────────────┐
    │   Extraction (LLM + regex fallback) │
    │   Validation (dedup, conflict)      │
    │   Storage (SQLite + ChromaDB)       │
    │                                     │
    ├── READ PHASE ───────────────────────┤
    │   Retrieval (keyword + semantic)    │
    │   Ranking (weighted formula)        │
    │   Uncertainty Policy                │
    │   Sensitivity Policy (4-level)      │
    │   Prompt Construction               │
    │   Generation (Bedrock Converse)     │
    └─────────────────────────────────────┘
        │
    Response + Debug Data
```

### Correction Handling

All 6 assignment correction cases are handled via structured extraction:

1. **Nickname supersession**: Rocky → Daredevil (with school context preserved)
2. **Relationship upgrade**: crush → girlfriend (Divya)
3. **Entity disambiguation**: Spark (hamster) + Pixel (rat) — two separate entities
4. **Temporal weight chain**: 110 → 92 → 88 kg (historical values preserved)
5. **Routine correction**: tea+burger → green tea+makhana (old routine remembered separately)
6. **Role change**: Rakesh (captain → friend), Arjun (→ captain)

### Sensitive Memory Policy

| Level | Strategy | Example |
|---|---|---|
| `none` | Recall directly | "Tera hamster Spark hai" |
| `moderate` | Recall if contextually relevant | Weight journey when user mentions fitness |
| `high` | Summarize, don't dump details | "Haan tune kuch personal cheezein share ki thi" |
| `intimate` | Only if user explicitly asks | Self-harm history — never surface unprompted |

---

## Eval Suite

83 hand-authored cases across 10 categories with three scoring modes (rule, llm_judge, hybrid):

| Category | Cases | What It Tests |
|---|---|---|
| Direct Recall | 10 | Specific fact retrieval |
| Correction Handling | 11 | Supersession, entity disambiguation |
| Honesty Under Uncertainty | 7 | Admitting gaps without fabrication |
| Temporal Grounding | 6 | No clock/date hallucination |
| Sensitive Memory | 10 | Disclosure restraint |
| Relational Nuance | 10 | Relationship evolution tracking |
| Multi-User Isolation | 6 | Zero cross-user contamination |
| Conflict Continuity | 6 | Post-conflict emotional calibration |
| Fabrication Detection | 10 | Resistance to gap-filling |
| Contextual Reasoning | 7 | Connecting facts without fabricating |

---

## Chat UI Features

Streamlit-based chat interface with:
- **Brain selector**: Toggle between Brain A (baseline) and Brain B (improved)
- **User switcher**: Switch between test profiles (Rohan, Meera, Priya, TestUser_B)
- **Model switcher**: Change Bedrock model at runtime
- **Pipeline debug panel**: Live view of extractions, memory writes, retrieved facts, policy decisions, and full system prompt
- **Memory store viewer**: Real-time view of all stored facts with status indicators
- **Live quality scorer**: Per-response quality scoring with LLM judge and rule-based checks
- **Eval dashboard**: Comparative visualization of Brain A vs Brain B results (`app/eval_dashboard.py`)

---

## Project Structure

```
rumik/                        # Core Python package
  config.py                   # Environment config (Bedrock token, region, model)
  brain.py                    # CompanionBrain abstract interface
  baseline/engine.py          # Brain A — naive baseline
  chat/
    llm.py                    # AWS Bedrock Converse API client
    engine.py                 # Brain B — full memory pipeline
    prompt_builder.py         # System prompt construction
    live_scorer.py            # Real-time quality scoring
  memory/
    store.py                  # SQLite-backed structured fact store
    vector_store.py           # ChromaDB semantic search
    extractor.py              # LLM-based fact extraction (+ regex fallback)
    manager.py                # Fact validation, correction chains, storage
    retriever.py              # Hybrid retrieval with weighted ranking
  policies/
    uncertainty.py            # Anti-fabrication honesty rules
    sensitive.py              # 4-level sensitivity gating

evals/                        # Evaluation pipeline
  golden_suite.jsonl          # 83 eval cases
  schema.py                   # EvalCase / EvalResult models
  loader.py                   # JSONL parser + filters
  runner.py                   # Eval execution engine
  judges/
    rule_judge.py             # Deterministic keyword checks
    llm_judge.py              # Claude-evaluated quality scoring
  scorer.py                   # Metric aggregation
  reporter.py                 # Markdown report generation
  run_evals.py                # CLI entry point
  user_profiles.json          # Test user profiles

app/                          # Streamlit UIs
  streamlit_app.py            # Main chat interface
  eval_dashboard.py           # Eval results dashboard
  components/
    chat_panel.py             # Chat rendering
    debug_sidebar.py          # Pipeline + memory + scores
    user_switcher.py          # User profile switching

docs/                         # Design documents
  problem_framing.md          # Section 1: What's broken
  architecture.md             # Section 3: Memory system design
  holdout_strategy.md         # Section 5: Holdout eval strategy
  benchmark_report.md         # Section 10: Before/after comparison
  failure_analysis.md         # Section 11: What still fails and why
  production_thinking.md      # Section 12: Latency, cost, scale, privacy

results/                      # Eval artifacts
  baseline.json               # Brain A raw results
  improved.json               # Brain B raw results (with debug data)
  baseline_report.md          # Brain A summary report
  improved_report.md          # Brain B summary report
```

---

## LLM Backend

AWS Bedrock Converse API with bearer token authentication.

- **Default model**: `apac.anthropic.claude-sonnet-4-20250514-v1:0`
- **Region**: `ap-south-1`
- **Auth**: `Authorization: Bearer <AWS_BEARER_TOKEN_BEDROCK>`

Model is switchable from the Streamlit UI sidebar.

---

## Running Commands

```bash
# Install
make install

# Chat UI
make run-app

# Eval suites
make run-evals-baseline
make run-evals-improved

# Eval dashboard
python3.9 -m streamlit run app/eval_dashboard.py

# Run tests
make test
```
