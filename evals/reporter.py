from __future__ import annotations
from evals.schema import EvalResult


def generate_report(
    results: list[EvalResult],
    scores: dict,
    label: str = "Baseline (Brain A)",
    comparison_scores: dict | None = None,
    comparison_label: str = "Improved (Brain B)",
) -> str:
    """Generate a markdown benchmark report."""
    lines: list[str] = []
    lines.append(f"# Eval Report: {label}")
    lines.append("")

    overall = scores["overall"]
    lines.append("## Overall Results")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total cases | {overall['total']} |")
    lines.append(f"| Passed | {overall['passed']} |")
    lines.append(f"| Failed | {overall['failed']} |")
    lines.append(f"| Errored | {overall['errored']} |")
    lines.append(f"| Pass rate | {overall['pass_rate']:.1%} |")
    lines.append(f"| Avg score | {overall['avg_score']:.3f} |")
    lines.append("")

    # Key metrics table
    lines.append("## Key Metrics")
    lines.append("")
    if comparison_scores:
        lines.append(f"| Metric | {label} | {comparison_label} |")
        lines.append(f"|---|---|---|")
        lines.append(f"| Critical pass rate | {scores['critical_pass_rate']:.1%} | {comparison_scores['critical_pass_rate']:.1%} |")
        lines.append(f"| Hallucination rate | {scores['hallucination_rate']:.1%} | {comparison_scores['hallucination_rate']:.1%} |")
        lines.append(f"| Direct recall rate | {scores['direct_recall_rate']:.1%} | {comparison_scores['direct_recall_rate']:.1%} |")
        lines.append(f"| Correction success | {scores['correction_success_rate']:.1%} | {comparison_scores['correction_success_rate']:.1%} |")
        lines.append(f"| Sensitive restraint | {scores['sensitive_restraint_rate']:.1%} | {comparison_scores['sensitive_restraint_rate']:.1%} |")
        lines.append(f"| Isolation rate | {scores['isolation_rate']:.1%} | {comparison_scores['isolation_rate']:.1%} |")
        lines.append(f"| Relationship accuracy | {scores['relationship_accuracy']:.1%} | {comparison_scores['relationship_accuracy']:.1%} |")
    else:
        lines.append(f"| Metric | {label} | Target |")
        lines.append(f"|---|---|---|")
        lines.append(f"| Critical pass rate | {scores['critical_pass_rate']:.1%} | 100% |")
        lines.append(f"| Hallucination rate | {scores['hallucination_rate']:.1%} | 0% |")
        lines.append(f"| Direct recall rate | {scores['direct_recall_rate']:.1%} | 90%+ |")
        lines.append(f"| Correction success | {scores['correction_success_rate']:.1%} | 90%+ |")
        lines.append(f"| Sensitive restraint | {scores['sensitive_restraint_rate']:.1%} | - |")
        lines.append(f"| Isolation rate | {scores['isolation_rate']:.1%} | 100% |")
        lines.append(f"| Relationship accuracy | {scores['relationship_accuracy']:.1%} | 85%+ |")
    lines.append("")

    # Category breakdown
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Total | Passed | Pass Rate | Avg Score |")
    lines.append("|---|---|---|---|---|")
    for cat, data in sorted(scores["category_breakdown"].items()):
        lines.append(
            f"| {cat} | {data['total']} | {data['passed']} | "
            f"{data['pass_rate']:.1%} | {data['avg_score']:.3f} |"
        )
    lines.append("")

    # Failed cases detail
    failed = [r for r in results if not r.passed]
    if failed:
        lines.append("## Failed Cases")
        lines.append("")
        lines.append("| Case ID | Category | Severity | Score | Issue |")
        lines.append("|---|---|---|---|---|")
        for r in failed[:30]:
            issue = ""
            if r.error:
                issue = f"ERROR: {r.error[:200]}"
            elif r.rule_checks and r.rule_checks.get("failures"):
                issue = r.rule_checks["failures"][0][:200]
            elif r.judge_assessment:
                issue = r.judge_assessment.get("reasoning", "")[:200]
            lines.append(
                f"| {r.case_id} | {r.category} | {r.severity} | "
                f"{r.score:.2f} | {issue} |"
            )
        lines.append("")

    return "\n".join(lines)
