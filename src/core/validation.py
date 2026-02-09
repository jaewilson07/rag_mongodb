"""Startup validation for MongoDB connection, Redis, and schema."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from mdrag.config.settings import Settings
import redis
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from mdrag.core.exceptions import MDRAGException


class ValidationError(MDRAGException):
    """Raised when validation fails (connection, collections, indexes, etc.)."""

    pass


_SETUP_INSTRUCTIONS_CONNECTION = """
Setup instructions:
  1. Verify MONGODB_URI in .env
  2. For Atlas: check cluster is running and IP allowlisted
  3. For local: run 'docker compose up -d' and 'docker exec ... mongosh --eval "rs.initiate()"'
"""

_SETUP_INSTRUCTIONS_SCHEMA = """
Setup instructions:
  1. Run ingestion first: uv run python -m mdrag.ingestion.ingest -d ./documents
  2. Create vector and text indexes in Atlas UI (see README)
  3. For local MongoDB: ensure replica set is initialized (rs.initiate())
"""


async def validate_mongodb(settings: Settings, *, strict: bool = True) -> None:
    """
    Validate MongoDB connection and required collections/indexes.

    Args:
        settings: Application settings with MongoDB configuration.
        strict: If True, require collections and indexes to exist (for query/CLI/server).
                If False, only require connection (for ingestion before first run).

    Raises:
        ValidationError: If connection fails, or (when strict) if collections/indexes
            are missing. Includes detailed message and setup instructions.
    """
    client = AsyncMongoClient(
        settings.mongodb_connection_string,
        serverSelectionTimeoutMS=5000,
    )
    try:
        # Connection check
        try:
            await client.admin.command("ping")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            err_msg = str(e)
            code = getattr(e, "code", None)
            code_str = f" (code {code})" if code else ""
            raise ValidationError(
                f"MongoDB validation failed\n"
                f"  Connection: FAILED\n"
                f"  Error: {err_msg}{code_str}\n"
                f"{_SETUP_INSTRUCTIONS_CONNECTION}"
            ) from e
        except Exception as e:
            err_msg = str(e)
            code = getattr(e, "code", None)
            code_str = f" (code {code})" if code else ""
            raise ValidationError(
                f"MongoDB validation failed\n"
                f"  Connection: FAILED\n"
                f"  Error: {err_msg}{code_str}\n"
                f"{_SETUP_INSTRUCTIONS_CONNECTION}"
            ) from e

        if not strict:
            # Ingestion mode: connection OK is sufficient
            return

        db = client[settings.mongodb_database]
        try:
            collections = await db.list_collection_names()
        except Exception as e:
            err_msg = str(e)
            code = getattr(e, "code", None)
            code_str = f" (code {code})" if code else ""
            raise ValidationError(
                f"MongoDB validation failed\n"
                f"  Connection: OK\n"
                f"  Collections: FAILED to list ({err_msg}{code_str})\n"
                f"{_SETUP_INSTRUCTIONS_CONNECTION}"
            ) from e
        has_docs = settings.mongodb_collection_documents in collections
        has_chunks = settings.mongodb_collection_chunks in collections

        # Strict mode: require collections
        if not has_docs or not has_chunks:
            docs_status = "OK" if has_docs else "MISSING"
            chunks_status = "OK" if has_chunks else "MISSING"
            raise ValidationError(
                f"MongoDB validation failed\n"
                f"  Connection: OK\n"
                f"  Collections: documents={docs_status}, chunks={chunks_status}\n"
                f"{_SETUP_INSTRUCTIONS_SCHEMA}"
            )

        # Strict mode: require Atlas Search indexes on chunks (vector, text)
        chunks = db[settings.mongodb_collection_chunks]
        search_index_names: list[str] = []
        try:
            agg_cursor = await chunks.aggregate([{"$listSearchIndexes": {}}])
            search_indexes = await agg_cursor.to_list(length=None)
            search_index_names = [
                idx.get("name") for idx in search_indexes if idx.get("name")
            ]
        except Exception:
            pass
        index_names = search_index_names

        missing = []
        if settings.mongodb_vector_index not in index_names:
            missing.append(settings.mongodb_vector_index)
        if settings.mongodb_text_index not in index_names:
            missing.append(settings.mongodb_text_index)

        if missing:
            raise ValidationError(
                f"MongoDB validation failed\n"
                f"  Connection: OK\n"
                f"  Collections: documents=OK, chunks=OK\n"
                f"  Indexes: missing {', '.join(missing)}\n"
                f"{_SETUP_INSTRUCTIONS_SCHEMA}"
            )
    finally:
        await client.close()


def validate_redis(redis_url: str) -> None:
    """
    Validate Redis connection.
    Required for ingestion job queue (crawl_and_save, API ingest endpoints).

    Args:
        redis_url: Redis connection URL (e.g. redis://localhost:6379/0).

    Raises:
        ValidationError: If connection fails.
    """
    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        client.ping()
        client.close()
    except Exception as e:
        raise ValidationError(
            f"Redis validation failed\n"
            f"  Connection: FAILED\n"
            f"  Error: {e}\n"
            f"  Setup: Run 'docker compose up -d redis' or ensure Redis is running\n"
            f"  URL: {redis_url}"
        ) from e


def validate_rq_workers(redis_url: str, queue_name: str = "default") -> None:
    """
    Validate that at least one RQ worker is listening to the ingestion queue.

    Required for queue-based ingestion flows (crawl_and_save, ReadingsService,
    API ingest endpoints). Jobs enqueued without workers will never be processed.

    Args:
        redis_url: Redis connection URL (e.g. redis://localhost:6379/0).
        queue_name: RQ queue name to check (default: "default").

    Raises:
        ValidationError: If no workers are listening to the queue.
    """
    try:
        from rq import Queue
        from rq.worker import Worker

        conn = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        queue = Queue(queue_name, connection=conn)
        count = Worker.count(queue=queue)
        conn.close()
        if count < 1:
            raise ValidationError(
                f"RQ worker validation failed\n"
                f"  Workers listening to '{queue_name}': 0\n"
                f"  Setup: Start an ingestion worker in a separate terminal:\n"
                f"    uv run rq worker {queue_name} --url {redis_url}\n"
                f"  Jobs will queue but never process until a worker is running."
            )
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            f"RQ worker validation failed\n"
            f"  Error: {e}\n"
            f"  Setup: Ensure Redis is running, then start a worker:\n"
            f"    uv run rq worker {queue_name} --url {redis_url}"
        ) from e


async def validate_embedding_api(settings: Settings) -> None:
    """
    Validate embedding API connectivity with a minimal test request.

    Args:
        settings: Application settings with embedding configuration.

    Raises:
        ValidationError: If embedding API is unreachable or returns an error.
    """
    from mdrag.capabilities.retrieval.embeddings import EmbeddingClient

    try:
        client = EmbeddingClient(settings=settings)
        await client.initialize()
        await client.embed_text("test")
        await client.close()
    except Exception as e:
        raise ValidationError(
            f"Embedding API validation failed\n"
            f"  Connection: FAILED\n"
            f"  Error: {e}\n"
            f"  Setup: Verify EMBEDDING_API_KEY and EMBEDDING_BASE_URL in .env"
        ) from e


def validate_playwright() -> None:
    """
    Validate Playwright runtime is installed.

    Raises:
        ValidationError: If playwright command fails or is not found.
    """
    try:
        result = subprocess.run(
            ["playwright", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise ValidationError(
                "Playwright validation failed\n"
                "  Reason: Playwright command failed\n"
                "  Setup: Run 'playwright install'"
            )
    except FileNotFoundError:
        raise ValidationError(
            "Playwright validation failed\n"
            "  Reason: Playwright not installed\n"
            "  Setup: Run 'playwright install'"
        )
    except Exception as e:
        raise ValidationError(
            f"Playwright validation failed\n"
            f"  Reason: {e}\n"
            f"  Setup: Run 'playwright install'"
        ) from e


def validate_google_credentials(settings: Settings) -> None:
    """
    Validate Google Drive credentials are configured (service account or OAuth).

    Args:
        settings: Application settings.

    Raises:
        ValidationError: If no valid credentials are found.
    """
    import os

    sa_path = getattr(settings, "google_service_account_file", None)
    if sa_path:
        path = Path(sa_path)
        if path.exists():
            return
        raise ValidationError(
            f"Google Drive validation failed\n"
            f"  Reason: Service account file not found: {sa_path}\n"
            f"  Setup: Set GOOGLE_SERVICE_ACCOUNT_FILE to a valid JSON key path"
        )

    gdoc_client = getattr(settings, "gdoc_client", None) or os.getenv("GDOC_CLIENT")
    gdoc_token = getattr(settings, "gdoc_token", None) or os.getenv("GDOC_TOKEN")
    if gdoc_client and gdoc_token:
        return

    raise ValidationError(
        "Google Drive validation failed\n"
        "  Reason: No credentials configured\n"
        "  Setup: Set GOOGLE_SERVICE_ACCOUNT_FILE or GDOC_CLIENT/GDOC_TOKEN in .env"
    )


def validate_youtube_deps() -> None:
    """
    Validate YouTube extraction dependencies (yt-dlp, youtube-transcript-api).

    Raises:
        ValidationError: If required packages are not installed.
    """
    try:
        import yt_dlp  # noqa: F401
    except ImportError as e:
        raise ValidationError(
            f"YouTube dependencies validation failed\n"
            f"  Reason: {e}\n"
            f"  Setup: pip install yt-dlp youtube-transcript-api"
        ) from e

    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
    except ImportError as e:
        raise ValidationError(
            f"YouTube dependencies validation failed\n"
            f"  Reason: {e}\n"
            f"  Setup: pip install yt-dlp youtube-transcript-api"
        ) from e


def validate_searxng(searxng_url: str) -> None:
    """
    Validate SearXNG service is reachable.

    Args:
        searxng_url: SearXNG base URL (e.g. http://localhost:7080).

    Raises:
        ValidationError: If SearXNG is unreachable.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{searxng_url.rstrip('/')}/search",
                params={"q": "test", "format": "json"},
            )
            response.raise_for_status()
    except Exception as e:
        raise ValidationError(
            f"SearXNG validation failed\n"
            f"  Connection: FAILED\n"
            f"  Error: {e}\n"
            f"  Setup: Run 'docker compose up -d searxng' or ensure SearXNG is running\n"
            f"  URL: {searxng_url}"
        ) from e


def validate_llm_api(settings: Settings) -> None:
    """
    Validate LLM API key is configured (for ReadingsService summary generation).

    Args:
        settings: Application settings.

    Raises:
        ValidationError: If LLM API key is missing.
    """
    llm_api_key = getattr(settings, "llm_api_key", None)
    if not llm_api_key:
        raise ValidationError(
            "LLM API validation failed\n"
            "  Reason: LLM_API_KEY not set\n"
            "  Setup: Set LLM_API_KEY in .env for summary generation"
        )


def validate_neo4j(
    neo4j_uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
) -> None:
    """
    Validate Neo4j connection and schema.

    Args:
        neo4j_uri: Neo4j bolt:// connection URI
        username: Database username
        password: Database password
        database: Database name

    Raises:
        ValidationError: If connection fails or schema not initialized
    """
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        raise ValidationError(
            "Neo4j validation failed\n"
            "  Reason: neo4j package not installed\n"
            "  Setup: pip install neo4j"
        ) from e

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))
        driver.verify_connectivity()

        # Check that database is accessible
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 as test")
            result.single()

        driver.close()
    except Exception as e:
        err_msg = str(e)
        raise ValidationError(
            f"Neo4j validation failed\n"
            f"  Connection: FAILED\n"
            f"  Error: {err_msg}\n"
            f"  Setup: Ensure Neo4j is running at {neo4j_uri}\n"
            f"  Docker: docker compose up -d neo4j"
        ) from e


def validate_vllm(
    reasoning_url: str,
    embedding_url: str,
    api_key: str | None = None,
) -> None:
    """
    Validate vLLM service endpoints are reachable.

    Args:
        reasoning_url: vLLM reasoning endpoint (e.g. http://localhost:8000)
        embedding_url: vLLM embedding endpoint (e.g. http://localhost:8001)
        api_key: Optional API key for vLLM

    Raises:
        ValidationError: If vLLM endpoints are unreachable
    """
    import httpx

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Check reasoning endpoint
    try:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            response = client.get(f"{reasoning_url.rstrip('/')}/health")
            response.raise_for_status()
    except Exception as e:
        raise ValidationError(
            f"vLLM reasoning endpoint validation failed\n"
            f"  URL: {reasoning_url}\n"
            f"  Error: {e}\n"
            f"  Setup: Start vLLM reasoning service\n"
            f"  Docker: docker compose -f docker-compose.vllm.yml up -d"
        ) from e

    # Check embedding endpoint
    try:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            response = client.get(f"{embedding_url.rstrip('/')}/health")
            response.raise_for_status()
    except Exception as e:
        raise ValidationError(
            f"vLLM embedding endpoint validation failed\n"
            f"  URL: {embedding_url}\n"
            f"  Error: {e}\n"
            f"  Setup: Start vLLM embedding service\n"
            f"  Docker: docker compose -f docker-compose.vllm.yml up -d"
        ) from e


__all__ = [
    "ValidationError",
    "validate_mongodb",
    "validate_redis",
    "validate_rq_workers",
    "validate_embedding_api",
    "validate_playwright",
    "validate_google_credentials",
    "validate_youtube_deps",
    "validate_searxng",
    "validate_llm_api",
    "validate_neo4j",
    "validate_vllm",
]
