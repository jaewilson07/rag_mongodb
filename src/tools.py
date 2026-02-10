"""Tools compatibility shim - re-exports from mdrag.workflows.rag.tools."""

from mdrag.workflows.rag.tools import (
    HasDeps,
    SearchResult,
    WebSearchResult,
    hybrid_search,
    semantic_search,
    text_search,
    searxng_search,
)

__all__ = [
    "HasDeps",
    "SearchResult",
    "WebSearchResult",
    "hybrid_search",
    "semantic_search",
    "text_search",
    "searxng_search",
]
