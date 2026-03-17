from __future__ import annotations
import sqlite3
import uuid
import re
from datetime import datetime


class MemoryStore:
    """SQLite-backed structured fact store with per-user isolation."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id   TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                canonical_name TEXT NOT NULL,
                entity_type TEXT DEFAULT 'unknown',
                aliases     TEXT DEFAULT '[]',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
                fact_id         TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                entity_id       TEXT,
                predicate       TEXT NOT NULL,
                value           TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT 'user_stated',
                status          TEXT NOT NULL DEFAULT 'current',
                confidence      REAL NOT NULL DEFAULT 1.0,
                sensitivity     TEXT NOT NULL DEFAULT 'none',
                memory_form     TEXT NOT NULL DEFAULT 'atomic',
                supersedes      TEXT,
                valid_from      TEXT,
                valid_until     TEXT,
                context_summary TEXT,
                conversation_id TEXT,
                created_at      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id);
            CREATE INDEX IF NOT EXISTS idx_facts_user_status ON facts(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity_id);
            CREATE INDEX IF NOT EXISTS idx_entities_user ON entities(user_id);
        """)
        self.conn.commit()

    # --- Entity operations ---

    def add_entity(
        self,
        user_id: str,
        canonical_name: str,
        entity_type: str = "unknown",
        aliases: list[str] | None = None,
    ) -> str:
        entity_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO entities (entity_id, user_id, canonical_name, entity_type, aliases, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entity_id, user_id, canonical_name, entity_type,
             str(aliases or []), datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return entity_id

    def find_entity(self, user_id: str, name: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM entities WHERE user_id = ? AND (canonical_name = ? OR aliases LIKE ?)",
            (user_id, name, f"%{name}%"),
        ).fetchone()
        return dict(row) if row else None

    # --- Fact operations ---

    def add_fact(
        self,
        user_id: str,
        predicate: str,
        value: str,
        source: str = "user_stated",
        status: str = "current",
        confidence: float = 1.0,
        sensitivity: str = "none",
        memory_form: str = "atomic",
        entity_id: str | None = None,
        supersedes: str | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
        context_summary: str | None = None,
        conversation_id: str | None = None,
    ) -> str:
        fact_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO facts "
            "(fact_id, user_id, entity_id, predicate, value, source, status, confidence, "
            "sensitivity, memory_form, supersedes, valid_from, valid_until, context_summary, "
            "conversation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fact_id, user_id, entity_id, predicate, value, source, status,
             confidence, sensitivity, memory_form, supersedes, valid_from,
             valid_until, context_summary, conversation_id,
             datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return fact_id

    def get_facts(
        self,
        user_id: str,
        status: str | None = "current",
        predicate: str | None = None,
        entity_id: str | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM facts WHERE user_id = ?"
        params: list = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY created_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_all_facts(self, user_id: str) -> list[dict]:
        """Get all facts including stale/corrected (for debug view)."""
        return self.get_facts(user_id, status=None)

    def search_facts(self, user_id: str, search_text: str, status: str = "current") -> list[dict]:
        """Keyword search across predicate and value fields."""
        query = (
            "SELECT * FROM facts WHERE user_id = ? AND status = ? "
            "AND (LOWER(predicate) LIKE ? OR LOWER(value) LIKE ?) "
            "ORDER BY created_at DESC"
        )
        pattern = f"%{search_text.lower()}%"
        rows = self.conn.execute(query, (user_id, status, pattern, pattern)).fetchall()
        return [dict(r) for r in rows]

    def find_fact(self, user_id: str, predicate: str, status: str = "current") -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM facts WHERE user_id = ? AND predicate = ? AND status = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id, predicate, status),
        ).fetchone()
        return dict(row) if row else None

    def update_fact_status(self, fact_id: str, new_status: str):
        self.conn.execute(
            "UPDATE facts SET status = ? WHERE fact_id = ?",
            (new_status, fact_id),
        )
        self.conn.commit()

    def get_correction_chain(self, fact_id: str) -> list[dict]:
        """Follow the supersedes chain backwards to build correction history."""
        chain = []
        current_id = fact_id
        while current_id:
            row = self.conn.execute(
                "SELECT * FROM facts WHERE fact_id = ?", (current_id,)
            ).fetchone()
            if not row:
                break
            chain.append(dict(row))
            current_id = dict(row).get("supersedes")
        return chain

    # --- Eval seeding ---

    def seed_from_eval(self, user_id: str, memory_state: list[dict]):
        """Bulk-load eval case memory_state into structured facts.

        Parses key naming conventions:
          *_current / *_now   -> status=current
          *_old / *_previous / *_was -> status=corrected
          Otherwise           -> status=current

        Groups paired keys (e.g. nickname_current + nickname_old) and creates
        supersession chains between them.
        """
        grouped: dict[str, list[dict]] = {}
        for item in memory_state:
            key = item.get("key", "")
            base_key, temporal_tag = self._parse_key(key)
            if base_key not in grouped:
                grouped[base_key] = []
            grouped[base_key].append({**item, "_temporal": temporal_tag, "_original_key": key})

        for base_key, items in grouped.items():
            old_items = [i for i in items if i["_temporal"] in ("old", "previous", "was", "corrected")]
            current_items = [i for i in items if i["_temporal"] in ("current", "now", "")]

            old_fact_ids = []
            for item in old_items:
                fid = self.add_fact(
                    user_id=user_id,
                    predicate=base_key,
                    value=item.get("value", ""),
                    source=item.get("source", "user_stated"),
                    status="corrected",
                    confidence=self._parse_confidence(item.get("confidence", "high")),
                    sensitivity=self._parse_sensitivity(item.get("sensitive", False)),
                )
                old_fact_ids.append(fid)

            for item in current_items:
                supersedes_id = old_fact_ids[-1] if old_fact_ids else None
                self.add_fact(
                    user_id=user_id,
                    predicate=item.get("_original_key", base_key) if not current_items else base_key,
                    value=item.get("value", ""),
                    source=item.get("source", "user_stated"),
                    status="current",
                    confidence=self._parse_confidence(item.get("confidence", "high")),
                    sensitivity=self._parse_sensitivity(item.get("sensitive", False)),
                    supersedes=supersedes_id,
                )

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        """Split 'nickname_current' -> ('nickname', 'current')."""
        suffixes = ["_current", "_now", "_old", "_previous", "_was", "_corrected"]
        for suffix in suffixes:
            if key.endswith(suffix):
                return key[: -len(suffix)], suffix.lstrip("_")
        return key, ""

    @staticmethod
    def _parse_confidence(val) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        mapping = {"high": 0.95, "medium": 0.7, "low": 0.4}
        return mapping.get(str(val).lower(), 0.7)

    @staticmethod
    def _parse_sensitivity(val) -> str:
        if isinstance(val, bool):
            return "high" if val else "none"
        if isinstance(val, str):
            return val if val in ("none", "moderate", "high", "intimate") else "none"
        return "none"

    # --- Cleanup ---

    def clear_user(self, user_id: str):
        self.conn.execute("DELETE FROM facts WHERE user_id = ?", (user_id,))
        self.conn.execute("DELETE FROM entities WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
