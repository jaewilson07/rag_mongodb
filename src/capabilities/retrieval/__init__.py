"""Retrieval and embedding utilities for search/query layers."""

from mdrag.capabilities.retrieval.embeddings import EmbeddingClient
from mdrag.capabilities.retrieval.formatting import build_citations, build_prompt, format_search_results
from mdrag.capabilities.retrieval.vector_store import VectorStore

__all__ = [
    "EmbeddingClient",
    "VectorStore",
    "build_citations",
    "build_prompt",
    "format_search_results",
]