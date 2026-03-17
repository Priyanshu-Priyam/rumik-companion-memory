from __future__ import annotations
import logging
from rumik.brain import CompanionBrain
from rumik.chat.llm import call_llm, format_messages_for_bedrock
from rumik.chat.prompt_builder import build_system_prompt
from rumik.memory.store import MemoryStore
from rumik.memory.vector_store import VectorStore
from rumik.memory.manager import MemoryManager
from rumik.memory.extractor import FactExtractor
from rumik.memory.retriever import HybridRetriever
from rumik.policies.uncertainty import apply_uncertainty_policy
from rumik.policies.sensitive import apply_sensitivity_policy

logger = logging.getLogger(__name__)


class ImprovedEngine(CompanionBrain):
    """Brain B: full memory pipeline with extraction, correction,
    retrieval, ranking, and policy enforcement."""

    def __init__(
        self,
        model_id: str | None = None,
        extract_on_chat: bool = False,
        db_path: str = ":memory:",
        chroma_dir: str | None = None,
    ):
        self._model_id = model_id
        self._extract_on_chat = extract_on_chat

        self._store = MemoryStore(db_path=db_path)
        self._vs = VectorStore(persist_dir=chroma_dir)
        self._manager = MemoryManager(self._store, self._vs)
        self._extractor = FactExtractor(model_id=model_id)
        self._retriever = HybridRetriever(self._store, self._vs)

    def seed_memory(self, user_id: str, facts: list[dict]) -> None:
        self._manager.seed_from_eval(user_id, facts)

    def chat(
        self,
        user_id: str,
        message: str,
        history: list[dict] | None = None,
    ) -> dict:
        debug: dict = {"model_id": self._model_id}

        # --- WRITE PHASE: extract facts from the message ---
        extraction_results = []
        manager_actions = []
        if self._extract_on_chat:
            ext_output = self._extractor.extract(user_id, message, history)
            extraction_results = ext_output["results"]
            debug["extractions"] = extraction_results
            debug["extraction_raw"] = ext_output.get("raw_response")
            debug["extraction_error"] = ext_output.get("error")
            debug["extraction_source"] = ext_output.get("source")

            if ext_output.get("error"):
                logger.warning(
                    "Extraction error for user %s: %s",
                    user_id, ext_output["error"],
                )

            if extraction_results:
                manager_actions = self._manager.process_extractions(
                    user_id, extraction_results
                )
                debug["manager_actions"] = manager_actions

        # --- READ PHASE: retrieve -> rank -> policies -> generate ---

        retrieved = self._retriever.retrieve(user_id, message, top_k=15)
        debug["retrieved_facts"] = [
            {"predicate": f.get("predicate"), "value": f.get("value"),
             "score": f.get("retrieval_score"), "status": f.get("status"),
             "sensitivity": f.get("sensitivity")}
            for f in retrieved
        ]

        historical = self._store.get_facts(user_id, status="corrected")
        historical += self._store.get_facts(user_id, status="stale")
        debug["historical_count"] = len(historical)

        uncertainty = apply_uncertainty_policy(retrieved, message)
        debug["has_relevant_facts"] = uncertainty["has_relevant_facts"]

        sensitivity = apply_sensitivity_policy(
            uncertainty["facts"], message
        )
        debug["withheld_sensitive"] = len(sensitivity.get("withheld", []))

        system_prompt = build_system_prompt(
            current_facts=sensitivity["facts"],
            historical_facts=historical[:5] if historical else None,
            uncertainty_instructions=uncertainty["instructions"],
            sensitivity_instructions=sensitivity["instructions"],
        )
        debug["system_prompt"] = system_prompt

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
            "debug": debug,
        }

    def reset(self, user_id: str) -> None:
        self._manager.clear_user(user_id)
