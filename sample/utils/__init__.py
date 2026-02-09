"""Sample script utilities for pre-flight checks and common functions."""

from __future__ import annotations

import subprocess
from typing import Any

import httpx
from mdrag.settings import Settings
from pymongo import AsyncMongoClient
from redis.asyncio import Redis


async def check_mongodb(settings: Settings) -> dict[str, Any]:
    """
    Check MongoDB connection and verify required indexes exist.

    Args:
        settings: Application settings with MongoDB configuration

    Returns:
        Dictionary with status, message, and optional details
    """
    try:
        client = AsyncMongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=5000,
        )
        await client.admin.command("ping")

        db = client[settings.mongodb_database]

        # Check collections exist
        collections = await db.list_collection_names()
        has_docs = settings.mongodb_collection_documents in collections
        has_chunks = settings.mongodb_collection_chunks in collections

        # Check indexes if collections exist
        indexes_ok = True
        missing_indexes = []

        if has_chunks:
            chunks = db[settings.mongodb_collection_chunks]
            chunk_indexes = await chunks.list_indexes().to_list(length=None)
            index_names = [idx.get("name") for idx in chunk_indexes]

            if settings.mongodb_vector_index not in index_names:
                missing_indexes.append(
                    f"Vector index '{settings.mongodb_vector_index}'"
                )
                indexes_ok = False

            if settings.mongodb_text_index not in index_names:
                missing_indexes.append(f"Text index '{settings.mongodb_text_index}'")
                indexes_ok = False

        await client.close()

        if not has_docs or not has_chunks:
            return {
                "status": "warning",
                "message": "MongoDB connected but collections are empty",
                "details": {
                    "has_documents": has_docs,
                    "has_chunks": has_chunks,
                },
            }

        if not indexes_ok:
            return {
                "status": "error",
                "message": "MongoDB connected but required indexes are missing",
                "details": {
                    "missing_indexes": missing_indexes,
                },
            }

        return {
            "status": "ok",
            "message": "MongoDB connection successful",
            "details": {
                "database": settings.mongodb_database,
                "has_documents": has_docs,
                "has_chunks": has_chunks,
                "indexes_ok": indexes_ok,
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"MongoDB connection failed: {e}",
            "details": {"error": str(e)},
        }


async def check_redis(redis_url: str) -> dict[str, Any]:
    """
    Check Redis connection.

    Args:
        redis_url: Redis connection URL

    Returns:
        Dictionary with status and message
    """
    try:
        redis = Redis.from_url(redis_url, socket_connect_timeout=5)
        await redis.ping()
        await redis.aclose()

        return {
            "status": "ok",
            "message": "Redis connection successful",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Redis connection failed: {e}",
            "details": {"error": str(e)},
        }


async def check_searxng(searxng_url: str) -> dict[str, Any]:
    """
    Check SearXNG availability.

    Args:
        searxng_url: SearXNG base URL

    Returns:
        Dictionary with status and message
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{searxng_url.rstrip('/')}/search",
                params={"q": "test", "format": "json"},
            )
            response.raise_for_status()

        return {
            "status": "ok",
            "message": "SearXNG connection successful",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"SearXNG connection failed: {e}",
            "details": {"error": str(e)},
        }


def check_playwright() -> dict[str, Any]:
    """
    Check if Playwright runtime is installed.

    Returns:
        Dictionary with status and message
    """
    try:
        result = subprocess.run(
            ["playwright", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            return {
                "status": "ok",
                "message": f"Playwright installed: {result.stdout.strip()}",
            }
        else:
            return {
                "status": "error",
                "message": "Playwright command failed",
                "details": {"stderr": result.stderr},
            }

    except FileNotFoundError:
        return {
            "status": "error",
            "message": "Playwright not installed",
            "details": {"help": "Run: playwright install"},
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Playwright check failed: {e}",
            "details": {"error": str(e)},
        }


def check_google_credentials(settings: Settings) -> dict[str, Any]:
    """
    Check if Google Drive credentials are configured.

    Args:
        settings: Application settings

    Returns:
        Dictionary with status and message
    """
    from pathlib import Path

    # Check for service account file
    service_account_path = getattr(settings, "google_service_account_file", None)
    if service_account_path:
        sa_path = Path(service_account_path)
        if sa_path.exists():
            return {
                "status": "ok",
                "message": "Google service account file found",
                "details": {"auth_method": "service_account"},
            }
        else:
            return {
                "status": "error",
                "message": f"Google service account file not found: {service_account_path}",
                "details": {"auth_method": "service_account"},
            }

    # Check for OAuth tokens
    gdoc_client = getattr(settings, "gdoc_client", None)
    gdoc_token = getattr(settings, "gdoc_token", None)

    if gdoc_client and gdoc_token:
        return {
            "status": "ok",
            "message": "Google OAuth tokens configured",
            "details": {"auth_method": "oauth"},
        }

    return {
        "status": "error",
        "message": "Google Drive credentials not configured",
        "details": {
            "help": "Set either GOOGLE_SERVICE_ACCOUNT_FILE or GDOC_CLIENT/GDOC_TOKEN in .env",
        },
    }


def check_api_keys(
    settings: Settings, require_llm: bool = True, require_embedding: bool = True
) -> dict[str, Any]:
    """
    Check if LLM and embedding API keys are configured.

    Args:
        settings: Application settings
        require_llm: Whether LLM API key is required
        require_embedding: Whether embedding API key is required

    Returns:
        Dictionary with status and message
    """
    missing = []

    if require_llm:
        llm_api_key = getattr(settings, "llm_api_key", None)
        if not llm_api_key:
            missing.append("LLM_API_KEY")

    if require_embedding:
        embedding_api_key = getattr(settings, "embedding_api_key", None)
        if not embedding_api_key:
            missing.append("EMBEDDING_API_KEY")

    if missing:
        return {
            "status": "error",
            "message": f"Missing API keys: {', '.join(missing)}",
            "details": {"missing_keys": missing},
        }

    return {
        "status": "ok",
        "message": "API keys configured",
    }


def print_service_error(
    service: str, result: dict[str, Any], instructions: str | None = None
) -> None:
    """
    Print consistent error message for service check failures.

    Args:
        service: Service name (e.g., "MongoDB", "Redis")
        result: Result dictionary from check function
        instructions: Optional setup instructions
    """
    print(f"❌ {service} check failed")
    print(f"   Message: {result['message']}")

    if "details" in result:
        details = result["details"]
        if "error" in details:
            print(f"   Error: {details['error']}")
        if "help" in details:
            print(f"   Help: {details['help']}")
        if "missing_indexes" in details:
            print(f"   Missing indexes: {', '.join(details['missing_indexes'])}")

    if instructions:
        print("\n   Setup instructions:")
        for line in instructions.split("\n"):
            if line.strip():
                print(f"   {line}")

    print()


def print_pre_flight_results(checks: dict[str, dict[str, Any]]) -> bool:
    """
    Print summary of pre-flight check results.

    Args:
        checks: Dictionary mapping service name to check result

    Returns:
        True if all checks passed, False otherwise
    """
    print("\n" + "=" * 60)
    print("PRE-FLIGHT CHECKS")
    print("=" * 60)

    all_passed = True

    for service, result in checks.items():
        status = result["status"]
        symbol = "✓" if status == "ok" else "⚠" if status == "warning" else "❌"
        print(f"{symbol} {service}: {result['message']}")

        if status in ["error", "warning"]:
            all_passed = False

    print("=" * 60)

    if not all_passed:
        print("\nSome checks failed. Please resolve issues before running this sample.")
        print()

    return all_passed
