"""Retrieval and embedding utilities for search/query layers."""

from mdrag.retrieval.embeddings import EmbeddingClient
from mdrag.retrieval.formatting import build_citations, build_prompt, format_search_results
from mdrag.retrieval.vector_store import VectorStore

__all__ = [
    "EmbeddingClient",
    "VectorStore",
    "build_citations",
    "build_prompt",
    "format_search_results",
]