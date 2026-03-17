from __future__ import annotations
import json
from pathlib import Path
from evals.schema import EvalCase


def load_suite(path: str | Path = "evals/golden_suite.jsonl") -> list[EvalCase]:
    """Load eval cases from a JSONL file."""
    cases: list[EvalCase] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            cases.append(EvalCase(**data))
    return cases


def filter_cases(
    cases: list[EvalCase],
    category: str | None = None,
    severity: str | None = None,
    tags: list[str] | None = None,
) -> list[EvalCase]:
    """Filter eval cases by category, severity, or tags."""
    filtered = cases
    if category:
        filtered = [c for c in filtered if c.category == category]
    if severity:
        filtered = [c for c in filtered if c.severity == severity]
    if tags:
        filtered = [c for c in filtered if any(t in c.tags for t in tags)]
    return filtered
