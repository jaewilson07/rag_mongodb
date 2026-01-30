"""Pydantic models for ingestion metadata."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MetadataPassport(BaseModel):
    """Minimal metadata required for citation-ready chunks."""

    source_type: Literal["gdrive", "web", "upload"]
    source_url: str
    document_title: str
    page_number: Optional[int] = None
    heading_path: List[str] = Field(default_factory=list)
    ingestion_timestamp: str
    content_hash: str
