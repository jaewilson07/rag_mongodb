"""RQ worker entrypoint for ingestion jobs."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from mdrag.capabilities.ingestion.jobs.store import JobStore
from mdrag.capabilities.ingestion.jobs.service import IngestionService
from mdrag.mdrag_logging.service_logging import get_logger, log_async
from mdrag.config.settings import load_settings

logger = get_logger(__name__)


def process_ingestion_job(job_id: str, payload: Dict[str, Any]) -> None:
    """Background job handler for ingestion tasks."""
    log_async(
        logger,
        "info",
        "ingestion_worker_start",
        action="ingestion_worker_start",
        job_id=job_id,
        source_type=payload.get("source_type"),
    )
    settings = load_settings()
    job_store = JobStore(settings.redis_url)
    service = IngestionService(settings)

    try:
        asyncio.run(service.run_job(job_id, payload, job_store))
        log_async(
            logger,
            "info",
            "ingestion_worker_complete",
            action="ingestion_worker_complete",
            job_id=job_id,
        )
    except Exception as exc:
        log_async(
            logger,
            "error",
            "ingestion_worker_failed",
            action="ingestion_worker_failed",
            job_id=job_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise