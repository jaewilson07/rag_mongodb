"""Feedback API routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.dependencies import AgentDependencies
from src.observability.pii import redact_text
from src.server.api.feedback.models import FeedbackRequest, FeedbackResponse
from src.server.config import api_config

feedback_router = APIRouter(
    prefix=api_config.FEEDBACK_PREFIX,
    tags=["feedback"],
)


@feedback_router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit explicit user feedback for a trace."""
    if request.rating not in (1, -1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be 1 (up) or -1 (down)",
        )

    deps = AgentDependencies()
    await deps.initialize()
    try:
        feedback_collection = deps.db[deps.settings.mongodb_collection_feedback]
        feedback_collection.insert_one(
            {
                "trace_id": request.trace_id,
                "rating": request.rating,
                "comment": redact_text(request.comment or "") if request.comment else None,
                "created_at": datetime.now(),
            }
        )
    finally:
        await deps.cleanup()

    return FeedbackResponse(trace_id=request.trace_id, status="recorded")
