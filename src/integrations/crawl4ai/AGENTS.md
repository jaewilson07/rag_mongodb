# Crawl4AI Integration (src/integrations/crawl4ai) - Agent Guide

## Purpose

Headless browser web crawling with Playwright. Supports single-page extraction and recursive deep crawling with domain scoping.

## Architecture

```mermaid
classDiagram
    class Crawl4AIClient {
        +crawl_single_page(url, ...) Source
        +crawl_deep(start_url, max_depth, ...) list~Source~
    }

    class crawl_single_page {
        <<function>>
        +url: str
        +cookies: str|dict
        +headers: dict
        +word_count_threshold: int
        returns Source|None
    }

    class crawl_deep {
        <<function>>
        +start_url: str
        +max_depth: int
        +allowed_domains: list
        +max_concurrent: int
        returns list~Source~
    }

    class CrawlerRunConfig {
        +word_count_threshold: int
        +remove_overlay_elements: bool
        +cache_mode: CacheMode
        +cookies: list
        +headers: dict
    }

    Crawl4AIClient --> crawl_single_page : delegates to
    Crawl4AIClient --> crawl_deep : delegates to
    crawl_single_page --> CrawlerRunConfig : builds
    crawl_deep --> crawl_single_page : calls per page
```

## Deep Crawl Flow

```mermaid
flowchart TD
    START[start_url] --> CRAWL[crawl page]
    CRAWL --> CHECK{depth < max_depth?}
    CHECK -->|yes| LINKS[extract links]
    LINKS --> FILTER[filter by allowed_domains]
    FILTER --> VISITED{already visited?}
    VISITED -->|no| CRAWL
    VISITED -->|yes| SKIP[skip]
    CHECK -->|no| DONE[return results]
    SKIP --> DONE
```

## Durable Lessons

1. **Managed crawler context.** `_with_crawler()` ensures `AsyncWebCrawler` is properly entered/exited. If a caller provides one, it's reused; otherwise a temporary one is created. This prevents resource leaks.

2. **Cookie authentication.** `_parse_cookies()` converts `"name=value; name2=value2"` strings into Playwright-compatible cookie dicts with domain prefixed by `.` for subdomain matching.

3. **Domain scoping is automatic.** `crawl_deep` defaults `allowed_domains` to the start URL's domain. External links are filtered out unless explicitly allowed.

4. **Concurrency semaphore.** Deep crawl uses `asyncio.Semaphore(max_concurrent)` to cap parallel browser tabs. Default is 10.

5. **httpx fallback for non-JS pages.** When Playwright fails, `crawl_single_page` falls back to a simple httpx GET + BeautifulSoup parse. This handles CDN-served docs and static sites where a full browser is unnecessary.
