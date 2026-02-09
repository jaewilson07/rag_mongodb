"""Ingestion-specific exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class IngestionError(MDRAGException):
    """Raised when ingestion fails (chunk validation, storage handoff, pipeline)."""

    pass


__all__ = ["IngestionError"]
