"""RAG workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class RAGError(MDRAGException):
    """Raised when RAG agent, tools, or dependency wiring fails."""

    pass


__all__ = ["RAGError"]
