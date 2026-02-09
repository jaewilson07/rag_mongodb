"""Query-specific exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class QueryError(MDRAGException):
    """Raised when query service fails (LLM, formatting, etc.)."""

    pass


__all__ = ["QueryError"]
