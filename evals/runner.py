from __future__ import annotations
import time
import traceback
from rumik.brain import CompanionBrain
from evals.schema import EvalCase, EvalResult
from evals.judges.rule_judge import judge_rule
from evals.judges.llm_judge import judge_llm


def run_eval(brain: CompanionBrain, case: EvalCase) -> EvalResult:
    """Run a single eval case against a brain and return the result."""
    user_id = case.user_profile

    try:
        brain.reset(user_id)
        brain.seed_memory(user_id, case.memory_state)

        # Replay conversation history turn by turn
        accumulated_history: list[dict] = []
        for turn in case.history:
            content = turn.get("content", turn.get("message", ""))
            role = turn.get("role", "user")
            if role == "user":
                replay_result = brain.chat(user_id, content, history=accumulated_history)
                accumulated_history.append({"role": "user", "content": content})
                assistant_reply = replay_result.get("response", "")
                accumulated_history.append({"role": "assistant", "content": assistant_reply})
            else:
                accumulated_history.append({"role": role, "content": content})

        # Send the actual test message
        result = brain.chat(user_id, case.user_message, history=accumulated_history)
        response_text = result.get("response", "")
        debug_data = result.get("debug", None)

        # Score the response
        rule_checks = None
        judge_assessment = None

        if case.scoring == "rule":
            rule_checks = judge_rule(
                response_text,
                case.expected_checks,
                case.disallowed_behaviors,
            )
            passed = rule_checks["passed"]
            score = rule_checks["score"]

        elif case.scoring == "llm_judge":
            judge_assessment = judge_llm(response_text, case)
            passed = judge_assessment.get("passed", False)
            score = judge_assessment.get("score", 0.0)

        elif case.scoring == "hybrid":
            rule_checks = judge_rule(
                response_text,
                case.expected_checks,
                case.disallowed_behaviors,
            )
            judge_assessment = judge_llm(response_text, case)

            rule_score = rule_checks["score"]
            judge_score = judge_assessment.get("score", 0.0)
            score = (rule_score * 0.4) + (judge_score * 0.6)

            rule_passed = rule_checks["passed"]
            judge_passed = judge_assessment.get("passed", False)
            if rule_passed and judge_passed:
                passed = True
            elif judge_passed and rule_score >= 0.75:
                passed = True
            else:
                passed = False

        else:
            passed = False
            score = 0.0

        return EvalResult(
            case_id=case.id,
            category=case.category,
            severity=case.severity,
            passed=passed,
            score=score,
            response=response_text,
            rule_checks=rule_checks,
            judge_assessment=judge_assessment,
            debug=debug_data,
        )

    except Exception as e:
        return EvalResult(
            case_id=case.id,
            category=case.category,
            severity=case.severity,
            passed=False,
            score=0.0,
            response="",
            error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
        )


def run_suite(
    brain: CompanionBrain,
    cases: list[EvalCase],
    progress_callback=None,
) -> list[EvalResult]:
    """Run all eval cases and return results."""
    results: list[EvalResult] = []
    total = len(cases)

    for i, case in enumerate(cases):
        if progress_callback:
            progress_callback(i, total, case.id)

        result = run_eval(brain, case)
        results.append(result)

        print(
            f"  [{i+1}/{total}] {case.id:8s} | "
            f"{'PASS' if result.passed else 'FAIL':4s} | "
            f"score={result.score:.2f} | "
            f"{case.category}"
        )

    return results
