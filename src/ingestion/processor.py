"""Document processing utilities for Docling-based ingestion."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument

from src.ingestion.google_drive import (
    GoogleDriveClient,
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_SLIDES_MIME_TYPE,
    GOOGLE_PDF_EXPORT,
)
from src.ingestion.models import MetadataPassport
from src.integrations.crawl4ai import Crawl4AIClient
from src.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    """Result of processing a single document source."""

    content: str
    docling_document: DoclingDocument
    docling_json: Dict[str, Any]
    page_texts: Dict[str, str]
    title: str
    source_type: str
    source_url: str
    content_hash: str
    metadata: Dict[str, Any]


class DocumentProcessor:
    """Convert ingestion sources into Docling documents and markdown."""

    def __init__(
        self,
        settings: Settings,
        crawl_client: Crawl4AIClient | None = None,
        drive_client: GoogleDriveClient | None = None,
    ) -> None:
        self.settings = settings
        self.crawl_client = crawl_client or Crawl4AIClient()
        self._drive_client = drive_client

    async def process_web_url(
        self,
        url: str,
        deep: bool = False,
        max_depth: Optional[int] = None,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> list[ProcessedDocument]:
        """Fetch a URL with Crawl4AI and convert raw HTML to Docling."""
        if deep:
            pages = await self.crawl_client.crawl_deep(
                start_url=url,
                max_depth=max_depth or self.settings.crawl4ai_max_depth,
                word_count_threshold=self.settings.crawl4ai_word_count_threshold,
                remove_overlay_elements=self.settings.crawl4ai_remove_overlay_elements,
                remove_base64_images=self.settings.crawl4ai_remove_base64_images,
                cache_mode=self.settings.crawl4ai_cache_mode,
                browser_type=self.settings.crawl4ai_browser_type,
                timeout=self.settings.crawl4ai_timeout,
                cookies=self.settings.crawl4ai_cookies,
                user_agent=self.settings.crawl4ai_user_agent,
            )
        else:
            page = await self.crawl_client.crawl_single_page(
                url=url,
                word_count_threshold=self.settings.crawl4ai_word_count_threshold,
                remove_overlay_elements=self.settings.crawl4ai_remove_overlay_elements,
                remove_base64_images=self.settings.crawl4ai_remove_base64_images,
                cache_mode=self.settings.crawl4ai_cache_mode,
                browser_type=self.settings.crawl4ai_browser_type,
                timeout=self.settings.crawl4ai_timeout,
                cookies=self.settings.crawl4ai_cookies,
                user_agent=self.settings.crawl4ai_user_agent,
            )
            pages = [page] if page else []

        processed: list[ProcessedDocument] = []
        for page in pages:
            if not page:
                continue
            html = page.get("html") or ""
            if not html.strip():
                logger.warning("crawl4ai_empty_html", extra={"url": page.get("url")})
                continue

            page_url = page.get("url", url)
            metadata = {
                "crawl_metadata": page.get("metadata", {}),
                "crawl_url": page_url,
                "crawl_start_url": url if deep else None,
            }
            metadata.update(self._default_namespace(url, namespace, fallback_group="web"))
            processed.append(
                self._process_html(
                    html=html,
                    source_url=page_url,
                    title_hint=page.get("metadata", {}).get("page_title"),
                    extra_metadata=metadata,
                )
            )

        return processed

    async def process_google_file(
        self,
        file_id: str,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Fetch and convert a Google Drive file ID into Docling."""
        client = self._get_drive_client()

        metadata = await asyncio.to_thread(client.get_file, file_id)
        name = metadata.get("name", file_id)
        mime_type = metadata.get("mimeType", "")

        if mime_type in {GOOGLE_DOC_MIME_TYPE, GOOGLE_SLIDES_MIME_TYPE}:
            file_bytes = await asyncio.to_thread(
                client.export_file,
                file_id,
                GOOGLE_PDF_EXPORT,
            )
            filename = f"{name}.pdf"
        else:
            file_bytes = await asyncio.to_thread(client.download_file, file_id)
            filename = name

        source_url = metadata.get("webViewLink") or (
            f"https://drive.google.com/file/d/{file_id}/view"
        )

        extra_metadata = {
            "gdrive_file_id": file_id,
            "gdrive_name": name,
            "gdrive_mime_type": mime_type,
            "gdrive_modified_time": metadata.get("modifiedTime"),
            "source_url": source_url,
        }
        extra_metadata.update(
            self._default_namespace(source_url, namespace, fallback_group="gdrive")
        )

        return self._process_bytes(
            file_bytes=file_bytes,
            filename=filename,
            source_type="gdrive",
            source_url=source_url,
            title_hint=name,
            extra_metadata=extra_metadata,
        )

    async def list_google_drive_files_in_folder(
        self, folder_id: str
    ) -> list[dict[str, str]]:
        """List files in a Google Drive folder."""
        client = self._get_drive_client()
        return await asyncio.to_thread(client.list_files_in_folder, folder_id)

    def process_local_file(
        self,
        file_path: str,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Convert a local file path into Docling markdown."""
        file_path = os.path.abspath(file_path)
        source_url = f"file://{file_path}"
        with open(file_path, "rb") as handle:
            file_bytes = handle.read()

        extra_metadata = {"file_path": file_path}
        extra_metadata.update(
            self._default_namespace(source_url, namespace, fallback_group="upload")
        )
        return self._process_bytes(
            file_bytes=file_bytes,
            filename=os.path.basename(file_path),
            source_type="upload",
            source_url=source_url,
            title_hint=os.path.basename(file_path),
            extra_metadata=extra_metadata,
        )

    def process_upload(
        self,
        file_bytes: bytes,
        filename: str,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Convert uploaded bytes into Docling markdown."""
        source_url = f"upload://{filename}"
        extra_metadata = {}
        extra_metadata.update(
            self._default_namespace(source_url, namespace, fallback_group="upload")
        )
        return self._process_bytes(
            file_bytes=file_bytes,
            filename=filename,
            source_type="upload",
            source_url=source_url,
            title_hint=filename,
            extra_metadata=extra_metadata,
        )

    def _process_html(
        self,
        html: str,
        source_url: str,
        title_hint: Optional[str],
        extra_metadata: Dict[str, Any],
    ) -> ProcessedDocument:
        """Convert raw HTML to Docling markdown."""
        content_hash = self._hash_bytes(html.encode("utf-8"))
        with self._tempfile(suffix=".html") as temp_file:
            temp_file.write(html.encode("utf-8"))
            temp_file.flush()
            return self._convert_docling(
                file_path=temp_file.name,
                source_type="web",
                source_url=source_url,
                title_hint=title_hint or source_url,
                content_hash=content_hash,
                extra_metadata=extra_metadata,
            )

    def _process_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        source_type: str,
        source_url: str,
        title_hint: Optional[str],
        extra_metadata: Dict[str, Any],
    ) -> ProcessedDocument:
        """Convert file bytes to Docling markdown."""
        content_hash = self._hash_bytes(file_bytes)
        suffix = Path(filename).suffix or ".bin"

        with self._tempfile(suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_file.flush()
            return self._convert_docling(
                file_path=temp_file.name,
                source_type=source_type,
                source_url=source_url,
                title_hint=title_hint or filename,
                content_hash=content_hash,
                extra_metadata=extra_metadata,
            )

    def _convert_docling(
        self,
        file_path: str,
        source_type: str,
        source_url: str,
        title_hint: str,
        content_hash: str,
        extra_metadata: Dict[str, Any],
    ) -> ProcessedDocument:
        try:
            converter = DocumentConverter()
            result = converter.convert(file_path)
            docling_doc = result.document
        except Exception as exc:
            message = str(exc)
            if "unsupported" in message.lower():
                logger.error("docling_unsupported_format", extra={"error": message})
                raise ValueError("Docling unsupported format") from exc
            if "oom" in message.lower() or "out of memory" in message.lower():
                logger.error("docling_oom", extra={"error": message})
                raise MemoryError("Docling out of memory") from exc
            logger.error("docling_conversion_failed", extra={"error": message})
            raise

        markdown = self._export_to_markdown(docling_doc)
        title = self._extract_title(markdown, title_hint)

        passport = MetadataPassport(
            source_type=source_type,
            source_url=source_url,
            document_title=title,
            page_number=None,
            heading_path=[],
            ingestion_timestamp=datetime.now().isoformat(),
            content_hash=content_hash,
        )

        source_mask = self._source_mask(source_type)
        metadata = {
            **passport.model_dump(),
            "source": source_url,
            "file_size": len(markdown),
            "line_count": len(markdown.split("\n")),
            "word_count": len(markdown.split()),
            "source_mask": source_mask,
            **extra_metadata,
        }

        return ProcessedDocument(
            content=markdown,
            docling_document=docling_doc,
            docling_json=self._serialize_docling(docling_doc),
            page_texts=self._extract_page_texts(docling_doc),
            title=title,
            source_type=source_type,
            source_url=source_url,
            content_hash=content_hash,
            metadata=metadata,
        )

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
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _source_mask(source_type: str) -> int:
        mapping = {
            "web": 1,
            "gdrive": 2,
            "upload": 4,
        }
        return mapping.get(source_type, 0)

    @staticmethod
    def _serialize_docling(docling_doc: DoclingDocument) -> Dict[str, Any]:
        if hasattr(docling_doc, "model_dump"):
            return docling_doc.model_dump()
        if hasattr(docling_doc, "dict"):
            return docling_doc.dict()
        if hasattr(docling_doc, "to_dict"):
            return docling_doc.to_dict()
        return {"raw": str(docling_doc)}

    @staticmethod
    def _extract_page_texts(docling_doc: DoclingDocument) -> Dict[str, str]:
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
    def _default_namespace(
        source_url: str,
        namespace: Optional[Dict[str, Any]],
        fallback_group: Optional[str] = None,
    ) -> Dict[str, Any]:
        namespace = namespace or {}
        if namespace.get("source_group"):
            return namespace
        parsed = urlparse(source_url)
        if parsed.hostname:
            return {**namespace, "source_group": parsed.hostname}
        return {**namespace, "source_group": fallback_group or ""}

    def _get_drive_client(self) -> GoogleDriveClient:
        if not self._drive_client:
            self._drive_client = GoogleDriveClient(
                self.settings.google_service_account_file,
                subject=self.settings.google_impersonate_subject,
            )
        return self._drive_client

    @staticmethod
    def _tempfile(suffix: str) -> Any:
        return tempfile.NamedTemporaryFile(delete=True, suffix=suffix)
