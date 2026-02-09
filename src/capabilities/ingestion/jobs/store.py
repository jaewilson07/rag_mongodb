"""Ingestion job tracking and status persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import redis

from mdrag.mdrag_logging.service_logging import get_logger, log_async

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Lifecycle states for ingestion jobs."""

    PENDING = "PENDING"
    FETCHING_SOURCE = "FETCHING_SOURCE"
    DOCLING_PARSING = "DOCLING_PARSING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class JobState:
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None


class JobStore:
    """Persist job state in Redis."""

    def __init__(self, redis_url: str) -> None:
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def create_job(self, job_id: str, payload: Dict[str, Any]) -> JobState:
        now = datetime.now().isoformat()
        state = JobState(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            payload=payload,
        )
        self._save_state(state)
        log_async(
            logger,
            "info",
            "ingestion_job_created",
            action="ingestion_job_created",
            job_id=job_id,
            status=state.status.value,
        )
        return state

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> JobState:
        state = self.get_job(job_id) or JobState(
            job_id=job_id,
            status=status,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        state.status = status
        state.updated_at = datetime.now().isoformat()
        if error is not None:
            state.error = error
        if result is not None:
            state.result = result
        self._save_state(state)
        log_async(
            logger,
            "info",
            "ingestion_job_status_updated",
            action="ingestion_job_status_updated",
            job_id=job_id,
            status=status.value,
            has_error=bool(error),
        )
        return state

    def get_job(self, job_id: str) -> Optional[JobState]:
        raw = self.redis.hgetall(self._key(job_id))
        if not raw:
            return None
        payload = json.loads(raw.get("payload", "null"))
        result = json.loads(raw.get("result", "null"))
        return JobState(
            job_id=job_id,
            status=JobStatus(raw.get("status", JobStatus.PENDING.value)),
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
            error=raw.get("error") or None,
            payload=payload,
            result=result,
        )

    def _save_state(self, state: JobState) -> None:
        self.redis.hset(
            self._key(state.job_id),
            mapping={
                "status": state.status.value,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
                "error": state.error or "",
                "payload": json.dumps(state.payload or {}),
                "result": json.dumps(state.result or {}),
            },
        )

    @staticmethod
    def _key(job_id: str) -> str:
        return f"ingestion:job:{job_id}"