"""FastAPI routes for ingestion jobs."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from mdrag.mdrag_logging.service_logging import log_call
from mdrag.interfaces.api.api.ingest.models import (
    DriveIngestRequest,
    JobResponse,
    JobStatusResponse,
    WebIngestRequest,
)
from mdrag.interfaces.api.config import api_config
from mdrag.interfaces.api.services.ingest import IngestJobService

ingest_service = IngestJobService()

ingest_router = APIRouter(
    prefix=api_config.INGEST_PREFIX,
    tags=["ingestion"],
)

jobs_router = APIRouter(
    prefix=api_config.JOBS_PREFIX,
    tags=["jobs"],
)


@ingest_router.post("/web", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
@log_call(action_name="ingest_web")
async def ingest_web(request: WebIngestRequest) -> JobResponse:
    """Queue ingestion for a web URL."""
    payload = ingest_service.queue_web(
        url=request.url,
        deep=request.deep,
        max_depth=request.max_depth,
        namespace={
            "user_id": request.user_id,
            "org_id": request.org_id,
            "source_group": request.source_group,
        },
    )
    return JobResponse(
        job_id=payload["job_id"],
        status=payload["status"],
        status_url=f"{api_config.JOBS_PREFIX}/{payload['job_id']}",
    )


@ingest_router.post("/drive", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
@log_call(action_name="ingest_drive")
async def ingest_drive(request: DriveIngestRequest) -> JobResponse:
    """Queue ingestion for Google Drive sources."""
    if not (request.file_ids or request.folder_ids or request.doc_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one Drive file, folder, or doc ID.",
        )

    payload = ingest_service.queue_drive(
        file_ids=request.file_ids,
        folder_ids=request.folder_ids,
        doc_ids=request.doc_ids,
        namespace={
            "user_id": request.user_id,
            "org_id": request.org_id,
            "source_group": request.source_group,
        },
    )
    return JobResponse(
        job_id=payload["job_id"],
        status=payload["status"],
        status_url=f"{api_config.JOBS_PREFIX}/{payload['job_id']}",
    )


@ingest_router.post("/upload", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
@log_call(action_name="ingest_upload")
async def ingest_upload(
    file: UploadFile = File(...),
    user_id: str | None = None,
    org_id: str | None = None,
    source_group: str | None = None,
) -> JobResponse:
    """Queue ingestion for a local file upload."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload filename is required.",
        )

    suffix = Path(file.filename).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    payload = ingest_service.queue_upload(
        file_path=temp_path,
        namespace={
            "user_id": user_id,
            "org_id": org_id,
            "source_group": source_group,
        },
    )
    return JobResponse(
        job_id=payload["job_id"],
        status=payload["status"],
        status_url=f"{api_config.JOBS_PREFIX}/{payload['job_id']}",
    )


@jobs_router.get("/{job_id}", response_model=JobStatusResponse)
@log_call(action_name="get_job_status")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of an ingestion job."""
    state = ingest_service.get_job(job_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status.value,
        created_at=state.created_at,
        updated_at=state.updated_at,
        error=state.error,
        result=state.result,
    )
