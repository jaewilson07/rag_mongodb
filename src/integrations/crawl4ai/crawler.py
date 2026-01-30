"""Core crawler functions for Crawl4AI web crawling operations.

This module provides the actual crawling implementation using Crawl4AI,
supporting both single-page and deep crawling with authentication support.
"""

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

from src.logging_utils import log_service

logger = logging.getLogger(__name__)


def _parse_cookies(
    cookies: str | dict[str, str] | None,
    url: str,
) -> list[dict[str, Any]] | None:
    """Parse cookies into Playwright cookie format."""
    if not cookies:
        return None

    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Remove www. prefix for broader cookie scope
    if domain.startswith("www."):
        domain = domain[4:]

    cookie_list: list[dict[str, Any]] = []

    if isinstance(cookies, str):
        for cookie in cookies.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookie_list.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": f".{domain}",
                        "path": "/",
                    }
                )
    elif isinstance(cookies, dict):
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
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    cache_mode: str = "BYPASS",
) -> CrawlerRunConfig:
    """Build a CrawlerRunConfig with authentication support."""
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

    parsed_cookies = _parse_cookies(cookies, url)
    if parsed_cookies:
        config_kwargs["cookies"] = parsed_cookies
        logger.debug(
            "Added cookies for domain extraction",
            extra={"cookie_count": len(parsed_cookies), "url": url},
        )

    if headers:
        config_kwargs["headers"] = headers
        logger.debug(
            "Added custom headers",
            extra={"header_count": len(headers)},
        )

    return CrawlerRunConfig(**config_kwargs)


@log_service
async def crawl_single_page(
    crawler: AsyncWebCrawler,
    url: str,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    **kwargs,
) -> dict[str, Any] | None:
    """Crawl a single web page and extract content."""
    try:
        config = _build_crawler_config(
            url=url,
            cookies=cookies,
            headers=headers,
            word_count_threshold=word_count_threshold,
            remove_overlay_elements=remove_overlay_elements,
            cache_mode=cache_mode,
        )

        logger.info("Crawling single page", extra={"url": url})
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            logger.warning("Failed to crawl", extra={"url": url, "error": result.error_message})
            return None

        metadata = {
            "page_title": getattr(result, "title", None),
            "status_code": getattr(result, "status_code", None),
            "crawl_timestamp": getattr(result, "crawl_timestamp", None),
        }

        if hasattr(result, "metadata") and result.metadata:
            metadata.update(result.metadata)

        links: list[str] = []
        if hasattr(result, "links") and result.links:
            if isinstance(result.links, dict):
                links = list(result.links.get("internal", [])) + list(
                    result.links.get("external", [])
                )
            elif isinstance(result.links, list):
                links = result.links

        return {
            "url": result.url or url,
            "markdown": result.markdown or "",
            "html": result.html or "",
            "metadata": metadata,
            "links": links,
            "remove_base64_images": remove_base64_images,
        }

    except Exception as exc:
        logger.exception("Error crawling", extra={"url": url, "error": str(exc)})
        return None


@log_service
async def crawl_deep(
    crawler: AsyncWebCrawler,
    start_url: str,
    max_depth: int = 2,
    allowed_domains: list[str] | None = None,
    allowed_subdomains: list[str] | None = None,
    max_concurrent: int = 10,
    cookies: str | dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    word_count_threshold: int = 10,
    remove_overlay_elements: bool = True,
    remove_base64_images: bool = True,
    cache_mode: str = "BYPASS",
    **kwargs,
) -> list[dict[str, Any]]:
    """Perform a deep crawl of a website, recursively following links."""
    max_depth = max(max_depth, 1)
    max_depth = min(max_depth, 10)

    parsed_start = urlparse(start_url)
    start_domain = parsed_start.netloc

    if not allowed_domains:
        clean_domain = start_domain
        if clean_domain.startswith("www."):
            clean_domain = clean_domain[4:]
        allowed_domains = [clean_domain, f"www.{clean_domain}"]

    def _is_allowed_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc

            domain_match = False
            for allowed in allowed_domains or []:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    domain_match = True
                    break

            if not domain_match:
                return False

            if allowed_subdomains:
                for subdomain in allowed_subdomains:
                    if domain.startswith(f"{subdomain}."):
                        return True
                return False

            return True

        except Exception:
            return False

    visited_urls: set[str] = set()
    results: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _crawl_page(url: str, depth: int, parent_url: str | None = None) -> None:
        normalized_url = url.split("#")[0].rstrip("/")

        async with semaphore:
            if normalized_url in visited_urls:
                return
            visited_urls.add(normalized_url)

            if not _is_allowed_url(normalized_url):
                logger.debug("Skipping disallowed URL", extra={"url": normalized_url})
                return

            result = await crawl_single_page(
                crawler=crawler,
                url=normalized_url,
                cookies=cookies,
                headers=headers,
                word_count_threshold=word_count_threshold,
                remove_overlay_elements=remove_overlay_elements,
                remove_base64_images=remove_base64_images,
                cache_mode=cache_mode,
            )

            if not result:
                logger.warning(
                    "Failed to crawl",
                    extra={"url": normalized_url, "depth": depth},
                )
                return

            result["metadata"]["crawl_depth"] = depth
            result["metadata"]["parent_url"] = parent_url

            results.append(result)
            logger.info(
                "Crawled",
                extra={"url": normalized_url, "depth": depth, "total": len(results)},
            )

            if depth < max_depth and result.get("links"):
                child_urls = [link for link in result["links"] if _is_allowed_url(link)]
                if child_urls:
                    child_tasks = [
                        _crawl_page(child_url, depth + 1, normalized_url)
                        for child_url in child_urls[:50]
                    ]
                    await asyncio.gather(*child_tasks, return_exceptions=True)

    logger.info(
        "Starting deep crawl",
        extra={
            "start_url": start_url,
            "max_depth": max_depth,
            "allowed_domains": allowed_domains,
        },
    )

    await _crawl_page(start_url, depth=1)

    logger.info("Deep crawl complete", extra={"pages": len(results)})
    return results
