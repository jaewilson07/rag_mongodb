"""Shared formatting utilities for retrieval results."""

from __future__ import annotations

from typing import Any, Dict, List


def build_prompt(query: str, results: list) -> str:
    sources = []
    for idx, result in enumerate(results, start=1):
        sources.append(f"[{idx}] {result.document_title}\n{result.content}\n")
    sources_text = "\n".join(sources)
    return (
        f"Question: {query}\n\n"
        "Use ONLY the sources below. Provide citations like [1] after each fact.\n\n"
        f"Sources:\n{sources_text}"
    )


def build_citations(results: list) -> Dict[str, Any]:
    citations: Dict[str, Any] = {}
    for idx, result in enumerate(results, start=1):
        citations[str(idx)] = {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "source_url": result.metadata.get("source_url"),
            "page_number": result.metadata.get("page_number"),
            "heading_path": result.metadata.get("heading_path", []),
            "source_type": result.metadata.get("source_type"),
            "summary_context": result.metadata.get("summary_context"),
            "document_title": result.document_title,
        }
    return citations


def format_search_results(results: list) -> str:
    if not results:
        return "No relevant information found in the knowledge base."

    response_parts: List[str] = [f"Found {len(results)} relevant documents:\n"]
    for i, result in enumerate(results, 1):
        score = f"{result.similarity:.2f}" if result.similarity is not None else "n/a"
        response_parts.append(
            f"\n--- Document {i}: {result.document_title} [{i}] (relevance: {score}) ---"
        )
        response_parts.append(result.content)

    return "\n".join(response_parts)