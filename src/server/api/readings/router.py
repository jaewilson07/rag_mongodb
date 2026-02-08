"""Readings API: save-and-research workflow (Wallabag/Instapaper style)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from mdrag.server.api.readings.models import (
    ReadingResponse,
    ReadingsListResponse,
    SaveReadingRequest,
)
from mdrag.server.config import api_config
from mdrag.server.services.readings import ReadingsService

logger = logging.getLogger(__name__)

readings_router = APIRouter(
    prefix=api_config.READINGS_PREFIX,
    tags=["readings"],
)


@readings_router.post("/save", response_model=ReadingResponse)
async def save_reading(request: SaveReadingRequest) -> ReadingResponse:
    """Save a URL: crawl, summarize, research related content, and ingest.

    This is the core endpoint for the 'Share to' workflow from Android.
    It crawls the page, generates a summary with key points,
    searches for related content, and stores everything.
    """
    service = ReadingsService()
    result = await service.save_reading(
        url=request.url,
        tags=request.tags,
        source_group=request.source_group,
        user_id=request.user_id,
        org_id=request.org_id,
    )
    return ReadingResponse(**result)


@readings_router.get("", response_model=ReadingsListResponse)
async def list_readings(
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ReadingsListResponse:
    """List all saved readings, most recent first."""
    service = ReadingsService()
    result = await service.list_readings(
        user_id=user_id, limit=limit, offset=offset
    )
    return ReadingsListResponse(**result)


@readings_router.get("/{reading_id}", response_model=ReadingResponse)
async def get_reading(reading_id: str) -> ReadingResponse:
    """Get a single reading by ID."""
    service = ReadingsService()
    result = await service.get_reading(reading_id)
    if not result:
        raise HTTPException(status_code=404, detail="Reading not found")
    return ReadingResponse(**result)
