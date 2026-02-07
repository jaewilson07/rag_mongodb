"""Pydantic models for the Readings / Save-to API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SaveReadingRequest(BaseModel):
    """Request to save a URL, crawl it, summarize, and research."""

    url: str = Field(..., description="URL to save and research")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    source_group: Optional[str] = Field(None, description="Source group")
    user_id: Optional[str] = Field(None, description="User ID for tenancy")
    org_id: Optional[str] = Field(None, description="Org ID for tenancy")


class RelatedLink(BaseModel):
    """A related link discovered during research."""

    title: str
    url: str
    snippet: str
    source: Optional[str] = None


class ReadingResponse(BaseModel):
    """Full reading response with summary and research."""

    id: str
    url: str
    title: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    related_links: List[RelatedLink] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    content_preview: str = ""
    word_count: int = 0
    saved_at: str
    status: str = "complete"
    source_group: Optional[str] = None
    ingestion_job_id: Optional[str] = None


class ReadingListItem(BaseModel):
    """Compact reading for list views."""

    id: str
    url: str
    title: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    saved_at: str
    status: str = "complete"
    domain: Optional[str] = None


class ReadingsListResponse(BaseModel):
    """Response listing saved readings."""

    readings: List[ReadingListItem]
    total: int
