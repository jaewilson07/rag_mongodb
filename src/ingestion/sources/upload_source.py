"""Upload collector implementing the SourceCollector protocol."""

from __future__ import annotations

import os
from typing import List

from mdrag.ingestion.models import (
    CollectedSource,
    SourceContent,
    SourceContentKind,
    UploadCollectionRequest,
    ingestion_timestamp,
)
from mdrag.ingestion.protocols import SourceCollector
from mdrag.integrations.models import SourceFrontmatter
from mdrag.mdrag_logging.service_logging import get_logger

logger = get_logger(__name__)


class UploadCollector(SourceCollector[UploadCollectionRequest]):
    """Collect uploaded content for ingestion."""

    name = "upload"

    async def collect(self, request: UploadCollectionRequest) -> List[CollectedSource]:
        """Collect upload sources and normalize for ingestion."""
        await logger.info(
            "collector_upload_start",
            action="collector_upload_start",
            filename=request.filename,
        )

        if not request.file_path and request.content is None:
            raise ValueError("Upload request must include file_path or content")

        if request.file_path:
            file_path = os.path.abspath(request.file_path)
            frontmatter = SourceFrontmatter(
                source_type="upload",
                source_url=f"file://{file_path}",
                source_title=request.filename,
                source_mime_type=request.mime_type,
                source_fetched_at=ingestion_timestamp(),
            )
            collected = CollectedSource(
                frontmatter=frontmatter,
                content=SourceContent(
                    kind=SourceContentKind.FILE_PATH,
                    data=file_path,
                    filename=request.filename,
                    mime_type=request.mime_type,
                ),
                metadata={"file_path": file_path},
                namespace=request.namespace,
            )
            return [collected]

        content = request.content
        if content is None:
            raise ValueError("Upload content cannot be None")

        if isinstance(content, bytes):
            kind = SourceContentKind.BYTES
        else:
            if request.mime_type == "text/html":
                kind = SourceContentKind.HTML
            else:
                kind = SourceContentKind.MARKDOWN

        frontmatter = SourceFrontmatter(
            source_type="upload",
            source_url=f"upload://{request.filename}",
            source_title=request.filename,
            source_mime_type=request.mime_type,
            source_fetched_at=ingestion_timestamp(),
        )
        collected = CollectedSource(
            frontmatter=frontmatter,
            content=SourceContent(
                kind=kind,
                data=content,
                filename=request.filename,
                mime_type=request.mime_type,
            ),
            metadata={},
            namespace=request.namespace,
        )
        await logger.info(
            "collector_upload_complete",
            action="collector_upload_complete",
            filename=request.filename,
            collected_count=1,
        )
        return [collected]


__all__ = ["UploadCollector"]
