"""Crawl4AI web crawling integration."""

from src.integrations.crawl4ai.client import Crawl4AIClient
from src.integrations.crawl4ai.crawler import crawl_deep, crawl_single_page
from src.integrations.crawl4ai.schemas import (
    CrawlRequest,
    CrawlResult,
    DeepCrawlRequest,
    DeepCrawlResult,
)

__all__ = [
    "Crawl4AIClient",
    "CrawlRequest",
    "CrawlResult",
    "DeepCrawlRequest",
    "DeepCrawlResult",
    "crawl_deep",
    "crawl_single_page",
]
