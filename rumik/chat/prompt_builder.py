from __future__ import annotations


COMPANION_PERSONA = """\
You are Ira, a warm and caring AI companion. You speak naturally in Hinglish \
(a mix of Hindi and English), matching the user's tone and energy.

You are emotionally present, genuine, and direct. You remember things about \
the user and reference them naturally in conversation — like a close friend would."""


def build_system_prompt(
    current_facts: list[dict],
    historical_facts: list[dict] | None = None,
    uncertainty_instructions: str = "",
    sensitivity_instructions: str = "",
) -> str:
    """Construct the full system prompt for Brain B.

    Separates current facts from historical context, and injects
    policy instructions for uncertainty and sensitivity handling.
    """
    sections = [COMPANION_PERSONA, ""]

    if uncertainty_instructions:
        sections.append(uncertainty_instructions)
        sections.append("")

    if sensitivity_instructions:
        sections.append(sensitivity_instructions)
        sections.append("")

    sections.append(_format_current_facts(current_facts))
    sections.append("")

    if historical_facts:
        sections.append(_format_historical_facts(historical_facts))
        sections.append("")

    return "\n".join(sections)


def _format_current_facts(facts: list[dict]) -> str:
    if not facts:
        return (
            "MEMORY (what you know about this user):\n"
            "(You have no stored information about this user yet.)"
        )

    lines = ["MEMORY (what you know about this user — reference these directly):"]
    for f in facts:
        pred = f.get("predicate", "?")
        val = f.get("value", "?")
        source = f.get("source", "unknown")
        confidence = f.get("confidence", "?")

        tags = []
        if source != "user_stated":
            tags.append(f"source: {source}")
        if isinstance(confidence, (int, float)) and confidence < 0.7:
            tags.append("low confidence")

        disclosure = f.get("_disclosure", "")
        if disclosure == "summarize_only":
            tags.append("SUMMARIZE ONLY")
        elif disclosure == "ask_before_revealing":
            tags.append("ASK BEFORE REVEALING")

        sensitivity = f.get("sensitivity", "none")
        if sensitivity in ("high", "intimate"):
            tags.append("SENSITIVE")

        tag_str = f" [{', '.join(tags)}]" if tags else ""
        lines.append(f"- {pred}: {val}{tag_str}")

    return "\n".join(lines)


def _format_historical_facts(facts: list[dict]) -> str:
    if not facts:
        return ""

    lines = [
        "HISTORICAL CONTEXT (past values — only reference if user asks about the past):"
    ]
    for f in facts:
        pred = f.get("predicate", "?")
        val = f.get("value", "?")
        status = f.get("status", "?")
        lines.append(f"- {pred}: {val} (was: {status})")

    return "\n".join(lines)
