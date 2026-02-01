"""Google Docs API low-level wrapper with composition-based architecture."""

import asyncio
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from markdownify import markdownify as md
from ..models import GoogleDocumentTab
from ...models import SourceFrontmatter, SourceURL

from .exceptions import GoogleDriveException
from .google_auth import GoogleAuth
from .google_drive import GoogleDrive


class GoogleDoc(GoogleDrive):
    """Low-level wrapper for Google Docs API operations with composition-based architecture.

    Inherits from GoogleDrive to access Drive API methods and file operations.
    Overrides Search and Export with Docs-specific implementations.
    Provides access to document structure and tabs metadata when available.
    """

    def __init__(self, authenticator: GoogleAuth):
        """
        Initialize Google Docs API client.

        Args:
            authenticator: GoogleAuth instance
        """
        super().__init__(authenticator)
        self._docs_service = None

        # Override with Docs-specific implementations
        self.search = GoogleDoc.Search(self)
        self.export = GoogleDoc.Export(self)

    @property
    def docs_service(self):
        """Lazy-loaded Google Docs API service client."""
        if self._docs_service is None:
            self._docs_service = build(
                "docs", "v1", credentials=self.authenticator.get_credentials()
            )
        return self._docs_service

    async def get_by_id(self, document_id: str, include_tabs: bool = False) -> dict[str, Any]:
        """Fetch a Google Doc with optional tabs content included.

        Args:
            document_id: The Google Docs document ID
            include_tabs: Attempt to include tabs content/metadata

        Returns:
            Raw Docs API response

        Raises:
            GoogleDriveException: If API call fails
        """
        await self.refresh_credentials_if_needed()
        try:
            if include_tabs:
                # Some environments may not support this param; surface errors clearly
                return await asyncio.to_thread(
                    lambda: self.docs_service.documents()
                    .get(documentId=document_id, includeTabsContent=True)
                    .execute()
                )
            return await asyncio.to_thread(
                lambda: self.docs_service.documents().get(documentId=document_id).execute()
            )
        except HttpError as e:
            raise GoogleDriveException(f"Failed to get Google Doc {document_id}: {e}", e) from e

    async def get_tabs_metadata(self, document_id: str) -> list[dict[str, Any]]:
        """Extract tabs metadata list from Docs API response when present.

        Returns an empty list if the response contains no tabs info.
        """
        doc = await self.get_by_id(document_id, include_tabs=True)
        tabs = doc.get("tabs") or []
        # Normalize expected keys when present
        normalized: list[dict[str, Any]] = []
        for i, t in enumerate(tabs):
            normalized.append(
                {
                    "tabId": t.get("tabId") or str(i),
                    "title": t.get("title") or f"Tab {i + 1}",
                    "index": t.get("index", i),
                    "parentTabId": t.get("parentTabId"),
                }
            )
        return normalized

    async def export_tabs(self, document_id: str) -> list[GoogleDocumentTab]:
        """Export a Google Doc into per-tab markdown sections.

        Strategy mirrors gdrive_sync approach:
        - Export full HTML
        - Split on '<p class="title"' delimiter
        - Extract title/ids from the first title element per chunk
        - Map metadata from Docs API tabs when available

        Args:
            document_id: Google Docs document ID

        Returns:
            List of GoogleDocumentTab models with markdown content
        """
        # Fetch tabs metadata (best-effort)
        tabs_meta = await self._safe_get_tabs_metadata(document_id)
        title_to_meta: dict[str, dict[str, Any]] = {
            (t.get("title") or "").strip(): t for t in tabs_meta
        }

        # Fetch document web view link for potential deep links
        file_meta = await self.get_file_metadata(
            document_id,
            fields="id,name,webViewLink,mimeType,createdTime,modifiedTime,owners,description",
        )
        base_url = file_meta.get("webViewLink")
        owners = [
            owner.get("displayName", owner.get("emailAddress", "Unknown"))
            for owner in (file_meta.get("owners") or [])
        ]
        description = file_meta.get("description")

        # Export full HTML
        html = await self._download_html(document_id)
        return self._build_tabs_from_html(
            document_id=document_id,
            html=html,
            title_to_meta=title_to_meta,
            file_meta=file_meta,
            base_url=base_url,
            owners=owners,
            description=description,
        )

    async def _download_html(self, document_id: str) -> str:
        """Download document as HTML (returns ZIP for large docs)."""
        import zipfile

        request = await self.export_as_media(document_id, "application/zip")

        def _download_sync() -> str:
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Extract HTML from the zip file
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as zip_file:
                # Find the main HTML file (usually the first .html file)
                html_files = [name for name in zip_file.namelist() if name.endswith(".html")]
                if not html_files:
                    raise ValueError("No HTML file found in exported ZIP")
                # Read the first HTML file
                with zip_file.open(html_files[0]) as html_file:
                    return html_file.read().decode("utf-8", errors="ignore")

        return await asyncio.to_thread(_download_sync)

    async def _download_html_with_assets(self, document_id: str) -> tuple[str, dict[str, bytes]]:
        """Download document HTML and bundled assets from the export ZIP."""
        import zipfile

        request = await self.export_as_media(document_id, "application/zip")

        def _download_sync() -> tuple[str, dict[str, bytes]]:
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            buf.seek(0)
            assets: dict[str, bytes] = {}
            with zipfile.ZipFile(buf, "r") as zip_file:
                html_files = [name for name in zip_file.namelist() if name.endswith(".html")]
                if not html_files:
                    raise ValueError("No HTML file found in exported ZIP")
                with zip_file.open(html_files[0]) as html_file:
                    html = html_file.read().decode("utf-8", errors="ignore")

                for name in zip_file.namelist():
                    if name.endswith("/"):
                        continue
                    if name.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
                    ):
                        with zip_file.open(name) as asset_file:
                            assets[name] = asset_file.read()

            return html, assets

        return await asyncio.to_thread(_download_sync)

    def _split_on_title(self, html: str) -> list[str]:
        """Split HTML on title delimiter."""
        # Split using the known delimiter; discard any pre-title header content
        delimiter = '<p class="title"'
        if delimiter not in html:
            # Fallback: single chunk
            return [html]
        parts = html.split(delimiter)
        # Reattach the delimiter to each subsequent part
        return [f"{delimiter}{p}" for p in parts[1:]]

    def _extract_title_and_id(self, html_chunk: str) -> tuple[str | None, str | None]:
        """Extract title text and heading ID from HTML chunk."""
        soup = BeautifulSoup(html_chunk, "html.parser")
        title_p = soup.find("p", {"class": "title"})
        if not title_p:
            return None, None
        title_text = title_p.get_text(strip=True) if title_p else None
        heading_id = title_p.get("id") or None
        if isinstance(heading_id, list):
            heading_id = heading_id[0] if heading_id else None
        elif heading_id is not None:
            heading_id = str(heading_id)
        return title_text, heading_id

    async def export_tabs_to_directory(
        self,
        document_id: str,
        output_dir: str | Path,
        *,
        include_metadata_on_fallback: bool = True,
    ) -> list[Path]:
        """Export Google Doc tabs to individual markdown files.

        Args:
            document_id: Google Docs document ID
            output_dir: Directory to write markdown files

        Returns:
            List of file paths written
        """
        _ = include_metadata_on_fallback

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        file_meta = await self.get_file_metadata(document_id, fields="id,name")
        doc_name = file_meta.get("name") or document_id
        safe_doc_name = self._sanitize_filename(doc_name, fallback=document_id)
        folder_name = (
            f"{document_id}-{safe_doc_name}"
            if safe_doc_name and safe_doc_name != document_id
            else document_id
        )
        output_path = output_root / folder_name
        output_path.mkdir(parents=True, exist_ok=True)

        html, assets = await self._download_html_with_assets(document_id)
        self._write_assets(output_path, assets)

        tabs_meta = await self._safe_get_tabs_metadata(document_id)
        title_to_meta: dict[str, dict[str, Any]] = {
            (t.get("title") or "").strip(): t for t in tabs_meta
        }
        file_meta_full = await self.get_file_metadata(
            document_id,
            fields="id,name,webViewLink,mimeType,createdTime,modifiedTime,owners,description",
        )
        base_url = file_meta_full.get("webViewLink")
        owners = [
            owner.get("displayName", owner.get("emailAddress", "Unknown"))
            for owner in (file_meta_full.get("owners") or [])
        ]
        description = file_meta_full.get("description")

        tabs = self._build_tabs_from_html(
            document_id=document_id,
            html=html,
            title_to_meta=title_to_meta,
            file_meta=file_meta_full,
            base_url=base_url,
            owners=owners,
            description=description,
            image_path_map=self._build_image_path_map(assets),
        )
        written_paths: list[Path] = []

        for tab in tabs:
            safe_title = self._sanitize_filename(
                tab.title,
                fallback=f"tab-{tab.index + 1}",
            )
            filename = f"{tab.index + 1:02d}-{safe_title}.md"
            file_path = output_path / filename
            content = tab.to_markdown()
            await asyncio.to_thread(file_path.write_text, content, encoding="utf-8")
            written_paths.append(file_path)

        return written_paths

    def _build_tabs_from_html(
        self,
        *,
        document_id: str,
        html: str,
        title_to_meta: dict[str, dict[str, Any]],
        file_meta: dict[str, Any],
        base_url: str | None,
        owners: list[str],
        description: str | None,
        image_path_map: dict[str, str] | None = None,
    ) -> list[GoogleDocumentTab]:
        chunks = self._split_on_title(html)

        tabs: list[GoogleDocumentTab] = []
        for idx, chunk_html in enumerate(chunks):
            title, heading_id = self._extract_title_and_id(chunk_html)
            meta = title_to_meta.get(title or "")
            tab_id = (meta.get("tabId") if meta else None) or heading_id or str(idx)
            parent_tab_id = meta.get("parentTabId") if meta else None

            tab_url = f"{base_url}#{heading_id}" if base_url and heading_id else base_url

            urls = self._extract_urls_from_html(chunk_html)
            image_entries = self._extract_image_entries(
                chunk_html,
                image_path_map=image_path_map,
            )
            urls.extend(self._image_entries_to_urls(image_entries))

            markdown = md(chunk_html or "")
            markdown = self._replace_markdown_images(markdown, image_entries)

            frontmatter = SourceFrontmatter(
                source_type="gdrive",
                source_url=tab_url or "",
                source_title=title or file_meta.get("name"),
                source_id=file_meta.get("id") or document_id,
                source_mime_type=file_meta.get("mimeType"),
                source_web_view_url=base_url,
                source_created_at=file_meta.get("createdTime"),
                source_modified_at=file_meta.get("modifiedTime"),
                source_owners=owners,
                source_description=description,
                metadata={
                    "tab_id": str(tab_id),
                    "tab_name": title or f"Tab {idx + 1}",
                    "urls": [url.model_dump(exclude_none=True) for url in urls],
                },
            )

            tabs.append(
                GoogleDocumentTab(
                    frontmatter=frontmatter,
                    content=markdown,
                    html=chunk_html,
                    metadata={"document_id": document_id},
                    links=[url.url for url in urls],
                    tab_id=str(tab_id),
                    title=title or f"Tab {idx + 1}",
                    index=idx,
                    parent_tab_id=str(parent_tab_id) if parent_tab_id else None,
                    tab_url=tab_url,
                )
            )

        return tabs

    def _sanitize_filename(self, value: str, fallback: str) -> str:
        """Sanitize a string for safe filesystem use."""
        cleaned = re.sub(r"[^\w\s-]", "", value or "", flags=re.UNICODE).strip()
        cleaned = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
        return cleaned or fallback

    def _write_assets(self, output_path: Path, assets: dict[str, bytes]) -> None:
        """Write bundled export assets to disk under the output path."""
        for asset_name, data in assets.items():
            target = output_path / asset_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def _build_image_path_map(self, assets: dict[str, bytes]) -> dict[str, str]:
        """Map HTML image src values to local relative paths."""
        mapping: dict[str, str] = {}
        for name in assets.keys():
            mapping[name] = name
            mapping[Path(name).name] = name
        return mapping

    def _extract_urls_from_html(self, html_chunk: str) -> list[SourceURL]:
        """Extract named URLs from anchor tags."""
        soup = BeautifulSoup(html_chunk, "html.parser")
        urls: list[SourceURL] = []
        seen: set[tuple[str, str | None]] = set()

        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue
            normalized = self._normalize_url(href)
            if not normalized:
                continue
            name = anchor.get_text(strip=True) or None
            key = (normalized, name)
            if key in seen:
                continue
            seen.add(key)
            urls.append(SourceURL(name=name, url=normalized, kind="link"))

        return urls

    def _normalize_url(self, href: str) -> str | None:
        """Normalize Google redirect URLs to the target URL."""
        if not href:
            return None
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.netloc in {"www.google.com", "google.com"} and parsed.path == "/url":
            params = parse_qs(parsed.query)
            target = params.get("q")
            if target:
                return unquote(target[0])
        return href

    @dataclass
    class _ImageEntry:
        alt: str | None
        src: str
        local_path: str | None
        source_url: str | None

    def _extract_image_entries(
        self,
        html_chunk: str,
        *,
        image_path_map: dict[str, str] | None = None,
    ) -> list[_ImageEntry]:
        soup = BeautifulSoup(html_chunk, "html.parser")
        entries: list[GoogleDoc._ImageEntry] = []

        for img in soup.find_all("img"):
            src = img.get("src") or ""
            data_src = img.get("data-src") or ""
            source_url = self._normalize_url(data_src) or self._normalize_url(src)
            local_path = None
            if image_path_map and src in image_path_map:
                local_path = image_path_map[src]
            alt = img.get("alt") or None
            if not src:
                continue
            entries.append(
                GoogleDoc._ImageEntry(
                    alt=alt,
                    src=src,
                    local_path=local_path,
                    source_url=source_url,
                )
            )

        return entries

    def _image_entries_to_urls(self, entries: list[_ImageEntry]) -> list[SourceURL]:
        urls: list[SourceURL] = []
        for entry in entries:
            url = entry.source_url or entry.local_path or entry.src
            if not url:
                continue
            name = entry.alt or Path(entry.local_path or entry.src).name or None
            urls.append(SourceURL(name=name, url=url, kind="image"))
        return urls

    def _replace_markdown_images(self, markdown: str, entries: list[_ImageEntry]) -> str:
        if not entries:
            return markdown

        images_iter = iter(entries)

        def _render_image(entry: GoogleDoc._ImageEntry) -> str:
            alt_text = entry.alt or ""
            local_path = entry.local_path or entry.src
            link_target = entry.source_url or local_path
            if link_target:
                return f"[![{alt_text}]({local_path})]({link_target})"
            return f"![{alt_text}]({local_path})"

        def _replace_img(match: re.Match) -> str:
            try:
                entry = next(images_iter)
            except StopIteration:
                return match.group(0)
            return _render_image(entry)

        markdown = re.sub(r"!\[[^\]]*\]\([^\)]*\)", _replace_img, markdown)
        markdown = re.sub(r"<!--\s*image\s*-->", _replace_img, markdown)
        return markdown

    async def _safe_get_tabs_metadata(self, document_id: str) -> list[dict[str, Any]]:
        """Get tabs metadata with fallback."""
        try:
            return await self.get_tabs_metadata(document_id)
        except HttpError:
            # If Docs API tabs are unavailable, proceed without metadata
            return []


__all__ = ["GoogleDoc"]
