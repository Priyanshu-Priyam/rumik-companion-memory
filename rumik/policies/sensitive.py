from __future__ import annotations
import re


def apply_sensitivity_policy(
    facts: list[dict],
    user_message: str,
) -> dict:
    """Filter and annotate facts based on sensitivity level.

    Sensitivity levels and disclosure strategy:
      none     -> include directly, no special handling
      moderate -> include if contextually relevant
      high     -> summarize presence, don't dump details unprompted
      intimate -> only include if user is explicitly asking about it

    Returns:
        {
            "facts": list[dict],          # filtered/annotated facts
            "withheld": list[dict],       # facts withheld due to sensitivity
            "instructions": str,          # sensitivity instructions for prompt
        }
    """
    user_asking_about = _detect_topic(user_message)
    is_emotional_context = _is_emotional_message(user_message)

    included = []
    withheld = []
    has_sensitive = False

    for fact in facts:
        level = fact.get("sensitivity", "none")

        if level == "none":
            included.append(fact)

        elif level == "moderate":
            included.append(fact)

        elif level == "high":
            if _is_fact_relevant_to_topic(fact, user_asking_about) or is_emotional_context:
                fact_copy = dict(fact)
                fact_copy["_disclosure"] = "summarize_only"
                included.append(fact_copy)
                has_sensitive = True
            else:
                withheld.append(fact)
                has_sensitive = True

        elif level == "intimate":
            if _is_fact_relevant_to_topic(fact, user_asking_about):
                fact_copy = dict(fact)
                fact_copy["_disclosure"] = "ask_before_revealing"
                included.append(fact_copy)
                has_sensitive = True
            else:
                withheld.append(fact)
                has_sensitive = True

        else:
            included.append(fact)

    instructions = _build_instructions(has_sensitive, bool(withheld))

    return {
        "facts": included,
        "withheld": withheld,
        "instructions": instructions,
    }


def _detect_topic(message: str) -> list[str]:
    """Extract likely topic keywords from the user's message."""
    tokens = re.findall(r'\w+', message.lower())
    return tokens


def _is_emotional_message(message: str) -> bool:
    emotional_markers = [
        "bahut", "mujhe dar", "anxiety", "stress", "depressed", "sad",
        "ro rahi", "ro raha", "hurt", "pain", "dukhi", "pareshan",
        "help", "madad", "zaruri", "urgent", "please", "cry",
        "self harm", "suicide", "khatam", "mar", "tod",
    ]
    msg_lower = message.lower()
    return any(m in msg_lower for m in emotional_markers)


def _is_fact_relevant_to_topic(fact: dict, topic_tokens: list[str]) -> bool:
    if not topic_tokens:
        return False
    pred = fact.get("predicate", "").lower()
    val = fact.get("value", "").lower()
    fact_text = f"{pred} {val}"
    return any(t in fact_text for t in topic_tokens if len(t) > 2)


def _build_instructions(has_sensitive: bool, has_withheld: bool) -> str:
    if not has_sensitive:
        return ""

    parts = [
        "SENSITIVE MEMORY RULES:",
        "- Some facts about this user are sensitive. Handle with care.",
        "- Do NOT bring up sensitive topics (health, finances, relationships, trauma) unprompted.",
        "- If the user brings up a sensitive topic themselves, respond with empathy and care.",
        "- Facts marked [SUMMARIZE ONLY]: reference them at a high level, don't dump raw details.",
        "- Facts marked [ASK BEFORE REVEALING]: only discuss if the user explicitly asks. You may say 'haan, tune kuch share kiya tha, kya us baare mein baat karni hai?'",
    ]

    if has_withheld:
        parts.append(
            "- You are aware the user has shared some private things in the past. "
            "If they ask 'kya tujhe yaad hai?', you can acknowledge you remember "
            "without revealing specifics: 'haan, tune kuch personal cheezein share ki thi.'"
        )

    return "\n".join(parts)
