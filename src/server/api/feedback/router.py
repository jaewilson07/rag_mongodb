"""Feedback API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from mdrag.mdrag_logging.service_logging import log_call
from mdrag.server.api.feedback.models import FeedbackRequest, FeedbackResponse
from mdrag.server.config import api_config
from mdrag.server.services.feedback import FeedbackService

feedback_router = APIRouter(
    prefix=api_config.FEEDBACK_PREFIX,
    tags=["feedback"],
)


@feedback_router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
@log_call(action_name="submit_feedback")
async def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit explicit user feedback for a trace."""
    if request.rating not in (1, -1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be 1 (up) or -1 (down)",
        )

    service = FeedbackService()
    await service.submit_feedback(
        trace_id=request.trace_id,
        rating=request.rating,
        comment=request.comment,
    )

    return FeedbackResponse(trace_id=request.trace_id, status="recorded")
