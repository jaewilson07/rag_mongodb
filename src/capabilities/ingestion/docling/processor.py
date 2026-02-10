"""Docling conversion utilities for ingestion."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument

from pydantic import BaseModel

from mdrag.capabilities.ingestion.models import (
    CollectedSource,
    DocumentIdentity,
    IngestionDocument,
    IngestionMetadata,
    Namespace,
    SourceContent,
    SourceContentKind,
    ingestion_timestamp,
)
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.config.settings import Settings

logger = get_logger(__name__)


class _MaterializedContent(BaseModel):
    """Internal helper for content materialization."""

    path: str
    content_hash: str
    cleanup: bool


class DoclingProcessor:
    """Convert collected sources into Docling documents and markdown."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Docling processor.

        Args:
            settings: Application settings.
        """
        self.settings = settings

    async def convert_source(self, source: CollectedSource) -> IngestionDocument:
        """Convert a collected source into an ingestion document.

        Args:
            source: Collected source payload.

        Returns:
            IngestionDocument ready for chunking.

        Raises:
            ValueError: If Docling cannot process the source content.
        """
        await logger.info(
            "docling_convert_start",
            action="docling_convert_start",
            source_type=source.frontmatter.source_type,
            source_url=source.frontmatter.source_url,
        )
        materialized = await self._materialize_content(source.content)
        try:
            docling_doc = await self._convert_docling(materialized.path)
        finally:
            if materialized.cleanup:
                await self._cleanup_tempfile(materialized.path)

        markdown = self._export_to_markdown(docling_doc)
        title_hint = source.frontmatter.source_title or source.frontmatter.source_url or ""
        title = self._extract_title(markdown, title_hint)

        identity = DocumentIdentity.build(
            source_type=source.frontmatter.source_type,
            source_url=source.frontmatter.source_url,
            content_hash=materialized.content_hash,
            source_id=source.frontmatter.source_id,
            source_mime_type=source.frontmatter.source_mime_type,
        )
        namespace = self._apply_default_namespace(
            source.namespace,
            source.frontmatter.source_url,
            fallback_group=source.frontmatter.source_type,
        )

        source_mask = self._source_mask(identity.source_type)
        frontmatter = source.frontmatter.model_copy(deep=True)
        frontmatter.metadata = {
            **frontmatter.metadata,
            "document_uid": identity.document_uid,
            "content_hash": identity.content_hash,
            "source_group": namespace.source_group,
            "user_id": namespace.user_id,
            "org_id": namespace.org_id,
            "source_mask": source_mask,
            "document_title": title,
        }

        metadata = IngestionMetadata(
            identity=identity,
            namespace=Namespace(**namespace.model_dump()),
            frontmatter=frontmatter,
            collected_at=frontmatter.source_fetched_at or ingestion_timestamp(),
            ingested_at=ingestion_timestamp(),
            source_metadata={**source.metadata, "source_mask": source_mask},
        )

        ingestion_doc = IngestionDocument(
            content=markdown,
            docling_document=docling_doc,
            docling_json=self._serialize_docling(docling_doc),
            page_texts=self._extract_page_texts(docling_doc),
            title=title,
            metadata=metadata,
        )

        await logger.info(
            "docling_convert_complete",
            action="docling_convert_complete",
            document_uid=identity.document_uid,
            title=title,
        )
        return ingestion_doc

    async def _materialize_content(self, content: SourceContent) -> _MaterializedContent:
        """Materialize source content into a file for Docling conversion."""
        if content.kind == SourceContentKind.FILE_PATH:
            file_path = str(content.data)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file not found: {file_path}")
            content_hash = await asyncio.to_thread(self._hash_file, file_path)
            return _MaterializedContent(
                path=file_path,
                content_hash=content_hash,
                cleanup=False,
            )

        if isinstance(content.data, str):
            data_bytes = content.data.encode("utf-8")
        else:
            data_bytes = content.data

        content_hash = self._hash_bytes(data_bytes)
        suffix = self._guess_suffix(content)
        temp_path = await asyncio.to_thread(self._write_tempfile, data_bytes, suffix)
        return _MaterializedContent(
            path=temp_path,
            content_hash=content_hash,
            cleanup=True,
        )

    @staticmethod
    def _guess_suffix(content: SourceContent) -> str:
        """Determine an appropriate file suffix for Docling."""
        if content.filename:
            suffix = Path(content.filename).suffix
            if suffix:
                if suffix.lower() == ".txt":
                    return ".md"
                return suffix
        if content.kind == SourceContentKind.HTML:
            return ".html"
        if content.kind == SourceContentKind.MARKDOWN:
            return ".md"
        if content.mime_type == "application/pdf":
            return ".pdf"
        return ".bin"

    @staticmethod
    def _write_tempfile(data: bytes, suffix: str) -> str:
        """Write data to a temporary file and return the file path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(data)
            handle.flush()
            return handle.name

    async def _cleanup_tempfile(self, path: str) -> None:
        """Remove temporary files created for Docling conversion."""
        try:
            await asyncio.to_thread(os.remove, path)
        except FileNotFoundError:
            return

    async def _convert_docling(self, file_path: str) -> DoclingDocument:
        """Convert a file to a Docling document."""

        def _convert() -> DoclingDocument:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            return result.document

        try:
            return await asyncio.to_thread(_convert)
        except Exception as exc:
            message = str(exc)
            if "unsupported" in message.lower():
                await logger.error(
                    "docling_unsupported_format",
                    action="docling_unsupported_format",
                    error=message,
                )
                raise ValueError("Docling unsupported format") from exc
            if "oom" in message.lower() or "out of memory" in message.lower():
                await logger.error(
                    "docling_oom",
                    action="docling_oom",
                    error=message,
                )
                raise MemoryError("Docling out of memory") from exc
            await logger.error(
                "docling_conversion_failed",
                action="docling_conversion_failed",
                error=message,
            )
            raise

    @staticmethod
    def _export_to_markdown(docling_doc: DoclingDocument) -> str:
        """Export Docling document to Markdown with table extraction."""
        try:
            return docling_doc.export_to_markdown(table_mode="markdown")
        except TypeError:
            try:
                return docling_doc.export_to_markdown(table_format="markdown")
            except TypeError:
                return docling_doc.export_to_markdown()

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        """Extract title from markdown or fallback string."""
        for line in content.split("\n")[:10]:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return os.path.splitext(os.path.basename(fallback))[0] or fallback

    @staticmethod
    def _hash_bytes(data: bytes) -> str:
        """Compute SHA-256 hash of bytes."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _hash_file(file_path: str) -> str:
        """Compute SHA-256 hash for a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _source_mask(source_type: str) -> int:
        mapping = {"web": 1, "gdrive": 2, "upload": 4}
        return mapping.get(source_type, 0)

    @staticmethod
    def _serialize_docling(docling_doc: DoclingDocument) -> Dict[str, Any]:
        """Serialize Docling document to a JSON-friendly dict."""
        if hasattr(docling_doc, "model_dump"):
            try:
                return docling_doc.model_dump(mode="json")
            except TypeError:
                return docling_doc.model_dump()
        if hasattr(docling_doc, "json"):
            try:
                return json.loads(docling_doc.json())
            except Exception:
                pass
        if hasattr(docling_doc, "dict"):
            return docling_doc.dict()
        if hasattr(docling_doc, "to_dict"):
            return docling_doc.to_dict()
        return {"raw": str(docling_doc)}

    @staticmethod
    def _extract_page_texts(docling_doc: DoclingDocument) -> Dict[str, str]:
        """Extract page-level markdown from Docling document."""
        page_texts: Dict[str, str] = {}
        pages = getattr(docling_doc, "pages", None)
        if not pages:
            return page_texts

        for index, page in enumerate(pages, start=1):
            text = getattr(page, "text", None) or getattr(page, "content", None)
            if not text and hasattr(page, "export_to_markdown"):
                try:
                    text = page.export_to_markdown()
                except Exception:
                    text = None
            if text:
                page_texts[str(index)] = text
        return page_texts

    @staticmethod
    def _apply_default_namespace(
        namespace: Namespace,
        source_url: str,
        fallback_group: Optional[str] = None,
    ) -> Namespace:
        """Apply default source group to namespace if missing."""
        if namespace.source_group:
            return namespace
        parsed = urlparse(source_url)
        if parsed.hostname:
            return namespace.model_copy(update={"source_group": parsed.hostname})
        return namespace.model_copy(update={"source_group": fallback_group or ""})


__all__ = ["DoclingProcessor"]
