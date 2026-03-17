from __future__ import annotations
import logging
from datetime import datetime
from rumik.memory.store import MemoryStore
from rumik.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """Orchestrates fact extraction, validation, correction, and storage."""

    def __init__(self, store: MemoryStore, vector_store: VectorStore):
        self.store = store
        self.vs = vector_store

    def seed_from_eval(self, user_id: str, memory_state: list[dict]):
        """Load eval case memory into both stores."""
        self.store.seed_from_eval(user_id, memory_state)

        all_facts = self.store.get_all_facts(user_id)
        vec_batch = []
        for f in all_facts:
            vec_batch.append({
                "fact_id": f["fact_id"],
                "text": f"{f['predicate']}: {f['value']}",
            })
        if vec_batch:
            self.vs.add_facts_bulk(user_id, vec_batch)

    def process_extractions(
        self,
        user_id: str,
        extractions: list[dict],
        conversation_id: str | None = None,
    ) -> list[dict]:
        """Process a batch of extracted facts: validate, resolve conflicts, store.

        Returns a list of action records for debug.
        """
        actions = []
        for ext in extractions:
            ext_type = ext.get("type", "new_fact")
            try:
                if ext_type == "correction":
                    action = self._handle_correction(user_id, ext, conversation_id)
                elif ext_type == "temporal_update":
                    action = self._handle_temporal_update(user_id, ext, conversation_id)
                elif ext_type == "entity_disambiguation":
                    action = self._handle_disambiguation(user_id, ext, conversation_id)
                elif ext_type in ("new_fact", "emotional_context"):
                    action = self._handle_new_fact(user_id, ext, conversation_id)
                else:
                    action = self._handle_new_fact(user_id, ext, conversation_id)
                actions.append(action)
            except Exception as e:
                logger.warning("Failed to process extraction %s: %s", ext, e)
                actions.append({"action": "error", "extraction": ext, "error": str(e)})
        return actions

    def _handle_new_fact(self, user_id: str, ext: dict, conv_id: str | None) -> dict:
        predicate = ext.get("predicate", "unknown")
        value = ext.get("value", "")
        sensitivity = ext.get("sensitivity", "none")

        existing = self.store.find_fact(user_id, predicate, status="current")
        if existing and existing["value"].lower() == value.lower():
            return {"action": "skipped_duplicate", "predicate": predicate, "value": value}

        fact_id = self.store.add_fact(
            user_id=user_id,
            predicate=predicate,
            value=value,
            source=ext.get("source", "user_stated"),
            sensitivity=sensitivity,
            conversation_id=conv_id,
        )

        self.vs.add_fact(user_id, fact_id, f"{predicate}: {value}")
        return {"action": "added", "fact_id": fact_id, "predicate": predicate, "value": value}

    def _handle_correction(self, user_id: str, ext: dict, conv_id: str | None) -> dict:
        predicate = ext.get("predicate", "unknown")
        new_value = ext.get("value", "")
        old_value = ext.get("old_value", "")

        old_fact = self._find_matching_fact(user_id, predicate, old_value)

        supersedes_id = None
        if old_fact:
            self.store.update_fact_status(old_fact["fact_id"], "corrected")
            supersedes_id = old_fact["fact_id"]

        new_fact_id = self.store.add_fact(
            user_id=user_id,
            predicate=predicate,
            value=new_value,
            source=ext.get("source", "user_stated"),
            sensitivity=ext.get("sensitivity", "none"),
            supersedes=supersedes_id,
            conversation_id=conv_id,
        )

        self.vs.add_fact(user_id, new_fact_id, f"{predicate}: {new_value}")

        return {
            "action": "corrected",
            "fact_id": new_fact_id,
            "supersedes": supersedes_id,
            "predicate": predicate,
            "old_value": old_value,
            "new_value": new_value,
        }

    def _handle_temporal_update(self, user_id: str, ext: dict, conv_id: str | None) -> dict:
        predicate = ext.get("predicate", "unknown")
        new_value = ext.get("value", "")

        old_facts = self.store.get_facts(user_id, status="current", predicate=predicate)
        supersedes_id = None
        for old in old_facts:
            self.store.update_fact_status(old["fact_id"], "stale")
            supersedes_id = old["fact_id"]

        now_iso = datetime.utcnow().isoformat()
        new_fact_id = self.store.add_fact(
            user_id=user_id,
            predicate=predicate,
            value=new_value,
            source=ext.get("source", "user_stated"),
            sensitivity=ext.get("sensitivity", "none"),
            supersedes=supersedes_id,
            valid_from=now_iso,
            conversation_id=conv_id,
        )

        self.vs.add_fact(user_id, new_fact_id, f"{predicate}: {new_value}")

        return {
            "action": "temporal_update",
            "fact_id": new_fact_id,
            "supersedes": supersedes_id,
            "predicate": predicate,
            "new_value": new_value,
        }

    def _handle_disambiguation(self, user_id: str, ext: dict, conv_id: str | None) -> dict:
        entity_name = ext.get("entity", "")
        predicate = ext.get("predicate", "")
        new_value = ext.get("value", "")
        old_value = ext.get("old_value", "")

        old_facts = self.store.get_facts(user_id, status="current")
        for f in old_facts:
            if (entity_name.lower() in f["value"].lower() or
                    entity_name.lower() in f["predicate"].lower()):
                if old_value and old_value.lower() in f["value"].lower():
                    self.store.update_fact_status(f["fact_id"], "corrected")

        new_fact_id = self.store.add_fact(
            user_id=user_id,
            predicate=f"{entity_name}_{predicate}" if entity_name != "self" else predicate,
            value=new_value,
            source=ext.get("source", "user_stated"),
            sensitivity=ext.get("sensitivity", "none"),
            conversation_id=conv_id,
        )

        self.vs.add_fact(user_id, new_fact_id, f"{entity_name} {predicate}: {new_value}")

        return {
            "action": "disambiguated",
            "fact_id": new_fact_id,
            "entity": entity_name,
            "predicate": predicate,
            "new_value": new_value,
            "old_value": old_value,
        }

    def _find_matching_fact(self, user_id: str, predicate: str, old_value: str) -> dict | None:
        """Find an existing current fact matching the predicate and optionally the old value."""
        exact = self.store.find_fact(user_id, predicate, status="current")
        if exact:
            return exact

        if old_value:
            all_current = self.store.get_facts(user_id, status="current")
            for f in all_current:
                if old_value.lower() in f["value"].lower():
                    return f
                if predicate.lower() in f["predicate"].lower():
                    return f
        return None

    def clear_user(self, user_id: str):
        self.store.clear_user(user_id)
        self.vs.remove_user(user_id)
