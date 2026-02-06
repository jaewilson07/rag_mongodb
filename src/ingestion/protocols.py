"""Protocol definitions for ingestion capabilities."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from mdrag.ingestion.docling.chunker import DoclingChunks
from mdrag.ingestion.docling.darwinxml_models import DarwinXMLDocument
from mdrag.ingestion.models import (
    CollectedSource,
    IngestionDocument,
    StorageRepresentations,
    StorageResult,
)

RequestT = TypeVar("RequestT", bound=BaseModel)


@runtime_checkable
class SourceCollector(Protocol, Generic[RequestT]):
    """Protocol for collection capabilities."""

    async def collect(self, request: RequestT) -> list[CollectedSource]:
        """Collect sources and normalize into ingestion payloads."""
        ...


@runtime_checkable
class IngestionProcessor(Protocol):
    """Protocol for document conversion capabilities."""

    async def convert_source(self, source: CollectedSource) -> IngestionDocument:
        """Convert collected sources into Docling-ready documents."""
        ...


@runtime_checkable
class StorageAdapter(Protocol):
    """Protocol for storage capabilities."""

    async def initialize(self) -> None:
        """Initialize storage dependencies."""
        ...

    async def store(
        self,
        document: IngestionDocument,
        chunks: list[DoclingChunks],
        representations: StorageRepresentations,
        darwin_documents: list[DarwinXMLDocument],
    ) -> StorageResult:
        """Persist document and chunk data to a storage backend."""
        ...

    async def close(self) -> None:
        """Close storage dependencies."""
        ...


__all__ = ["IngestionProcessor", "SourceCollector", "StorageAdapter"]
