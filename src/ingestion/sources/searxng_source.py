"""SearXNG ingestion source implementing the IngestionSource protocol."""

from typing import Any

import httpx

from .ingestion_source import IngestionSource
from ..docling.processor import DocumentProcessor, ProcessedDocument
from ...settings import load_settings


class SearXNGIngestionSource(IngestionSource):
    def __init__(
        self,
        query: str,
        result_index: int = 0,
        result_count: int = 5,
        categories: str | None = None,
        engines: list[str] | None = None,
        searxng_url: str | None = None,
        namespace: dict[str, Any] | None = None,
    ) -> None:
        self.query = query
        self.result_index = result_index
        self.result_count = result_count
        self.categories = categories
        self.engines = engines
        self.namespace = namespace or {}
        self.settings = load_settings()
        self.searxng_url = (searxng_url or self.settings.searxng_url).rstrip("/")
        self.processor = DocumentProcessor(self.settings)

    def fetch_and_convert(self, **kwargs) -> ProcessedDocument:
        """
        Query SearXNG and ingest the selected result URL as a ProcessedDocument.

        Select which result to ingest via `result_index` (default: first result).
        """
        import asyncio
        import concurrent.futures

        async def _query_searxng() -> list[dict[str, Any]]:
            params = {
                "q": self.query.strip(),
                "format": "json",
                "pageno": 1,
            }
            if self.categories:
                params["categories"] = self.categories
            if self.engines:
                params["engines"] = ",".join(self.engines)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.searxng_url}/search", params=params)
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            return results[: max(self.result_count, 0)]

        async def _run() -> ProcessedDocument:
            results = await _query_searxng()
            if not results:
                raise ValueError(f"No results returned for query: {self.query}")
            if self.result_index < 0 or self.result_index >= len(results):
                raise IndexError(
                    "result_index out of range for search results: "
                    f"{self.result_index} (total={len(results)})"
                )

            target = results[self.result_index]
            url = (target.get("url") or "").strip()
            if not url:
                raise ValueError("Selected SearXNG result is missing a URL")

            processed_docs = await self.processor.process_web_url(
                url=url,
                deep=False,
                namespace=self.namespace,
            )
            if not processed_docs:
                raise ValueError(f"No document content returned for url: {url}")
            return processed_docs[0]

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_run())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(_run())).result()
