"""Service layer for ingestion routes."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict

from rq import Queue

from mdrag.capabilities.ingestion.jobs import JobStore, process_ingestion_job
from mdrag.mdrag_logging.service_logging import get_logger, log_async
from mdrag.config.settings import load_settings


class IngestJobService:
    """Handle ingestion job orchestration."""

    def __init__(self, job_store: JobStore | None = None, queue: Queue | None = None) -> None:
        settings = load_settings()
        self.job_store = job_store or JobStore(settings.redis_url)
        self.queue = queue or Queue(connection=self.job_store.redis)
        self.logger = get_logger(__name__)

    def queue_web(self, url: str, deep: bool, max_depth: int | None, namespace: Dict[str, Any]) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        payload = {
            "source_type": "web",
            "url": url,
            "deep": deep,
            "max_depth": max_depth,
            "namespace": namespace,
        }
        self.job_store.create_job(job_id, payload)
        self.queue.enqueue(process_ingestion_job, job_id, payload)
        log_async(
            self.logger,
            "info",
            "ingest_job_queued",
            action="ingest_job_queued",
            job_id=job_id,
            source_type="web",
        )
        return {"job_id": job_id, "status": "PENDING"}

    def queue_drive(
        self,
        file_ids: list[str],
        folder_ids: list[str],
        doc_ids: list[str],
        namespace: Dict[str, Any],
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        payload = {
            "source_type": "gdrive",
            "file_ids": file_ids,
            "folder_ids": folder_ids,
            "doc_ids": doc_ids,
            "namespace": namespace,
        }
        self.job_store.create_job(job_id, payload)
        self.queue.enqueue(process_ingestion_job, job_id, payload)
        log_async(
            self.logger,
            "info",
            "ingest_job_queued",
            action="ingest_job_queued",
            job_id=job_id,
            source_type="gdrive",
        )
        return {"job_id": job_id, "status": "PENDING"}

    def queue_upload(self, file_path: str, namespace: Dict[str, Any]) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        payload = {
            "source_type": "upload",
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "namespace": namespace,
        }
        self.job_store.create_job(job_id, payload)
        self.queue.enqueue(process_ingestion_job, job_id, payload)
        log_async(
            self.logger,
            "info",
            "ingest_job_queued",
            action="ingest_job_queued",
            job_id=job_id,
            source_type="upload",
        )
        return {"job_id": job_id, "status": "PENDING"}

    def get_job(self, job_id: str):
        return self.job_store.get_job(job_id)
