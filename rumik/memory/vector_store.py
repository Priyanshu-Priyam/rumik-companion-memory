from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-backed semantic search for facts, with per-user isolation."""

    def __init__(self, persist_dir: str | None = None):
        try:
            import chromadb
            if persist_dir:
                self._client = chromadb.PersistentClient(path=persist_dir)
            else:
                self._client = chromadb.EphemeralClient()
            self._collection = self._client.get_or_create_collection(
                name="facts",
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
        except Exception as e:
            logger.warning("ChromaDB unavailable, falling back to keyword-only retrieval: %s", e)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def add_fact(self, user_id: str, fact_id: str, text: str):
        if not self._available:
            return
        try:
            self._collection.add(
                ids=[fact_id],
                documents=[text],
                metadatas=[{"user_id": user_id}],
            )
        except Exception as e:
            logger.warning("Failed to add fact to vector store: %s", e)

    def add_facts_bulk(self, user_id: str, facts: list[dict]):
        """Bulk-add facts. Each dict must have 'fact_id' and 'text' keys."""
        if not self._available or not facts:
            return
        try:
            self._collection.add(
                ids=[f["fact_id"] for f in facts],
                documents=[f["text"] for f in facts],
                metadatas=[{"user_id": user_id}] * len(facts),
            )
        except Exception as e:
            logger.warning("Failed to bulk-add to vector store: %s", e)

    def query(self, user_id: str, query_text: str, top_k: int = 15) -> list[dict]:
        """Semantic search filtered by user_id. Returns list of {fact_id, score, text}."""
        if not self._available:
            return []
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=min(top_k, self._collection.count() or 1),
                where={"user_id": user_id},
            )
            hits = []
            if results and results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)
                documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
                for i, fid in enumerate(ids):
                    hits.append({
                        "fact_id": fid,
                        "score": 1.0 - distances[i],
                        "text": documents[i],
                    })
            return hits
        except Exception as e:
            logger.warning("Vector query failed: %s", e)
            return []

    def remove_user(self, user_id: str):
        if not self._available:
            return
        try:
            existing = self._collection.get(where={"user_id": user_id})
            if existing and existing["ids"]:
                self._collection.delete(ids=existing["ids"])
        except Exception as e:
            logger.warning("Failed to remove user from vector store: %s", e)

    def clear(self):
        if not self._available:
            return
        try:
            import chromadb
            self._client.delete_collection("facts")
            self._collection = self._client.get_or_create_collection(
                name="facts",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.warning("Failed to clear vector store: %s", e)
