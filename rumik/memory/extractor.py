from __future__ import annotations
import json
import logging
import re
from rumik.chat.llm import call_llm, format_messages_for_bedrock

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """\
You are a memory extraction engine for an AI companion app. Your job is to \
parse a user's message and extract structured facts, corrections, and queries.

The user speaks in Hinglish (a mix of Hindi and English). You must handle \
both languages fluently.

Return a JSON array of extraction objects. Each object has these fields:
{
  "type": "new_fact" | "correction" | "temporal_update" | "entity_disambiguation" | "emotional_context",
  "entity": "name of the person/thing this fact is about (or 'self' for user)",
  "predicate": "what aspect this fact describes (e.g. 'nickname', 'pet_species', 'weight')",
  "value": "the current/new value",
  "old_value": "the previous value being corrected (only for correction/temporal_update)",
  "source": "user_stated",
  "sensitivity": "none" | "moderate" | "high" | "intimate"
}

CRITICAL RULES:
1. Extract ALL facts the user EXPLICITLY states — names, places, relationships, \
preferences, routines, emotions, corrections, etc. Even one-word introductions \
like "I am Rohan" or "hamara naam Priyanshu hai" contain a name fact.
2. For corrections, you MUST include both old_value and new value.
3. Sensitivity levels:
   - "none": general facts (name, hobbies, pets)
   - "moderate": personal but not private (weight, routines, relationships)
   - "high": private (health issues, family conflicts, financial stress)
   - "intimate": deeply personal (self-harm, trauma, sexual topics)
4. ONLY return [] if the message is purely a greeting with zero factual content \
(e.g. "hi", "hey", "kya haal hai", "what's up"). If the user states ANYTHING \
about themselves, their life, people, places, or preferences, you MUST extract it.
5. Return ONLY the JSON array, no other text.

EXAMPLES:

User: "I am Priyanshu"
[
  {"type": "new_fact", "entity": "self", "predicate": "name", "value": "Priyanshu", "old_value": null, "source": "user_stated", "sensitivity": "none"}
]

User: "hamara naam Rohan hai"
[
  {"type": "new_fact", "entity": "self", "predicate": "name", "value": "Rohan", "old_value": null, "source": "user_stated", "sensitivity": "none"}
]

User: "Mera naam Rohan hai aur main Delhi se hoon"
[
  {"type": "new_fact", "entity": "self", "predicate": "name", "value": "Rohan", "old_value": null, "source": "user_stated", "sensitivity": "none"},
  {"type": "new_fact", "entity": "self", "predicate": "city", "value": "Delhi", "old_value": null, "source": "user_stated", "sensitivity": "none"}
]

User: "Tum mujhe Rocky bol rahi thi, but mera nickname Daredevil hai. Rocky school mein tha, ab se Daredevil yaad rakhna."
[
  {"type": "correction", "entity": "self", "predicate": "nickname", "value": "Daredevil", "old_value": "Rocky", "source": "user_stated", "sensitivity": "none"}
]

User: "Divya pehle meri crush thi, but ab meri girlfriend hai. Agli baar usse crush mat bolna."
[
  {"type": "correction", "entity": "Divya", "predicate": "relationship_status", "value": "girlfriend", "old_value": "crush", "source": "user_stated", "sensitivity": "moderate"}
]

User: "Spark mera rat nahi hai. Spark hamster hai. Mera rat alag hai, uska naam Pixel hai."
[
  {"type": "entity_disambiguation", "entity": "Spark", "predicate": "species", "value": "hamster", "old_value": "rat", "source": "user_stated", "sensitivity": "none"},
  {"type": "new_fact", "entity": "Pixel", "predicate": "species", "value": "rat", "old_value": null, "source": "user_stated", "sensitivity": "none"},
  {"type": "new_fact", "entity": "Pixel", "predicate": "relationship", "value": "user's pet", "old_value": null, "source": "user_stated", "sensitivity": "none"}
]

User: "Mera weight pehle 110 tha, last month 92 tha, aur ab 88 hai."
[
  {"type": "temporal_update", "entity": "self", "predicate": "weight", "value": "88", "old_value": "110, then 92", "source": "user_stated", "sensitivity": "moderate"}
]

User: "Pehle main shaam ko tea aur burger leta tha, but ab green tea aur makhana leta hoon."
[
  {"type": "correction", "entity": "self", "predicate": "evening_routine", "value": "green tea and makhana", "old_value": "tea and burger", "source": "user_stated", "sensitivity": "none"}
]

User: "Rakesh pehle basketball captain tha, but ab captain Arjun hai. Rakesh ab bhi dost hai, bas role change ho gaya hai."
[
  {"type": "correction", "entity": "Rakesh", "predicate": "role", "value": "friend (no longer captain)", "old_value": "basketball captain", "source": "user_stated", "sensitivity": "none"},
  {"type": "correction", "entity": "Arjun", "predicate": "role", "value": "basketball captain", "old_value": null, "source": "user_stated", "sensitivity": "none"}
]

User: "Kya haal hai?"
[]

User: "Mujhe bahut anxiety ho rahi hai health ko lekar"
[
  {"type": "emotional_context", "entity": "self", "predicate": "health_anxiety", "value": "experiencing health anxiety", "old_value": null, "source": "user_stated", "sensitivity": "high"}
]
"""

_GREETING_PATTERNS = re.compile(
    r"^(hi|hey|hello|yo|sup|kya hal|kaise ho|what'?s up|hola|namaste|"
    r"hey hey|kya haal|howdy|good morning|good evening|morning|haan)"
    r"[\s!?.]*$",
    re.IGNORECASE,
)

_NAME_PATTERN = re.compile(
    r"(?:(?:mera|hamara|my)\s+(?:naam|name)\s+(?:hai\s+)?(\w+))|"
    r"(?:(?:i\s+am|i'm|main\s+hoon|mai\s+hu|naam\s+hai)\s+(\w+))|"
    r"(?:(\w+)\s+(?:hai\s+)?(?:mera|hamara)\s+naam)",
    re.IGNORECASE,
)

_CITY_PATTERN = re.compile(
    r"(?:(?:main|mai|i)\s+(?:.*?\s+)?(?:se\s+hoon|mein\s+rehta|mein\s+rehti|"
    r"se\s+hu|from|in)\s+(\w+))|"
    r"(?:(\w+)\s+(?:se\s+hoon|mein\s+rehta|mein\s+rehti|se\s+hu))",
    re.IGNORECASE,
)


def _is_pure_greeting(message: str) -> bool:
    return bool(_GREETING_PATTERNS.match(message.strip()))


def _fallback_extract(message: str) -> list[dict]:
    """Regex-based fallback for common facts when LLM extraction returns empty."""
    results = []

    name_match = _NAME_PATTERN.search(message)
    if name_match:
        name = name_match.group(1) or name_match.group(2) or name_match.group(3)
        if name and len(name) > 1:
            results.append({
                "type": "new_fact",
                "entity": "self",
                "predicate": "name",
                "value": name.strip(),
                "old_value": None,
                "source": "user_stated",
                "sensitivity": "none",
            })

    city_match = _CITY_PATTERN.search(message)
    if city_match:
        city = city_match.group(1) or city_match.group(2)
        if city and len(city) > 1 and city.lower() not in ("main", "mai", "i", "mein"):
            results.append({
                "type": "new_fact",
                "entity": "self",
                "predicate": "city",
                "value": city.strip(),
                "old_value": None,
                "source": "user_stated",
                "sensitivity": "none",
            })

    return results


class FactExtractor:
    """LLM-based fact extractor with retry and regex fallback."""

    def __init__(self, model_id: str | None = None):
        self._model_id = model_id

    def extract(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
    ) -> dict:
        """Extract structured facts from a user message.

        Returns a dict with:
          results: list of extraction dicts
          raw_response: the raw LLM output (for debugging)
          error: error message if extraction failed, else None
          source: 'llm' | 'llm_retry' | 'fallback'
        """
        if _is_pure_greeting(message):
            return {"results": [], "raw_response": "[]", "error": None, "source": "greeting_skip"}

        context_turns = ""
        if history:
            recent = history[-6:]
            lines = []
            for t in recent:
                role = t.get("role", "user")
                content = t.get("content", "")
                lines.append(f"{role}: {content}")
            context_turns = "\n".join(lines) + "\n\n"

        prompt = f"{context_turns}User: {message}"

        messages = format_messages_for_bedrock([
            {"role": "user", "content": prompt},
        ])

        # Attempt 1
        parsed, raw, error = self._call_extraction(messages)
        if parsed:
            return {"results": parsed, "raw_response": raw, "error": None, "source": "llm"}

        # Attempt 2 (retry) — only if the message has real content
        if not error and len(message.split()) >= 2:
            logger.info("Extraction returned empty for non-trivial message, retrying: %s", message[:60])
            parsed2, raw2, error2 = self._call_extraction(messages)
            if parsed2:
                return {"results": parsed2, "raw_response": raw2, "error": None, "source": "llm_retry"}
            raw = raw2 or raw
            error = error2

        # Attempt 3 (regex fallback)
        fallback = _fallback_extract(message)
        if fallback:
            logger.info("Using regex fallback extraction for: %s", message[:60])
            return {"results": fallback, "raw_response": raw, "error": error, "source": "fallback"}

        return {"results": [], "raw_response": raw, "error": error, "source": "empty"}

    def _call_extraction(self, messages: list[dict]) -> tuple:
        """Single LLM extraction call. Returns (parsed, raw, error)."""
        try:
            raw = call_llm(
                messages=messages,
                system=EXTRACTION_SYSTEM,
                model=self._model_id,
                temperature=0.0,
                max_tokens=1024,
            )
            parsed = self._parse_response(raw)
            return parsed, raw, None
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            logger.warning("Extraction failed: %s", error_msg)
            return [], None, error_msg

    @staticmethod
    def _parse_response(raw: str) -> list[dict]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Could not parse extraction response: %s", text[:200])
            return []
