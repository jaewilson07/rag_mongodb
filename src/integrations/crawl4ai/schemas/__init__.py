"""Pydantic models for Crawl4AI service."""

from typing import Any

from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    """Request to crawl a single page."""

    url: str = Field(..., description="URL to crawl")
    word_count_threshold: int = Field(10, ge=1, description="Minimum word count for content blocks")
    remove_overlay_elements: bool = Field(True, description="Remove overlay elements")
    remove_base64_images: bool = Field(True, description="Remove base64 encoded images")
    cache_mode: str = Field("BYPASS", description="Cache mode (BYPASS, CACHED, or WRITE)")
    browser_type: str = Field("chromium", description="Browser type (chromium or firefox)")
    timeout: int = Field(30, ge=5, le=300, description="Request timeout in seconds")
    cookies: str | dict[str, str] | None = Field(None, description="Optional cookies")
    user_agent: str | None = Field(None, description="Optional custom user agent")


class DeepCrawlRequest(BaseModel):
    """Request to perform a deep crawl of a website."""

    start_url: str = Field(..., description="Starting URL for the crawl")
    max_depth: int = Field(2, ge=1, le=10, description="Maximum crawl depth")
    allowed_domains: list[str] | None = Field(
        None, description="Allowed domains (None = same domain as start_url)"
    )
    allowed_subdomains: list[str] | None = Field(None, description="Allowed subdomains")
    exclude_external_links: bool = Field(False, description="Exclude external links")
    remove_overlay_elements: bool = Field(True, description="Remove overlay elements")
    remove_base64_images: bool = Field(True, description="Remove base64 encoded images")
    word_count_threshold: int = Field(10, ge=1, description="Minimum word count for content blocks")
    cache_mode: str = Field("BYPASS", description="Cache mode")
    browser_type: str = Field("chromium", description="Browser type")
    timeout: int = Field(30, ge=5, le=300, description="Request timeout in seconds")
    cookies: str | dict[str, str] | None = Field(None, description="Optional cookies")
    user_agent: str | None = Field(None, description="Optional custom user agent")


class CrawlResult(BaseModel):
    """Result of a crawl operation."""

    url: str = Field(..., description="The crawled URL")
    content: str = Field(..., description="Extracted content")
    markdown: str = Field(..., description="Content as markdown")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Crawl metadata")
    links: list[str] = Field(default_factory=list, description="Links found on the page")


class DeepCrawlResult(BaseModel):
    """Result of a deep crawl operation."""

    start_url: str = Field(..., description="The starting URL")
    total_pages: int = Field(..., description="Total pages crawled")
    pages: list[CrawlResult] = Field(default_factory=list, description="Results for each page")
    summary: dict[str, Any] = Field(default_factory=dict, description="Crawl summary")
