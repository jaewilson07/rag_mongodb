"""Core crawler functions for Crawl4AI web crawling operations.

This module provides the actual crawling implementation using Crawl4AI,
supporting both single-page and deep crawling with authentication support.
"""

# ruff: noqa: I001

import asyncio
from datetime import datetime
from collections.abc import Awaitable, Callable
from typing import Any, cast
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from ...mdrag_logging.service_logging import get_logger, log_service
from ..models import Source, SourceFrontmatter

logger = get_logger(__name__)


def _attach_frontmatter(result: dict[str, Any]) -> Source:
    metadata = result.get("metadata", {}) or {}
    fetched_at = metadata.get("crawl_timestamp") or datetime.now().isoformat()

    frontmatter = SourceFrontmatter(
        source_type="web",
        source_url=result.get("url") or "",
        source_title=metadata.get("page_title"),
        source_mime_type=metadata.get("mime_type"),
        source_modified_at=metadata.get("last_modified") or metadata.get("modified"),
        source_fetched_at=fetched_at,
        source_etag=metadata.get("etag"),
    )

    raw_links = result.get("links") or []
    links: list[str] = []
    for link in raw_links:
        if isinstance(link, str):
            links.append(link)
            continue
        if isinstance(link, dict):
            href = link.get("href") or link.get("url")
            if isinstance(href, str):
                links.append(href)

    return Source(
        frontmatter=frontmatter,
        content=result.get("markdown") or "",
        html=result.get("html"),
        metadata=metadata,
        links=links,
    )


def _parse_cookies(cookies: str | dict[str, str] | None, url: str) -> list[dict[str, Any]] | None:
    """
    Parse cookies from string or dict format into Playwright cookie format.

    Args:
        cookies: Cookies as string (e.g., "sessionid=abc123; csrftoken=xyz")
                 or dict (e.g., {"sessionid": "abc123", "csrftoken": "xyz"})
        url: URL to extract domain for cookie assignment

    Returns:
        List of Playwright-compatible cookie dicts, or None if no cookies
    """
    if not cookies:
        return None

    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Remove www. prefix for broader cookie scope
    if domain.startswith("www."):
        domain = domain[4:]

    cookie_list = []

    if isinstance(cookies, str):
        # Parse string format: "name1=value1; name2=value2"
        for cookie_part in cookies.split(";"):
            cookie_value = cookie_part.strip()
            if "=" in cookie_value:
                name, value = cookie_value.split("=", 1)
                cookie_list.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": f".{domain}",  # Prefix with . for subdomain matching
                        "path": "/",
                    }
                )
    elif isinstance(cookies, dict):
        # Parse dict format
        for name, value in cookies.items():
            cookie_list.append(
                {
                    "name": name,
                    "value": value,
                    "domain": f".{domain}",
                    "path": "/",
                }
            )

    return cookie_list if cookie_list else None


def _build_crawler_config(
    url: str,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    user_agent: str | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    cache_mode: str = "BYPASS",
    wait_for: str | None = None,
    wait_until: str | None = None,
    wait_for_timeout: int | None = None,
    page_timeout: int | None = None,
    css_selector: str | None = None,
) -> tuple[CrawlerRunConfig, dict[str, int]]:
    """
    Build a CrawlerRunConfig with authentication support.

    Args:
        url: URL being crawled (used for cookie domain)
        cookies: Optional cookies for authentication
        headers: Optional HTTP headers for authentication
        word_count_threshold: Minimum word count for content blocks
        remove_overlay_elements: Whether to remove overlay elements
        cache_mode: Cache mode string (BYPASS, CACHED, or WRITE)

    Returns:
        Configured CrawlerRunConfig instance
    """
    # Parse cache mode
    cache_mode_enum = CacheMode.BYPASS
    if cache_mode.upper() == "CACHED":
        cache_mode_enum = CacheMode.READ_ONLY
    elif cache_mode.upper() == "WRITE":
        cache_mode_enum = CacheMode.WRITE_ONLY

    config_kwargs = {
        "word_count_threshold": word_count_threshold,
        "remove_overlay_elements": remove_overlay_elements,
        "cache_mode": cache_mode_enum,
    }

    if wait_for:
        config_kwargs["wait_for"] = wait_for
    if wait_until:
        config_kwargs["wait_until"] = wait_until
    if wait_for_timeout is not None:
        config_kwargs["wait_for_timeout"] = wait_for_timeout
    if page_timeout is not None:
        config_kwargs["page_timeout"] = page_timeout
    if css_selector:
        config_kwargs["css_selector"] = css_selector

    if user_agent:
        headers = {**(headers or {}), "User-Agent": user_agent}

    # Add cookies if provided
    parsed_cookies = _parse_cookies(cookies, url)
    if parsed_cookies:
        config_kwargs["cookies"] = parsed_cookies

    # Add headers if provided
    if headers:
        config_kwargs["headers"] = headers

    metadata = {
        "cookie_count": len(parsed_cookies) if parsed_cookies else 0,
        "header_count": len(headers) if headers else 0,
    }

    return CrawlerRunConfig(**config_kwargs), metadata


async def _with_crawler(
    crawler: AsyncWebCrawler | None,
    action: Callable[[AsyncWebCrawler], Awaitable[Any]],
) -> Any:
    if crawler is not None:
        return await action(crawler)

    async with AsyncWebCrawler() as managed_crawler:
        return await action(managed_crawler)


@log_service()
async def crawl_single_page(
    url: str,
    crawler: AsyncWebCrawler | None = None,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    http_client: Any | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    browser_type: str | None = None,
    timeout: int | None = None,
    user_agent: str | None = None,
    wait_for: str | None = None,
    wait_until: str | None = None,
    wait_for_timeout: int | None = None,
    page_timeout: int | None = None,
    css_selector: str | None = None,
    allow_fallback: bool = True,
    **kwargs,  # Accept additional kwargs for forward compatibility
) -> Source | None:
    """
    Crawl a single web page and extract content.

    Args:
        crawler: AsyncWebCrawler instance (must be entered via __aenter__)
        url: The URL to crawl
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        word_count_threshold: Minimum word count for a block to be included
        remove_overlay_elements: Remove overlay elements from the page
        remove_base64_images: Remove base64 encoded images
        cache_mode: Cache mode for crawling (BYPASS, CACHED, or WRITE)

    Returns:
        Source payload with markdown, metadata, and frontmatter, or None if failed.
    """
    async def _run(active_crawler: AsyncWebCrawler) -> Source | None:
        _ = (remove_base64_images, browser_type, timeout, kwargs)

        async def _httpx_fallback() -> Source | None:
            if not http_client:
                return None

            try:
                response = await http_client.get(url, follow_redirects=True)
                response.raise_for_status()
                html = response.text
                title = ""

                try:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(html, "html.parser")
                    title_tag = soup.find("title")
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                except Exception:
                    title = ""

                await logger.info(
                    "crawl_single_page_fallback_complete",
                    url=url,
                    status_code=response.status_code,
                    action="crawl_single_page_fallback_complete",
                )

                return _attach_frontmatter(
                    {
                        "url": str(response.url),
                        "markdown": "",
                        "html": html,
                        "metadata": {
                            "page_title": title,
                            "status_code": response.status_code,
                        },
                        "links": [],
                    }
                )
            except Exception as fallback_error:
                await logger.warning(
                    "crawl_single_page_fallback_failed",
                    url=url,
                    error=str(fallback_error),
                    error_type=type(fallback_error).__name__,
                    action="crawl_single_page_fallback_failed",
                )
                return None
        try:
            config, config_meta = _build_crawler_config(
                url=url,
                cookies=cookies,
                headers=headers,
                user_agent=user_agent,
                word_count_threshold=word_count_threshold,
                remove_overlay_elements=remove_overlay_elements,
                cache_mode=cache_mode,
                wait_for=wait_for,
                wait_until=wait_until,
                wait_for_timeout=wait_for_timeout,
                page_timeout=page_timeout,
                css_selector=css_selector,
            )

            await logger.info("crawl_single_page_start", url=url, action="crawl_single_page_start")
            if config_meta["cookie_count"]:
                await logger.debug(
                    "crawl_single_page_cookies_configured",
                    url=url,
                    cookie_count=config_meta["cookie_count"],
                    action="crawl_single_page_cookies_configured",
                )
            if config_meta["header_count"]:
                await logger.debug(
                    "crawl_single_page_headers_configured",
                    url=url,
                    header_count=config_meta["header_count"],
                    action="crawl_single_page_headers_configured",
                )

            result = cast(Any, await active_crawler.arun(url=url, config=config))

            if not result.success:
                await logger.warning(
                    "crawl_single_page_failed",
                    url=url,
                    error=result.error_message,
                    action="crawl_single_page_failed",
                )
                if allow_fallback:
                    fallback_result = await _httpx_fallback()
                    if fallback_result:
                        return fallback_result
                return None

            # Extract metadata from the result
            metadata = {
                "page_title": getattr(result, "title", None),
                "status_code": getattr(result, "status_code", None),
                "crawl_timestamp": getattr(result, "crawl_timestamp", None),
            }

            # Add any additional metadata from result.metadata if available
            if hasattr(result, "metadata") and result.metadata:
                metadata.update(result.metadata)

            # Extract links if available
            links = []
            if hasattr(result, "links") and result.links:
                # Handle both internal and external links
                if isinstance(result.links, dict):
                    links = list(result.links.get("internal", [])) + list(
                        result.links.get("external", [])
                    )
                elif isinstance(result.links, list):
                    links = result.links

            return _attach_frontmatter(
                {
                    "url": result.url or url,
                    "markdown": result.markdown or "",
                    "html": result.html or "",
                    "metadata": metadata,
                    "links": links,
                }
            )

        except Exception as e:
            await logger.error(
                "crawl_single_page_error",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                action="crawl_single_page_error",
            )
            if allow_fallback:
                fallback_result = await _httpx_fallback()
                if fallback_result:
                    return fallback_result
            return None

    return await _with_crawler(crawler, _run)


@log_service()
async def crawl_deep(
    start_url: str,
    crawler: AsyncWebCrawler | None = None,
    max_depth: int = 2,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    exclude_external_links: bool = False,
    max_concurrent: int = 10,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    browser_type: str | None = None,
    timeout: int | None = None,
    user_agent: str | None = None,
    visited_urls: set[str] | None = None,
    current_depth: int = 0,
    **kwargs,  # Accept additional kwargs for forward compatibility
) -> list[Source]:
    """
    Perform a deep crawl of a website, recursively following links.

    Args:
        crawler: AsyncWebCrawler instance (must be entered via __aenter__)
        start_url: The starting URL for the crawl
        max_depth: Maximum recursion depth (1 = start page only, 2 = start + 1 level, etc.)
        allowed_domains: List of allowed domains for exact matching
        allowed_subdomains: List of allowed subdomain prefixes
        max_concurrent: Maximum concurrent crawler sessions
        cookies: Optional authentication cookies as string or dict
        headers: Optional custom HTTP headers as dict
        word_count_threshold: Minimum word count for a block to be included
        remove_overlay_elements: Remove overlay elements from the page
        remove_base64_images: Remove base64 encoded images
        cache_mode: Cache mode for crawling

    Returns:
        List of Source payloads for each crawled page.
    """
    max_depth = max(max_depth, 1)
    max_depth = min(max_depth, 10)
    _ = (remove_base64_images, browser_type, timeout, kwargs)

    # Parse starting URL for domain filtering
    parsed_start = urlparse(start_url)
    start_domain = parsed_start.netloc

    # Default allowed domains to starting domain if not provided
    if not allowed_domains:
        # Remove www. prefix for matching
        clean_domain = start_domain
        if clean_domain.startswith("www."):
            clean_domain = clean_domain[4:]
        allowed_domains = [clean_domain, f"www.{clean_domain}"]

    if exclude_external_links:
        allowed_domains = [start_domain.replace("www.", ""), f"www.{start_domain.replace('www.', '')}"]

    def _is_allowed_url(url: str) -> bool:
        """Check if a URL is allowed based on domain/subdomain filters."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            # Check allowed domains (exact match)
            domain_match = False
            for allowed in allowed_domains:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    domain_match = True
                    break

            if not domain_match:
                return False

            # Check allowed subdomains (prefix match)
            if allowed_subdomains:
                return any(domain.startswith(f"{subdomain}.") for subdomain in allowed_subdomains)

            return True

        except Exception:
            return False

    # Track visited URLs and results
    visited_urls = visited_urls or set()
    results: list[Source] = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _run(active_crawler: AsyncWebCrawler) -> list[Source]:
        async def _crawl_page(url: str, depth: int, parent_url: str | None = None) -> None:
            """Crawl a single page and queue its links for further crawling."""
            # Normalize URL (remove fragment, trailing slash)
            normalized_url = url.split("#")[0].rstrip("/")

            async with semaphore:
                # Skip if already visited
                if normalized_url in visited_urls:
                    return
                visited_urls.add(normalized_url)

                # Skip if not allowed
                if not _is_allowed_url(normalized_url):
                    await logger.debug(
                        "crawl_deep_url_disallowed",
                        url=normalized_url,
                        action="crawl_deep_url_disallowed",
                    )
                    return

                # Crawl the page
                result = await crawl_single_page(
                    crawler=active_crawler,
                    url=normalized_url,
                    cookies=cookies,
                    headers=headers,
                    word_count_threshold=word_count_threshold,
                    remove_overlay_elements=remove_overlay_elements,
                    remove_base64_images=remove_base64_images,
                    cache_mode=cache_mode,
                    user_agent=user_agent,
                )

                if not result:
                    await logger.warning(
                        "crawl_deep_page_failed",
                        url=normalized_url,
                        depth=depth,
                        action="crawl_deep_page_failed",
                    )
                    return

                # Add crawl metadata
                result.metadata["crawl_depth"] = depth
                result.metadata["parent_url"] = parent_url

                results.append(result)
                await logger.info(
                    "crawl_deep_page_complete",
                    url=normalized_url,
                    depth=depth,
                    total=len(results),
                    action="crawl_deep_page_complete",
                )

                # Follow links if not at max depth
                if depth < max_depth and result.links:
                    child_urls = [link for link in result.links if _is_allowed_url(link)]
                    if child_urls:
                        child_tasks = [
                            _crawl_page(child_url, depth + 1, normalized_url)
                            for child_url in child_urls[:50]  # Limit links per page
                        ]
                        await asyncio.gather(*child_tasks, return_exceptions=True)

        await logger.info(
            "crawl_deep_start",
            start_url=start_url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            action="crawl_deep_start",
        )

        start_depth = max(current_depth, 1)
        await _crawl_page(start_url, depth=start_depth)

        await logger.info(
            "crawl_deep_complete",
            start_url=start_url,
            total=len(results),
            action="crawl_deep_complete",
        )
        return results

    return await _with_crawler(crawler, _run)


__all__ = ["crawl_deep", "crawl_single_page"]
