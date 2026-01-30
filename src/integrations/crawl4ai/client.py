"""Crawl4AI service client for web crawling operations."""

import logging
from typing import Any

from crawl4ai import AsyncWebCrawler

from src.logging_utils import log_service_class
from src.integrations.crawl4ai.crawler import crawl_deep, crawl_single_page

logger = logging.getLogger(__name__)


@log_service_class
class Crawl4AIClient:
    """Client for Crawl4AI web crawling service."""

    async def crawl_single_page(
        self,
        url: str,
        word_count_threshold: int = 10,
        remove_overlay_elements: bool = True,
        remove_base64_images: bool = True,
        cache_mode: str = "BYPASS",
        browser_type: str = "chromium",
        timeout: int = 30,
        cookies: str | dict[str, str] | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any] | None:
        """Crawl a single web page and extract content."""
        _ = browser_type
        _ = timeout
        _ = user_agent

        async with AsyncWebCrawler() as crawler:
            return await crawl_single_page(
                crawler=crawler,
                url=url,
                word_count_threshold=word_count_threshold,
                remove_overlay_elements=remove_overlay_elements,
                remove_base64_images=remove_base64_images,
                cache_mode=cache_mode,
                cookies=cookies,
                user_agent=user_agent,
            )

    async def crawl_deep(
        self,
        start_url: str,
        max_depth: int = 2,
        allowed_domains: list[str] | None = None,
        allowed_subdomains: list[str] | None = None,
        exclude_external_links: bool = False,
        remove_overlay_elements: bool = True,
        remove_base64_images: bool = True,
        word_count_threshold: int = 10,
        cache_mode: str = "BYPASS",
        browser_type: str = "chromium",
        timeout: int = 30,
        cookies: str | dict[str, str] | None = None,
        user_agent: str | None = None,
        visited_urls: set[str] | None = None,
        current_depth: int = 0,
    ) -> list[dict[str, Any]]:
        """Perform a deep crawl of a website."""
        _ = browser_type
        _ = timeout
        _ = user_agent
        _ = visited_urls
        _ = current_depth

        async with AsyncWebCrawler() as crawler:
            results = await crawl_deep(
                crawler=crawler,
                start_url=start_url,
                max_depth=max_depth,
                allowed_domains=allowed_domains,
                allowed_subdomains=allowed_subdomains,
                max_concurrent=10,
                cookies=cookies,
                word_count_threshold=word_count_threshold,
                remove_overlay_elements=remove_overlay_elements,
                remove_base64_images=remove_base64_images,
                cache_mode=cache_mode,
            )

        if exclude_external_links:
            filtered: list[dict[str, Any]] = []
            for page in results:
                links = page.get("links", [])
                filtered.append({
                    **page,
                    "links": [link for link in links if link.startswith(start_url)],
                })
            return filtered

        return results
