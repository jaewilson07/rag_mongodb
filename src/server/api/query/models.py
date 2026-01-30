"""Pydantic models for query API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for grounded query."""

    query: str = Field(..., description="User query string")
    search_type: str = Field("hybrid", description="semantic | text | hybrid")
    match_count: int = Field(5, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filter by source_type/source_group/user_id/org_id/source_mask",
    )
    parent_trace_id: Optional[str] = Field(
        None, description="Optional prior trace to detect corrections"
    )


class QueryResponse(BaseModel):
    """Response model with citations and grounding status."""

    answer: str
    citations: Dict[str, Any]
    grounding: Dict[str, Any]
    trace_id: str
