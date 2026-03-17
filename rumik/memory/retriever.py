from __future__ import annotations
import re
import math
from datetime import datetime
from rumik.memory.store import MemoryStore
from rumik.memory.vector_store import VectorStore


class HybridRetriever:
    """Combines SQLite keyword lookup with ChromaDB semantic search, then ranks."""

    RELEVANCE_W = 0.4
    RECENCY_W = 0.3
    CONFIDENCE_W = 0.2
    SOURCE_W = 0.1

    SOURCE_WEIGHTS = {
        "user_stated": 1.0,
        "inferred": 0.7,
        "guessed": 0.3,
    }

    def __init__(self, store: MemoryStore, vector_store: VectorStore):
        self.store = store
        self.vs = vector_store

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 15,
        include_historical: bool = False,
    ) -> list[dict]:
        """Retrieve and rank facts relevant to the query.

        Returns list of dicts with keys: fact + retrieval_score + retrieval_source.
        """
        scored: dict[str, dict] = {}

        current_facts = self.store.get_facts(user_id, status="current")
        for f in current_facts:
            fid = f["fact_id"]
            keyword_score = self._keyword_relevance(query, f)
            scored[fid] = {
                **f,
                "_relevance": keyword_score,
                "_source": "structured",
            }

        if include_historical:
            historical = self.store.get_facts(user_id, status="corrected")
            historical += self.store.get_facts(user_id, status="stale")
            for f in historical:
                fid = f["fact_id"]
                if fid not in scored:
                    keyword_score = self._keyword_relevance(query, f)
                    scored[fid] = {
                        **f,
                        "_relevance": keyword_score * 0.5,
                        "_source": "structured_historical",
                    }

        semantic_hits = self.vs.query(user_id, query, top_k=top_k * 2)
        for hit in semantic_hits:
            fid = hit["fact_id"]
            if fid in scored:
                scored[fid]["_relevance"] = max(
                    scored[fid]["_relevance"],
                    hit["score"],
                )
                if hit["score"] > scored[fid].get("_semantic_score", 0):
                    scored[fid]["_semantic_score"] = hit["score"]
            else:
                fact_row = self._lookup_fact(user_id, fid)
                if fact_row:
                    scored[fid] = {
                        **fact_row,
                        "_relevance": hit["score"],
                        "_source": "semantic",
                        "_semantic_score": hit["score"],
                    }

        ranked = []
        for fid, data in scored.items():
            final_score = self._compute_score(data)
            ranked.append({
                **{k: v for k, v in data.items() if not k.startswith("_")},
                "retrieval_score": round(final_score, 4),
                "retrieval_source": data.get("_source", "unknown"),
            })

        ranked.sort(key=lambda x: x["retrieval_score"], reverse=True)
        return ranked[:top_k]

    def _compute_score(self, data: dict) -> float:
        relevance = data.get("_relevance", 0.0)

        created_str = data.get("created_at", "")
        recency = self._recency_score(created_str)

        confidence = data.get("confidence", 0.7)
        if isinstance(confidence, str):
            confidence = {"high": 0.95, "medium": 0.7, "low": 0.4}.get(confidence, 0.7)

        source = data.get("source", "user_stated")
        source_w = self.SOURCE_WEIGHTS.get(source, 0.5)

        return (
            self.RELEVANCE_W * relevance
            + self.RECENCY_W * recency
            + self.CONFIDENCE_W * confidence
            + self.SOURCE_W * source_w
        )

    @staticmethod
    def _recency_score(created_at: str) -> float:
        if not created_at:
            return 0.5
        try:
            dt = datetime.fromisoformat(created_at)
            age_hours = (datetime.utcnow() - dt).total_seconds() / 3600
            return max(0.0, 1.0 - (age_hours / (24 * 30)))
        except (ValueError, TypeError):
            return 0.5

    @staticmethod
    def _keyword_relevance(query: str, fact: dict) -> float:
        query_lower = query.lower()
        query_tokens = set(re.findall(r'\w+', query_lower))
        if not query_tokens:
            return 0.1

        pred = fact.get("predicate", "").lower()
        val = fact.get("value", "").lower()
        fact_tokens = set(re.findall(r'\w+', f"{pred} {val}"))

        if not fact_tokens:
            return 0.0

        overlap = query_tokens & fact_tokens
        if not overlap:
            return 0.05

        return len(overlap) / max(len(query_tokens), 1)

    def _lookup_fact(self, user_id: str, fact_id: str) -> dict | None:
        """Look up a fact by ID, ensuring user_id matches for isolation."""
        row = self.store.conn.execute(
            "SELECT * FROM facts WHERE fact_id = ? AND user_id = ?",
            (fact_id, user_id),
        ).fetchone()
        return dict(row) if row else None
