"""Pydantic models for feedback API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """Explicit feedback submission."""

    trace_id: str = Field(..., description="Trace ID for the query")
    rating: int = Field(..., description="Thumbs up/down: 1 or -1")
    comment: Optional[str] = Field(None, description="Optional user comment")


class FeedbackResponse(BaseModel):
    """Feedback acknowledgement."""

    trace_id: str
    status: str
