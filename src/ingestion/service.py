"""High-level ingestion service for background job processing."""

from __future__ import annotations

import os
from typing import Any, Dict

from src.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig, IngestionResult
from src.ingestion.jobs import JobStatus, JobStore
from src.settings import Settings


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
        source_type = payload.get("source_type")
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
                job_store.update_status(job_id, JobStatus.DOCLING_PARSING)
                job_store.update_status(job_id, JobStatus.INDEXING)
                results = await self.pipeline._ingest_google_drive(
                    folder_ids=payload.get("folder_ids", []),
                    file_ids=payload.get("file_ids", []),
                    doc_ids=payload.get("doc_ids", []),
                    namespace=namespace,
                )
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
                except OSError:
                    pass
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
        except Exception as exc:
            job_store.update_status(job_id, JobStatus.FAILED, error=str(exc))
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
