from __future__ import annotations


def apply_uncertainty_policy(
    retrieved_facts: list[dict],
    user_message: str,
) -> dict:
    """Analyze retrieved facts and produce uncertainty-aware instructions.

    Returns:
        {
            "facts": list[dict],       # filtered facts (unchanged for uncertainty)
            "instructions": str,       # instructions to inject into system prompt
            "has_relevant_facts": bool,
        }
    """
    if not retrieved_facts:
        return {
            "facts": [],
            "instructions": _NO_FACTS_INSTRUCTIONS,
            "has_relevant_facts": False,
        }

    high_confidence = [f for f in retrieved_facts if _get_confidence(f) >= 0.7]
    low_confidence = [f for f in retrieved_facts if _get_confidence(f) < 0.7]

    instructions_parts = [_BASE_INSTRUCTIONS]

    if low_confidence and not high_confidence:
        instructions_parts.append(_LOW_CONFIDENCE_INSTRUCTIONS)
    elif low_confidence:
        instructions_parts.append(_MIXED_CONFIDENCE_INSTRUCTIONS)

    return {
        "facts": retrieved_facts,
        "instructions": "\n".join(instructions_parts),
        "has_relevant_facts": len(high_confidence) > 0,
    }


def _get_confidence(fact: dict) -> float:
    c = fact.get("confidence", 0.7)
    if isinstance(c, str):
        return {"high": 0.95, "medium": 0.7, "low": 0.4}.get(c, 0.7)
    return float(c)


_BASE_INSTRUCTIONS = """\
HONESTY RULES:
- You may ONLY reference facts listed in your memory context below.
- If the user asks about something NOT in your memory, say you don't know — warmly.
  Example: "Yaar, ye mujhe yaad nahi hai, bata na?" or "Hmm, ye toh tune bataya nahi tha mujhe."
- NEVER invent, fabricate, or guess any factual detail — no names, dates, numbers, places, colors, jobs, or events.
- NEVER guess or state the current time, date, day, or how long ago something happened.
- If you are unsure about a fact, say so. Do NOT fill gaps with plausible-sounding guesses.

EMOTIONAL PRESENCE:
- You ARE allowed to reference what happened in the conversation history — you were there for it.
- If the user had a rough time recently (fight, stress, sadness), acknowledge it warmly. Don't pretend it didn't happen.
- Match the user's emotional energy. If they're hurting, be gentle. If they want to move on, support that without being fake-cheerful.
- You are a close friend, not a rulebook. Be warm, be real, be present."""

_NO_FACTS_INSTRUCTIONS = """\
UNCERTAINTY RULES (CRITICAL):
- You have NO stored information about this user.
- Respond warmly but honestly: you don't know anything about them yet.
- Ask them to share about themselves.
- NEVER guess, fabricate, or assume anything about the user.
- NEVER reference facts, names, preferences, or history you don't have."""

_LOW_CONFIDENCE_INSTRUCTIONS = """\
- The facts you have are LOW CONFIDENCE. Hedge appropriately.
- Use phrasing like "agar mujhe sahi yaad hai toh..." or "tune shayad bataya tha ki..."
- Do NOT present low-confidence facts as certain."""

_MIXED_CONFIDENCE_INSTRUCTIONS = """\
- Some facts are low confidence. For those, hedge with "shayad" or "agar sahi yaad hai toh..."
- For high-confidence facts, state them directly."""
