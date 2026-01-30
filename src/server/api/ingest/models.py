"""Pydantic models for ingestion API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class WebIngestRequest(BaseModel):
    """Request model for web ingestion."""

    url: str = Field(..., description="URL to ingest")
    deep: bool = Field(False, description="Enable deep crawl")
    max_depth: Optional[int] = Field(None, description="Maximum crawl depth")
    user_id: Optional[str] = Field(None, description="User namespace for tenancy")
    org_id: Optional[str] = Field(None, description="Org namespace for tenancy")
    source_group: Optional[str] = Field(
        None, description="Source grouping (e.g., domain or folder)"
    )


class DriveIngestRequest(BaseModel):
    """Request model for Google Drive ingestion."""

    file_ids: List[str] = Field(default_factory=list, description="Drive file IDs")
    folder_ids: List[str] = Field(default_factory=list, description="Drive folder IDs")
    doc_ids: List[str] = Field(default_factory=list, description="Google Docs IDs")
    user_id: Optional[str] = Field(None, description="User namespace for tenancy")
    org_id: Optional[str] = Field(None, description="Org namespace for tenancy")
    source_group: Optional[str] = Field(
        None, description="Source grouping (e.g., domain or folder)"
    )


class JobResponse(BaseModel):
    """Response model for job creation."""

    job_id: str
    status: str
    status_url: str


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""

    job_id: str
    status: str
    created_at: str
    updated_at: str
    error: Optional[str] = None
    result: Optional[dict] = None
