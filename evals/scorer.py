from __future__ import annotations
from evals.schema import EvalResult


def aggregate(results: list[EvalResult]) -> dict:
    """Aggregate eval results into the metrics required by the assignment."""
    total = len(results)
    if total == 0:
        return {"error": "No results to aggregate"}

    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    errored = sum(1 for r in results if r.error)

    # Category breakdown
    categories: dict[str, dict] = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "scores": []}
        categories[cat]["total"] += 1
        if r.passed:
            categories[cat]["passed"] += 1
        categories[cat]["scores"].append(r.score)

    category_breakdown = {}
    for cat, data in sorted(categories.items()):
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        category_breakdown[cat] = {
            "total": data["total"],
            "passed": data["passed"],
            "pass_rate": data["passed"] / data["total"] if data["total"] else 0,
            "avg_score": round(avg_score, 3),
        }

    # Critical cases
    critical_results = [r for r in results if r.severity == "critical"]
    critical_total = len(critical_results)
    critical_passed = sum(1 for r in critical_results if r.passed)

    # Specific category rates
    def _category_rate(cat_name: str) -> float:
        cat_results = [r for r in results if r.category == cat_name]
        if not cat_results:
            return 0.0
        return sum(1 for r in cat_results if r.passed) / len(cat_results)

    # Hallucination rate (inverse of honesty + fabrication pass rate)
    honesty_results = [r for r in results if r.category in ("honesty_under_uncertainty", "fabrication_detection", "temporal_grounding")]
    hallucination_cases = len(honesty_results)
    hallucination_failures = sum(1 for r in honesty_results if not r.passed)

    return {
        "overall": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errored": errored,
            "pass_rate": round(passed / total, 3) if total else 0,
            "avg_score": round(sum(r.score for r in results) / total, 3),
        },
        "category_breakdown": category_breakdown,
        "critical_pass_rate": round(critical_passed / critical_total, 3) if critical_total else 0,
        "hallucination_rate": round(hallucination_failures / hallucination_cases, 3) if hallucination_cases else 0,
        "direct_recall_rate": round(_category_rate("direct_recall"), 3),
        "correction_success_rate": round(_category_rate("correction_handling"), 3),
        "sensitive_restraint_rate": round(_category_rate("sensitive_memory"), 3),
        "isolation_rate": round(_category_rate("multi_user_isolation"), 3),
        "relationship_accuracy": round(_category_rate("relational_nuance"), 3),
    }
