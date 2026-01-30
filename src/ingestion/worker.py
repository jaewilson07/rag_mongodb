"""RQ worker entrypoint for ingestion jobs."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from src.ingestion.jobs import JobStore
from src.ingestion.service import IngestionService
from src.settings import load_settings


def process_ingestion_job(job_id: str, payload: Dict[str, Any]) -> None:
    """Background job handler for ingestion tasks."""
    settings = load_settings()
    job_store = JobStore(settings.redis_url)
    service = IngestionService(settings)

    asyncio.run(service.run_job(job_id, payload, job_store))
