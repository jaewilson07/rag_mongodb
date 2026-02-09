"""RAG workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class RAGError(MDRAGException):
    """Raised when RAG workflow fails (agent, tools, dependencies)."""

    pass


__all__ = ["RAGError"]
