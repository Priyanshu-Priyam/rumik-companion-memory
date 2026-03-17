"""CLI entry point for running the eval suite.

Usage:
    python -m evals.run_evals --brain baseline --output results/baseline.json
    python -m evals.run_evals --brain improved --output results/improved.json
    python -m evals.run_evals --brain baseline --category direct_recall
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

from evals.loader import load_suite, filter_cases
from evals.runner import run_suite
from evals.scorer import aggregate
from evals.reporter import generate_report


def main():
    parser = argparse.ArgumentParser(description="Run Rumik eval suite")
    parser.add_argument(
        "--brain", choices=["baseline", "improved"], default="baseline",
        help="Which brain to evaluate",
    )
    parser.add_argument(
        "--suite", default="evals/golden_suite.jsonl",
        help="Path to eval suite JSONL",
    )
    parser.add_argument("--output", default=None, help="Save results JSON to this path")
    parser.add_argument("--report", default=None, help="Save markdown report to this path")
    parser.add_argument("--category", default=None, help="Filter to specific category")
    parser.add_argument("--severity", default=None, help="Filter to specific severity")
    parser.add_argument("--model", default=None, help="Override model ID for this run")

    args = parser.parse_args()

    # Load eval suite
    print(f"Loading eval suite from {args.suite}...")
    cases = load_suite(args.suite)
    print(f"  Loaded {len(cases)} cases")

    if args.category:
        cases = filter_cases(cases, category=args.category)
        print(f"  Filtered to {len(cases)} cases (category={args.category})")

    if args.severity:
        cases = filter_cases(cases, severity=args.severity)
        print(f"  Filtered to {len(cases)} cases (severity={args.severity})")

    if not cases:
        print("No cases to run. Exiting.")
        sys.exit(0)

    # Instantiate brain
    print(f"\nInstantiating brain: {args.brain}...")
    if args.brain == "baseline":
        from rumik.baseline.engine import BaselineEngine
        brain = BaselineEngine(model_id=args.model)
    else:
        try:
            from rumik.chat.engine import ImprovedEngine
            brain = ImprovedEngine(
                model_id=args.model,
                extract_on_chat=False,
            )
        except ImportError:
            print("Brain B (improved) not yet implemented. Use --brain baseline.")
            sys.exit(1)

    # Run
    print(f"\nRunning {len(cases)} eval cases...\n")
    start = time.time()
    results = run_suite(brain, cases)
    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s")

    # Score
    scores = aggregate(results)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    overall = scores["overall"]
    print(f"  Pass rate:  {overall['passed']}/{overall['total']} ({overall['pass_rate']:.1%})")
    print(f"  Avg score:  {overall['avg_score']:.3f}")
    print(f"  Errored:    {overall['errored']}")
    print(f"\n  Critical:   {scores['critical_pass_rate']:.1%}")
    print(f"  Recall:     {scores['direct_recall_rate']:.1%}")
    print(f"  Correction: {scores['correction_success_rate']:.1%}")
    print(f"  Isolation:  {scores['isolation_rate']:.1%}")
    print(f"  Sensitive:  {scores['sensitive_restraint_rate']:.1%}")
    print(f"  Halluc.:    {scores['hallucination_rate']:.1%}")
    print("=" * 60)

    # Save results
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "brain": args.brain,
            "model": args.model or "default",
            "total_cases": len(cases),
            "elapsed_seconds": round(elapsed, 1),
            "scores": scores,
            "results": [r.model_dump() for r in results],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")

    # Save report
    report_path = args.report
    if not report_path and args.output:
        report_path = args.output.replace(".json", "_report.md")

    if report_path:
        label = "Baseline (Brain A)" if args.brain == "baseline" else "Improved (Brain B)"
        report = generate_report(results, scores, label=label)
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
