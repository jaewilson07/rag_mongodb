"""Docling integration service for local file conversion."""

from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path

from mdrag.ingestion.docling.processor import DocumentProcessor
from mdrag.integrations.models import Source, SourceFrontmatter
from mdrag.mdrag_logging.service_logging import get_logger, log_async
from mdrag.settings import load_settings

logger = get_logger(__name__)


class DoclingExportService:
    """Export local files to markdown `Source` using Docling."""

    def __init__(self, processor: DocumentProcessor | None = None) -> None:
        self._processor = processor or DocumentProcessor(settings=load_settings())

    def export_local_file(self, file_path: str) -> Source:
        """Convert a local file path into a Source payload.

        Args:
            file_path: Path to the local file to convert.

        Returns:
            Source payload with YAML frontmatter and markdown content.

        Raises:
            FileNotFoundError: If the file_path does not exist.
            ValueError: If Docling cannot process the file.
        """
        path = Path(file_path)
        if not path.exists():
            log_async(
                logger,
                "warning",
                "docling_export_file_missing",
                action="docling_export_file_missing",
                file_path=file_path,
            )
            raise FileNotFoundError(f"File not found: {file_path}")

        log_async(
            logger,
            "info",
            "docling_export_start",
            action="docling_export_start",
            file_path=str(path),
        )
        processed = self._processor.process_local_file(str(path))
        mime_type, _ = mimetypes.guess_type(path.name)

        frontmatter = SourceFrontmatter(
            source_type="upload",
            source_url=processed.source_url,
            source_title=processed.title,
            source_mime_type=mime_type,
            source_fetched_at=datetime.now().isoformat(),
        )

        source = Source(
            frontmatter=frontmatter,
            content=processed.content,
            metadata=processed.metadata,
        )
        log_async(
            logger,
            "info",
            "docling_export_complete",
            action="docling_export_complete",
            file_path=str(path),
            title=processed.title,
        )
        return source


def export_local_file_as_source(file_path: str) -> Source:
    """Convenience wrapper for exporting a local file with Docling.

    Args:
        file_path: Path to the local file to convert.

    Returns:
        Source payload with YAML frontmatter and markdown content.
    """
    return DoclingExportService().export_local_file(file_path)
