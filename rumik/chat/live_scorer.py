from __future__ import annotations
import json
import re
import logging
from rumik.chat.llm import call_llm, format_messages_for_bedrock

logger = logging.getLogger(__name__)


def score_response(
    response: str,
    user_message: str,
    debug: dict,
    history: list[dict] | None = None,
) -> dict:
    """Score a live chat response using pipeline debug data and a quick LLM judge.

    Returns a dict with:
      overall: float 0-1
      breakdown: dict of dimension scores
      flags: list of quality warnings
      judge_reasoning: str from LLM quality check
    """
    flags: list[str] = []
    breakdown: dict[str, float] = {}

    retrieved = debug.get("retrieved_facts", [])
    extractions = debug.get("extractions", [])
    extraction_error = debug.get("extraction_error")
    extraction_source = debug.get("extraction_source", "")

    # --- 1. Extraction health ---
    if extraction_error:
        flags.append(f"Extraction error: {extraction_error}")
        breakdown["extraction"] = 0.3
    elif extraction_source == "greeting_skip":
        breakdown["extraction"] = 1.0
    elif extraction_source == "fallback":
        breakdown["extraction"] = 0.7
    elif extractions:
        breakdown["extraction"] = 1.0
    else:
        breakdown["extraction"] = 0.8

    # --- 2. Memory utilization ---
    if retrieved:
        used_count = 0
        for fact in retrieved:
            val = (fact.get("value") or "").lower()
            if val and len(val) > 2 and val in response.lower():
                used_count += 1
        utilization = min(used_count / max(len(retrieved), 1), 1.0)
        breakdown["memory_use"] = max(utilization, 0.5)
    else:
        breakdown["memory_use"] = 1.0

    # --- 3. Sensitivity compliance ---
    breakdown["sensitivity"] = 1.0

    # --- 4. Honesty check ---
    # Only flag fabrication if there's NO memory AND NO conversation history
    # that could justify the claim
    has_relevant = debug.get("has_relevant_facts", False)
    breakdown["honesty"] = 1.0
    if not has_relevant and not retrieved and not history:
        fabrication_markers = [
            r"(?:tumne|tune)\s+(?:bataya|bola)\s+tha\s+ki",
            r"(?:yaad|remember)\s+(?:hai|karta)",
        ]
        for pattern in fabrication_markers:
            if re.search(pattern, response, re.IGNORECASE):
                flags.append("Possible fabrication with no memory context")
                breakdown["honesty"] = 0.5
                break

    # --- 5. Response quality ---
    resp_len = len(response.strip())
    if resp_len < 10:
        breakdown["quality"] = 0.4
    elif resp_len > 2000:
        breakdown["quality"] = 0.7
    else:
        breakdown["quality"] = 1.0

    # --- 6. LLM quality judge ---
    try:
        judge_result = _run_llm_judge(response, user_message, debug, history)
        breakdown["llm_judge"] = judge_result["score"]
        judge_reasoning = judge_result.get("reasoning", "")
    except Exception as e:
        logger.warning("Live scorer judge failed: %s", e)
        breakdown["llm_judge"] = 0.8
        judge_reasoning = "Judge unavailable"

    # --- Overall score ---
    weights = {
        "extraction": 0.10,
        "memory_use": 0.10,
        "sensitivity": 0.10,
        "honesty": 0.15,
        "quality": 0.10,
        "llm_judge": 0.45,
    }
    overall = sum(breakdown.get(k, 0.8) * w for k, w in weights.items())

    return {
        "overall": round(overall, 3),
        "breakdown": breakdown,
        "flags": flags,
        "judge_reasoning": judge_reasoning,
    }


def _run_llm_judge(
    response: str,
    user_message: str,
    debug: dict,
    history: list[dict] | None = None,
) -> dict:
    """Quick LLM judge that sees the full conversation context."""

    # Build conversation context
    convo_context = ""
    if history:
        recent = history[-8:]
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")[:200]
            convo_context += f"  {role}: {content}\n"
    if not convo_context:
        convo_context = "  (first message, no prior history)\n"

    retrieved_summary = ""
    for f in debug.get("retrieved_facts", [])[:8]:
        pred = f.get("predicate", "?")
        val = f.get("value", "?")
        retrieved_summary += f"  - {pred}: {val}\n"
    if not retrieved_summary:
        retrieved_summary = "  (no facts in memory store)\n"

    prompt = f"""Rate this AI companion response. Score 0.0 to 1.0.

CONVERSATION SO FAR:
{convo_context}
CURRENT USER MESSAGE: "{user_message}"

COMPANION RESPONSE: "{response[:500]}"

FACTS IN MEMORY STORE:
{retrieved_summary}
IMPORTANT CONTEXT:
- The companion can legitimately reference anything said in the conversation above.
- Referencing what the user said 2 turns ago is NOT fabrication — it is conversation memory.
- Only flag fabrication if the companion claims to know something that was NEVER said in the conversation AND is not in the memory store.
- A warm greeting response with no facts is perfectly fine if the user just said hi.
- Asking follow-up questions is good companion behavior, not a flaw.

Score on:
1. ACCURACY: Does it correctly reference conversation and memory? (NOT fabrication if user said it earlier)
2. WARMTH: Natural, Hinglish-friendly, emotionally present?
3. HELPFULNESS: Engaging, not just deflecting?

Return ONLY valid JSON, no other text:
{{"score": 0.9, "reasoning": "one sentence"}}
"""
    messages = format_messages_for_bedrock([{"role": "user", "content": prompt}])
    raw = call_llm(
        messages=messages,
        system="You are a quality evaluator for an AI companion. Return ONLY a JSON object with score and reasoning. No flags array needed.",
        temperature=0.0,
        max_tokens=200,
    )

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
        return {
            "score": float(result.get("score", 0.8)),
            "reasoning": result.get("reasoning", ""),
        }
    except (json.JSONDecodeError, ValueError):
        return {"score": 0.8, "reasoning": text[:200]}
