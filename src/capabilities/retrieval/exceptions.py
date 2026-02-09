"""Retrieval-specific exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class RetrievalError(MDRAGException):
    """Raised when retrieval fails (vector search, text search, hybrid search)."""

    pass


__all__ = ["RetrievalError"]
