"""Crawl4AI collector implementing the SourceCollector protocol."""

from __future__ import annotations

from typing import List

from mdrag.capabilities.ingestion.models import (
    CollectedSource,
    SourceContent,
    SourceContentKind,
    WebCollectionRequest,
)
from mdrag.capabilities.ingestion.protocols import SourceCollector
from mdrag.integrations.crawl4ai import Crawl4AIClient
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import Settings, load_settings

logger = get_logger(__name__)


class Crawl4AICollector(SourceCollector[WebCollectionRequest]):
    """Collect web content via Crawl4AI."""

    name = "crawl4ai"

    def __init__(
        self,
        client: Crawl4AIClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.client = client or Crawl4AIClient()

    async def collect(self, request: WebCollectionRequest) -> List[CollectedSource]:
        """Collect web sources and normalize for ingestion."""
        await logger.info(
            "collector_crawl4ai_start",
            action="collector_crawl4ai_start",
            url=request.url,
            deep=request.deep,
            max_depth=request.max_depth,
        )

        if request.deep:
            sources = await self.client.crawl_deep(
                start_url=request.url,
                max_depth=request.max_depth or self.settings.crawl4ai_max_depth,
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
            source = await self.client.crawl_single_page(
                url=request.url,
                word_count_threshold=self.settings.crawl4ai_word_count_threshold,
                remove_overlay_elements=self.settings.crawl4ai_remove_overlay_elements,
                remove_base64_images=self.settings.crawl4ai_remove_base64_images,
                cache_mode=self.settings.crawl4ai_cache_mode,
                browser_type=self.settings.crawl4ai_browser_type,
                timeout=self.settings.crawl4ai_timeout,
                cookies=self.settings.crawl4ai_cookies,
                user_agent=self.settings.crawl4ai_user_agent,
            )
            sources = [source] if source else []

        collected: List[CollectedSource] = []
        for source in sources:
            if not source:
                continue
            payload = source.html or source.content or ""
            if not payload.strip():
                await logger.warning(
                    "collector_crawl4ai_empty_payload",
                    action="collector_crawl4ai_empty_payload",
                    url=source.frontmatter.source_url or request.url,
                )
                continue
            kind = (
                SourceContentKind.HTML
                if source.html and source.html.strip()
                else SourceContentKind.MARKDOWN
            )
            collected.append(
                CollectedSource(
                    frontmatter=source.frontmatter,
                    content=SourceContent(kind=kind, data=payload),
                    metadata=source.metadata,
                    links=source.links,
                    namespace=request.namespace,
                )
            )

        await logger.info(
            "collector_crawl4ai_complete",
            action="collector_crawl4ai_complete",
            url=request.url,
            collected_count=len(collected),
        )
        return collected


__all__ = ["Crawl4AICollector"]
