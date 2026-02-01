"""Crawl4AI ingestion source implementing the IngestionSource protocol."""

from typing import Any

from .ingestion_source import IngestionSource
from ..docling.processor import DocumentProcessor, ProcessedDocument
from ...settings import load_settings


class Crawl4AIIngestionSource(IngestionSource):
    def __init__(
        self,
        url: str,
        deep: bool = False,
        max_depth: int | None = None,
        page_index: int = 0,
        namespace: dict[str, Any] | None = None,
    ) -> None:
        self.url = url
        self.deep = deep
        self.max_depth = max_depth
        self.page_index = page_index
        self.namespace = namespace or {}
        self.settings = load_settings()
        self.processor = DocumentProcessor(self.settings)

    def fetch_and_convert(self, **kwargs) -> ProcessedDocument:
        """
        Fetch a URL via Crawl4AI and return a ProcessedDocument for ingestion.

        Note: If deep crawling returns multiple pages, select a page via
        `page_index` (default: first page).
        """
        import asyncio
        import concurrent.futures

        async def _run() -> ProcessedDocument:
            processed_docs = await self.processor.process_web_url(
                url=self.url,
                deep=self.deep,
                max_depth=self.max_depth,
                namespace=self.namespace,
            )
            if not processed_docs:
                raise ValueError(f"No document content returned for url: {self.url}")
            if self.page_index < 0 or self.page_index >= len(processed_docs):
                raise IndexError(
                    "page_index out of range for crawl results: "
                    f"{self.page_index} (total={len(processed_docs)})"
                )
            return processed_docs[self.page_index]

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_run())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(_run())).result()
