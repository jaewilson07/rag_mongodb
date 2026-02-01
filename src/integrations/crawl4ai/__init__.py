"""Crawl4AI web crawling service."""

from .client import Crawl4AIClient
from .crawler import crawl_deep, crawl_single_page
from .schemas import CrawlRequest, CrawlResult, DeepCrawlRequest, DeepCrawlResult

__all__ = [
    # Client
    "Crawl4AIClient",
    # Schemas
    "CrawlRequest",
    "CrawlResult",
    "DeepCrawlRequest",
    "DeepCrawlResult",
    # Crawler functions (for backward compatibility with workflow)
    "crawl_deep",
    "crawl_single_page",
]
