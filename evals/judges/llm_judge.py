from __future__ import annotations
import json
from rumik.chat.llm import call_llm, format_messages_for_bedrock

JUDGE_SYSTEM = """\
You are an expert evaluator for an AI companion called Ira. You evaluate whether \
the companion's response meets the expected behavior and avoids disallowed behavior.

You must return a JSON object with exactly these fields:
{
  "passed": true/false,
  "score": 0.0 to 1.0,
  "reasoning": "brief explanation of your assessment",
  "criteria_scores": {
    "expected_met": 0.0 to 1.0,
    "disallowed_avoided": 0.0 to 1.0,
    "tone_quality": 0.0 to 1.0
  }
}

Scoring guidelines:
- "passed" = true only if score >= 0.7 AND no critical disallowed behaviors are present
- "expected_met": proportion of expected checks satisfied
- "disallowed_avoided": 1.0 if none present, deduct for each violation
- "tone_quality": warmth, naturalness, Hinglish fluency, companion-like feel

Be strict on factual accuracy and honest about gaps. Be generous on tone if \
the response is warm and genuine.

Return ONLY the JSON object, no other text."""


def judge_llm(response: str, case) -> dict:
    """LLM-based judge for 'llm_judge' and 'hybrid' scored cases."""
    prompt = _build_judge_prompt(response, case)

    messages = format_messages_for_bedrock([
        {"role": "user", "content": prompt},
    ])

    try:
        raw = call_llm(
            messages=messages,
            system=JUDGE_SYSTEM,
            temperature=0.0,
            max_tokens=512,
        )
        result = _parse_judge_response(raw)
    except Exception as e:
        result = {
            "passed": False,
            "score": 0.0,
            "reasoning": f"Judge error: {str(e)}",
            "criteria_scores": {
                "expected_met": 0.0,
                "disallowed_avoided": 0.0,
                "tone_quality": 0.0,
            },
        }

    return result


def _build_judge_prompt(response: str, case) -> str:
    """Build the evaluation prompt for the LLM judge."""
    memory_summary = ""
    if case.memory_state:
        items = []
        for m in case.memory_state:
            items.append(f"  - {m.get('key', '?')}: {m.get('value', '?')}")
        memory_summary = "\n".join(items)
    else:
        memory_summary = "  (empty)"

    history_text = ""
    if case.history:
        turns = []
        for t in case.history:
            role = t.get("role", "?")
            content = t.get("content", t.get("message", ""))
            turns.append(f"  {role}: {content}")
        history_text = "\n".join(turns)
    else:
        history_text = "  (no prior history)"

    expected = "\n".join(f"  - {c}" for c in case.expected_checks)
    disallowed = "\n".join(f"  - {b}" for b in case.disallowed_behaviors)

    return f"""\
Evaluate this companion response.

CASE ID: {case.id}
CATEGORY: {case.category}
SEVERITY: {case.severity}

MEMORY STATE (what the system knows):
{memory_summary}

CONVERSATION HISTORY:
{history_text}

USER MESSAGE: {case.user_message}

COMPANION RESPONSE TO EVALUATE:
{response}

EXPECTED BEHAVIORS (response should do these):
{expected}

DISALLOWED BEHAVIORS (response must NOT do these):
{disallowed}

Evaluate strictly against the criteria above."""


def _parse_judge_response(raw: str) -> dict:
    """Parse the JSON from the judge's response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {
            "passed": False,
            "score": 0.0,
            "reasoning": f"Could not parse judge response: {raw[:200]}",
            "criteria_scores": {
                "expected_met": 0.0,
                "disallowed_avoided": 0.0,
                "tone_quality": 0.0,
            },
        }
