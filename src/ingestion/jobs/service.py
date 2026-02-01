"""High-level ingestion service for background job processing."""

from __future__ import annotations

import os
from typing import Any, Dict
from time import perf_counter

from mdrag.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig, IngestionResult
from mdrag.ingestion.jobs.store import JobStatus, JobStore
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import Settings

logger = get_logger(__name__)


class IngestionService:
    """Coordinate ingestion pipeline operations for job workers."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pipeline = DocumentIngestionPipeline(
            config=IngestionConfig(),
            documents_folder="documents",
            clean_before_ingest=False,
        )

    async def run_job(self, job_id: str, payload: Dict[str, Any], job_store: JobStore) -> None:
        from mdrag.ingestion.sources.ingestion_source import IngestionSource
        from mdrag.ingestion.sources.google_drive_source import GoogleDriveIngestionSource
        source_type = payload.get("source_type")
        start_time = perf_counter()
        await logger.info(
            "ingestion_job_start",
            action="ingestion_job_start",
            job_id=job_id,
            source_type=source_type,
        )
        await self.pipeline.initialize()

        try:
            if source_type == "web":
                namespace = payload.get("namespace")
                job_store.update_status(job_id, JobStatus.FETCHING_SOURCE)
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                job_store.update_status(job_id, JobStatus.INDEXING)
                results = await self.pipeline._ingest_crawl4ai(
                    urls=[payload["url"]],
                    deep=bool(payload.get("deep")),
                    max_depth=payload.get("max_depth"),
                    namespace=namespace,
                )
            elif source_type == "gdrive":
                namespace = payload.get("namespace")
                job_store.update_status(job_id, JobStatus.FETCHING_SOURCE)
                # Use protocol-based ingestion source
                file_id = None
                file_ids = payload.get("file_ids", [])
                if file_ids:
                    file_id = file_ids[0]
                elif payload.get("doc_ids"):
                    file_id = payload["doc_ids"][0]
                if not file_id:
                    raise ValueError("No Google Drive file_id provided for gdrive ingestion job")
                # Instantiate and use the protocol
                source: IngestionSource = GoogleDriveIngestionSource(file_id, namespace)
                processed = source.fetch_and_convert()
                # Now hand off to the pipeline for chunking/embedding
                results = [
                    await self.pipeline._ingest_processed_document(
                        processed,
                        namespace=namespace,
                    )
                ]
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                job_store.update_status(job_id, JobStatus.INDEXING)
            elif source_type == "upload":
                namespace = payload.get("namespace")
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                job_store.update_status(job_id, JobStatus.INDEXING)
                file_path = payload["file_path"]
                results = [
                    await self.pipeline._ingest_single_document(
                        file_path,
                        namespace=namespace,
                    )
                ]
                try:
                    os.remove(file_path)
                except OSError as exc:
                    await logger.warning(
                        "ingestion_upload_cleanup_failed",
                        action="ingestion_upload_cleanup_failed",
                        job_id=job_id,
                        file_path=file_path,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
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
            await self.pipeline.close()

    @staticmethod
    def _result_to_dict(result: IngestionResult) -> Dict[str, Any]:
        return {
            "document_id": result.document_id,
            "title": result.title,
            "chunks_created": result.chunks_created,
            "processing_time_ms": result.processing_time_ms,
            "errors": list(result.errors),
        }