"""Memory capability exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class MemoryError(MDRAGException):
    """Raised when memory operations fail."""

    pass


__all__ = ["MemoryError"]
