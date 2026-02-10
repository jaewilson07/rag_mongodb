"""Query layer with grounding verification and citation mapping."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mdrag.workflows.rag.dependencies import AgentDependencies
from mdrag.core.telemetry import redact_payload, redact_text, new_trace_id, start_span
from mdrag.workflows.rag.tools import hybrid_search, semantic_search, text_search
from mdrag.capabilities.retrieval.formatting import build_citations, build_prompt


@dataclass
class GroundingResult:
    grounded: bool
    max_similarity: float
    missing_citations: List[int]


class QueryService:
    """Run retrieval, generation, and grounding verification."""

    def __init__(self) -> None:
        self.deps = AgentDependencies()

    async def answer_query(
        self,
        query: str,
        search_type: str = "hybrid",
        match_count: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        parent_trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self.deps.initialize()
        trace_id = new_trace_id()
        start_time = time.perf_counter()

        class DepsWrapper:
            def __init__(self, deps):
                self.deps = deps

        deps_ctx = DepsWrapper(self.deps)

        with start_span("retrieval", {"trace_id": trace_id, "search_type": search_type}):
            if search_type == "semantic":
                results = await semantic_search(
                    deps_ctx, query, match_count, filters=filters
                )
            elif search_type == "text":
                results = await text_search(
                    deps_ctx, query, match_count, filters=filters
                )
            else:
                results = await hybrid_search(
                    deps_ctx, query, match_count, filters=filters
                )

        citations = build_citations(results)
        prompt = build_prompt(query, results)
        with start_span("generation", {"trace_id": trace_id}):
            answer, usage = await self._generate_answer(prompt)

        grounding = await self._verify_grounding(answer, results)

        latency_ms = (time.perf_counter() - start_time) * 1000
        trace_record = self._build_trace_record(
            trace_id=trace_id,
            query=query,
            answer=answer,
            citations=citations,
            results=results,
            grounding=grounding,
            filters=filters,
            latency_ms=latency_ms,
            usage=usage,
            parent_trace_id=parent_trace_id,
        )
        await self._store_trace(trace_record)

        if parent_trace_id and self._is_correction(query):
            await self._store_feedback(
                trace_id=parent_trace_id,
                rating=-1,
                comment="Implicit correction detected",
            )

        return {
            "answer": answer,
            "citations": citations,
            "grounding": {
                "grounded": grounding.grounded,
                "max_similarity": grounding.max_similarity,
                "missing_citations": grounding.missing_citations,
            },
            "trace_id": trace_id,
        }

    async def close(self) -> None:
        await self.deps.cleanup()

    async def _generate_answer(self, prompt: str) -> tuple[str, Dict[str, Any]]:
        response = await self.deps.llm_client.create(
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
        )
        usage = getattr(response, "usage", None)
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
        return response.choices[0].message.content.strip(), usage_dict

    async def _verify_grounding(self, answer: str, results: list) -> GroundingResult:
        missing_citations = self._find_missing_citations(answer, results)
        answer_embedding = await self.deps.get_embedding(answer)
        embeddings = [
            (result.chunk_id, result.content, result.metadata.get("embedding_text"))
            for result in results
        ]

        max_similarity = 0.0
        for _, content, embedding_text in embeddings:
            text = embedding_text or content
            chunk_embedding = await self.deps.get_embedding(text)
            similarity = self._cosine_similarity(answer_embedding, chunk_embedding)
            max_similarity = max(max_similarity, similarity)

        grounded = max_similarity >= 0.75 and not missing_citations
        return GroundingResult(
            grounded=grounded,
            max_similarity=max_similarity,
            missing_citations=missing_citations,
        )

    async def _store_trace(self, record: Dict[str, Any]) -> None:
        collection = self.deps.db[self.deps.settings.mongodb_collection_traces]
        await collection.insert_one(record)

    async def _store_feedback(self, trace_id: str, rating: int, comment: str) -> None:
        collection = self.deps.db[self.deps.settings.mongodb_collection_feedback]
        await collection.insert_one(
            {
                "trace_id": trace_id,
                "rating": rating,
                "comment": redact_text(comment),
                "created_at": time.time(),
            }
        )

    def _build_trace_record(
        self,
        trace_id: str,
        query: str,
        answer: str,
        citations: Dict[str, Any],
        results: list,
        grounding: GroundingResult,
        filters: Optional[Dict[str, Any]],
        latency_ms: float,
        usage: Dict[str, Any],
        parent_trace_id: Optional[str],
    ) -> Dict[str, Any]:
        retrieval_metadata = [
            {
                "chunk_id": result.chunk_id,
                "document_id": result.document_id,
                "source_url": result.metadata.get("source_url"),
                "page_number": result.metadata.get("page_number"),
                "heading_path": result.metadata.get("heading_path", []),
                "source_type": result.metadata.get("source_type"),
                "summary_context": result.metadata.get("summary_context"),
                "score": result.similarity,
            }
            for result in results
        ]

        payload = {
            "trace_id": trace_id,
            "parent_trace_id": parent_trace_id,
            "query": query,
            "answer": answer,
            "citations": citations,
            "retrieval": retrieval_metadata,
            "grounding": {
                "grounded": grounding.grounded,
                "max_similarity": grounding.max_similarity,
                "missing_citations": grounding.missing_citations,
            },
            "filters": filters or {},
            "latency_ms": latency_ms,
            "usage": usage,
            "created_at": time.time(),
        }

        return redact_payload(payload)

    @staticmethod
    def _is_correction(query: str) -> bool:
        lower = query.lower().strip()
        return lower.startswith("no,") or lower.startswith("actually") or lower.startswith("not ")

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _find_missing_citations(answer: str, results: list) -> List[int]:
        expected = set(range(1, len(results) + 1))
        found = set(int(x) for x in re.findall(r"\[(\d+)\]", answer))
        missing = sorted(expected - found)
        return missing

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are a librarian assistant. Use only the provided sources. "
            "Never use global knowledge. Every factual statement must have a citation."
        )