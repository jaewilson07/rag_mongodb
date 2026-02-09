"""Readings workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class ReadingsError(MDRAGException):
    """Raised when readings workflow fails (save-reading, extraction, research)."""

    pass


__all__ = ["ReadingsError"]
