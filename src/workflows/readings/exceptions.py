"""Readings workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class ReadingsError(MDRAGException):
    """Raised when save-reading, extraction, or research pipeline fails."""

    pass


__all__ = ["ReadingsError"]
