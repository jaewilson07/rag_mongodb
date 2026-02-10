"""Ingestion compatibility redirect package."""

from mdrag.capabilities.ingestion.ingest import IngestionWorkflow
from mdrag.capabilities.ingestion.models import (
    IngestionConfig,
    IngestionResult,
    CollectedSource,
    Namespace,
)

__all__ = [
    "IngestionWorkflow",
    "IngestionConfig",
    "IngestionResult",
    "CollectedSource",
    "Namespace",
]
