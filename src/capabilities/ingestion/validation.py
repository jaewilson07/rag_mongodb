"""Pipeline-attached validation for ingestion and readings."""

from __future__ import annotations

from mdrag.settings import Settings
from mdrag.validation import (
    validate_embedding_api,
    validate_google_credentials,
    validate_llm_api,
    validate_mongodb,
    validate_playwright,
    validate_redis,
    validate_rq_workers,
    validate_searxng,
    validate_youtube_deps,
)

# Core checks always run for ingestion
INGESTION_CORE_CHECKS = ["mongodb", "embedding"]

# Collector-specific checks (run only when that collector is used)
COLLECTOR_CHECKS: dict[str, list[str]] = {
    "crawl4ai": ["playwright"],
    "gdrive": ["google_credentials"],
    "upload": [],
}

# Readings-specific checks by URL type
READINGS_CHECKS: dict[str, list[str]] = {
    "web": ["playwright", "searxng"],
    "youtube": ["youtube_deps"],
}


async def validate_ingestion(
    settings: Settings,
    *,
    collectors: list[str],
    strict_mongodb: bool = False,
    require_redis: bool = True,
) -> None:
    """
    Run core and collector-specific validation for the ingestion pipeline.

    Args:
        settings: Application settings.
        collectors: List of collector names (e.g. ["crawl4ai"], ["gdrive"]).
        strict_mongodb: If True, require collections and indexes. If False, connection only.
        require_redis: If True, validate Redis connection (required for queue).

    Raises:
        ValidationError: On first validation failure.
    """
    # Core: MongoDB
    await validate_mongodb(settings, strict=strict_mongodb)

    # Core: Redis + RQ workers (when queue is used)
    if require_redis:
        redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
        validate_redis(redis_url)
        validate_rq_workers(redis_url, queue_name="default")

    # Core: Embedding API
    await validate_embedding_api(settings)

    # Collector-specific
    for name in collectors:
        checks = COLLECTOR_CHECKS.get(name, [])
        for check in checks:
            if check == "playwright":
                validate_playwright()
            elif check == "google_credentials":
                validate_google_credentials(settings)
            # upload has no extra checks


async def validate_readings(
    settings: Settings,
    url_type: str,
    *,
    searxng_url: str | None = None,
) -> None:
    """
    Run validation for ReadingsService (save_reading flow).

    Args:
        settings: Application settings.
        url_type: "web" or "youtube".
        searxng_url: SearXNG URL for related-link search. If None, skips SearXNG check.

    Raises:
        ValidationError: On first validation failure.
    """
    # Core: MongoDB
    await validate_mongodb(settings, strict=False)

    # Core: Redis + RQ workers (queue for ingestion)
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    validate_redis(redis_url)
    validate_rq_workers(redis_url, queue_name="default")

    # Core: LLM API (for summary generation)
    validate_llm_api(settings)

    # URL-type-specific
    checks = READINGS_CHECKS.get(url_type, [])
    for check in checks:
        if check == "playwright":
            validate_playwright()
        elif check == "youtube_deps":
            validate_youtube_deps()
        elif check == "searxng" and searxng_url:
            validate_searxng(searxng_url)
