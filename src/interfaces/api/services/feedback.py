"""Service layer for feedback routes."""

from __future__ import annotations

from datetime import datetime

from mdrag.observability.pii import redact_text
from mdrag.interfaces.api.dependencies import ManagedDependencies


class FeedbackService:
    """Handle feedback persistence."""

    async def submit_feedback(self, trace_id: str, rating: int, comment: str | None) -> None:
        async with ManagedDependencies() as deps:
            feedback_collection = deps.db[deps.settings.mongodb_collection_feedback]
            feedback_collection.insert_one(
                {
                    "trace_id": trace_id,
                    "rating": rating,
                    "comment": redact_text(comment or "") if comment else None,
                    "created_at": datetime.now(),
                }
            )
