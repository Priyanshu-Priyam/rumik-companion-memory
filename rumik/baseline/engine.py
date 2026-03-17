from __future__ import annotations
from rumik.brain import CompanionBrain
from rumik.chat.llm import call_llm, format_messages_for_bedrock

SYSTEM_PERSONA = """\
You are Ira, a warm and caring AI companion. You speak naturally in Hinglish \
(a mix of Hindi and English), matching the user's communication style.

Core rules:
- Be warm, emotionally present, and genuine
- If you remember something about the user, recall it directly and specifically
- If you do NOT remember something, say so honestly and warmly — never fabricate
- Never guess the current time, date, or duration — you don't have access to a live clock
- Never leak information from one user to another
- Treat sensitive information with care — don't dump private context unprompted

Below is everything you know about this user:
{memory_block}
"""


class BaselineEngine(CompanionBrain):
    """Brain A: naive baseline that stuffs all facts into the system prompt."""

    def __init__(self, model_id: str | None = None):
        self._memory: dict[str, list[dict]] = {}
        self._model_id = model_id

    def seed_memory(self, user_id: str, facts: list[dict]) -> None:
        self._memory[user_id] = list(facts)

    def chat(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
    ) -> dict:
        facts = self._memory.get(user_id, [])
        memory_block = self._format_facts(facts) if facts else "(No information stored about this user yet.)"
        system_prompt = SYSTEM_PERSONA.format(memory_block=memory_block)

        conversation: list[dict] = []
        if history:
            for turn in history:
                conversation.append({
                    "role": turn["role"],
                    "content": turn["content"],
                })

        conversation.append({"role": "user", "content": message})

        bedrock_messages = format_messages_for_bedrock(conversation)
        response_text = call_llm(
            messages=bedrock_messages,
            system=system_prompt,
            model=self._model_id,
            temperature=0.7,
            max_tokens=1024,
        )

        return {
            "response": response_text,
            "debug": {
                "system_prompt": system_prompt,
                "facts_used": facts,
                "model_id": self._model_id,
            },
        }

    def reset(self, user_id: str) -> None:
        self._memory.pop(user_id, None)

    @staticmethod
    def _format_facts(facts: list[dict]) -> str:
        lines = []
        for f in facts:
            key = f.get("key", "unknown")
            value = f.get("value", "")
            source = f.get("source", "unknown")
            confidence = f.get("confidence", "unknown")
            sensitive = f.get("sensitive", False)
            sensitivity_tag = " [SENSITIVE]" if sensitive else ""
            lines.append(
                f"- {key}: {value} (source: {source}, confidence: {confidence}){sensitivity_tag}"
            )
        return "\n".join(lines)
