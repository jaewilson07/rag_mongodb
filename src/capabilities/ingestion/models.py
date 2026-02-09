"""Pydantic models for ingestion domain contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import NAMESPACE_URL, uuid5

from docling_core.types.doc.document import DoclingDocument
from pydantic import BaseModel, ConfigDict, Field

from mdrag.integrations.models import SourceFrontmatter


class Namespace(BaseModel):
    """Namespace metadata for multi-tenant ingestion."""

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    source_group: Optional[str] = None


class DocumentIdentity(BaseModel):
    """Stable document identity for cross-store linkage."""

    document_uid: str
    content_hash: str
    source_type: Literal["gdrive", "web", "upload"]
    source_url: str
    source_id: Optional[str] = None
    source_mime_type: Optional[str] = None

    @classmethod
    def build(
        cls,
        *,
        source_type: Literal["gdrive", "web", "upload"],
        source_url: str,
        content_hash: str,
        source_id: Optional[str] = None,
        source_mime_type: Optional[str] = None,
    ) -> "DocumentIdentity":
        """Build a deterministic identity for a document.

        Args:
            source_type: Source type for the document.
            source_url: Canonical source URL.
            content_hash: Hash of the raw source payload.
            source_id: Optional external source identifier.
            source_mime_type: Optional source MIME type.

        Returns:
            DocumentIdentity instance.
        """
        identity_seed = f"{source_type}:{source_id or source_url}:{content_hash}"
        document_uid = str(uuid5(NAMESPACE_URL, identity_seed))
        return cls(
            document_uid=document_uid,
            content_hash=content_hash,
            source_type=source_type,
            source_url=source_url,
            source_id=source_id,
            source_mime_type=source_mime_type,
        )


class MetadataPassport(BaseModel):
    """Minimal metadata required for citation-ready chunks."""

    document_uid: str
    source_type: Literal["gdrive", "web", "upload"]
    source_url: str
    source_id: Optional[str] = None
    source_group: Optional[str] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    document_title: str
    page_number: Optional[int] = None
    heading_path: List[str] = Field(default_factory=list)
    ingestion_timestamp: str
    content_hash: str


class SourceContentKind(str, Enum):
    """Supported payload types for collected sources."""

    MARKDOWN = "markdown"
    HTML = "html"
    BYTES = "bytes"
    FILE_PATH = "file_path"


class SourceContent(BaseModel):
    """Payload container for collected source content."""

    kind: SourceContentKind
    data: str | bytes
    filename: Optional[str] = None
    mime_type: Optional[str] = None


class CollectedSource(BaseModel):
    """Normalized output from collection capabilities."""

    frontmatter: SourceFrontmatter
    content: SourceContent
    metadata: Dict[str, Any] = Field(default_factory=dict)
    links: List[str] = Field(default_factory=list)
    namespace: Namespace = Field(default_factory=Namespace)


class IngestionMetadata(BaseModel):
    """Metadata attached to processed documents and chunks."""

    identity: DocumentIdentity
    namespace: Namespace
    frontmatter: SourceFrontmatter
    collected_at: str
    ingested_at: str
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionDocument(BaseModel):
    """Docling-processed document ready for chunking."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: str
    docling_document: DoclingDocument
    docling_json: Dict[str, Any]
    page_texts: Dict[str, str]
    title: str
    metadata: IngestionMetadata


class GraphTriple(BaseModel):
    """Graph representation triple for downstream storage layers."""

    subject: str
    predicate: str
    object: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class StorageRepresentations(BaseModel):
    """Canonical representations for storage adapters."""

    markdown: str
    docling_json: Dict[str, Any]
    graph_triples: List[GraphTriple] = Field(default_factory=list)
    cypher_statements: List[str] = Field(default_factory=list)


class StorageResult(BaseModel):
    """Result from persisting into a storage adapter."""

    adapter: str
    document_uid: str
    document_id: str
    chunk_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionConfig(BaseModel):
    """Configuration for document ingestion workflow."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 2000
    max_tokens: int = 512
    enable_darwinxml: bool = False
    darwinxml_validate: bool = True
    darwinxml_strict: bool = False


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_uid: str
    title: str
    chunks_created: int
    processing_time_ms: float
    storage_results: List[StorageResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CollectionRequest(BaseModel):
    """Base request for collection capabilities."""

    namespace: Namespace = Field(default_factory=Namespace)


class WebCollectionRequest(CollectionRequest):
    """Request payload for web collection."""

    url: str
    deep: bool = False
    max_depth: Optional[int] = None


class GoogleDriveCollectionRequest(CollectionRequest):
    """Request payload for Google Drive collection."""

    file_ids: List[str] = Field(default_factory=list)
    folder_ids: List[str] = Field(default_factory=list)
    doc_ids: List[str] = Field(default_factory=list)


class UploadCollectionRequest(CollectionRequest):
    """Request payload for upload collection."""

    filename: str
    content: Optional[str | bytes] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None


def ingestion_timestamp() -> str:
    """Return a consistent timestamp string for ingestion events."""
    return datetime.now().isoformat()


__all__ = [
    "CollectionRequest",
    "CollectedSource",
    "DocumentIdentity",
    "GoogleDriveCollectionRequest",
    "GraphTriple",
    "IngestionConfig",
    "IngestionDocument",
    "IngestionMetadata",
    "IngestionResult",
    "MetadataPassport",
    "Namespace",
    "SourceContent",
    "SourceContentKind",
    "StorageRepresentations",
    "StorageResult",
    "UploadCollectionRequest",
    "WebCollectionRequest",
    "ingestion_timestamp",
]
