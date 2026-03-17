from __future__ import annotations
from abc import ABC, abstractmethod


class CompanionBrain(ABC):
    @abstractmethod
    def seed_memory(self, user_id: str, facts: list[dict]) -> None:
        """Pre-load memory state for a test case."""

    @abstractmethod
    def chat(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
    ) -> dict:
        """Send message, get response + debug metadata."""

    @abstractmethod
    def reset(self, user_id: str) -> None:
        """Clear all state for this user."""
