"""High-level ingestion service for background job processing."""

from __future__ import annotations

import os
from time import perf_counter
from typing import Any, Dict

from mdrag.capabilities.ingestion.ingest import IngestionWorkflow
from mdrag.capabilities.ingestion.jobs.store import JobStatus, JobStore
from mdrag.capabilities.ingestion.models import (
    GoogleDriveCollectionRequest,
    IngestionConfig,
    IngestionResult,
    Namespace,
    UploadCollectionRequest,
    WebCollectionRequest,
)
from mdrag.capabilities.ingestion.sources import Crawl4AICollector, GoogleDriveCollector, UploadCollector
from mdrag.capabilities.ingestion.validation import validate_ingestion
from mdrag.mdrag_logging.service_logging import get_logger, log_async
from mdrag.config.settings import Settings

logger = get_logger(__name__)

_SOURCE_TYPE_TO_COLLECTOR: dict[str, str] = {
    "web": "crawl4ai",
    "gdrive": "gdrive",
    "upload": "upload",
}


class IngestionService:
    """Coordinate ingestion workflow operations for job workers."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the ingestion service.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.workflow = IngestionWorkflow(
            config=IngestionConfig(),
            settings=settings,
        )

    async def run_job(
        self,
        job_id: str,
        payload: Dict[str, Any],
        job_store: JobStore,
    ) -> None:
        """Run a single ingestion job."""
        source_type = payload.get("source_type")
        start_time = perf_counter()
        await logger.info(
            "ingestion_job_start",
            action="ingestion_job_start",
            job_id=job_id,
            source_type=source_type,
        )

        try:
            await self.workflow.initialize()
            collector_name = _SOURCE_TYPE_TO_COLLECTOR.get(
                source_type, source_type or "upload"
            )
            await validate_ingestion(
                self.settings,
                collectors=[collector_name],
                strict_mongodb=False,
                require_redis=True,
            )
            results: list[IngestionResult] = []
            namespace = Namespace(**(payload.get("namespace") or {}))

            if source_type == "web":
                collector = Crawl4AICollector(settings=self.settings)
                job_store.update_status(job_id, JobStatus.FETCHING_SOURCE)
                sources = await collector.collect(
                    WebCollectionRequest(
                        url=payload["url"],
                        deep=bool(payload.get("deep")),
                        max_depth=payload.get("max_depth"),
                        namespace=namespace,
                    )
                )
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                results = await self.workflow.ingest_sources(sources)
                job_store.update_status(job_id, JobStatus.INDEXING)
            elif source_type == "gdrive":
                collector = GoogleDriveCollector(settings=self.settings)
                job_store.update_status(job_id, JobStatus.FETCHING_SOURCE)
                sources = await collector.collect(
                    GoogleDriveCollectionRequest(
                        file_ids=payload.get("file_ids", []),
                        folder_ids=payload.get("folder_ids", []),
                        doc_ids=payload.get("doc_ids", []),
                        namespace=namespace,
                    )
                )
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                results = await self.workflow.ingest_sources(sources)
                job_store.update_status(job_id, JobStatus.INDEXING)
            elif source_type == "upload":
                collector = UploadCollector()
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                sources = await collector.collect(
                    UploadCollectionRequest(
                        filename=payload.get("filename") or os.path.basename(
                            payload["file_path"]
                        ),
                        file_path=payload["file_path"],
                        namespace=namespace,
                    )
                )
                results = await self.workflow.ingest_sources(sources)
                job_store.update_status(job_id, JobStatus.INDEXING)
                self._cleanup_upload(payload.get("file_path"), job_id)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            result_payload = {
                "documents": [self._result_to_dict(result) for result in results],
            }
            job_store.update_status(
                job_id,
                JobStatus.COMPLETED,
                result=result_payload,
            )
            duration_ms = int((perf_counter() - start_time) * 1000)
            await logger.info(
                "ingestion_job_complete",
                action="ingestion_job_complete",
                job_id=job_id,
                source_type=source_type,
                document_count=len(results),
                duration_ms=duration_ms,
            )
        except Exception as exc:
            job_store.update_status(job_id, JobStatus.FAILED, error=str(exc))
            await logger.error(
                "ingestion_job_failed",
                action="ingestion_job_failed",
                job_id=job_id,
                source_type=source_type,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        finally:
            await self.workflow.close()

    @staticmethod
    def _cleanup_upload(file_path: str | None, job_id: str) -> None:
        """Remove temporary upload files after ingestion."""
        if not file_path:
            return
        try:
            os.remove(file_path)
        except OSError as exc:
            log_async(
                get_logger(__name__),
                "warning",
                "ingestion_upload_cleanup_failed",
                action="ingestion_upload_cleanup_failed",
                job_id=job_id,
                file_path=file_path,
                error=str(exc),
                error_type=type(exc).__name__,
            )

    @staticmethod
    def _result_to_dict(result: IngestionResult) -> Dict[str, Any]:
        """Convert ingestion result to dict for job payloads."""
        return {
            "document_uid": result.document_uid,
            "title": result.title,
            "chunks_created": result.chunks_created,
            "processing_time_ms": result.processing_time_ms,
            "errors": list(result.errors),
        }
