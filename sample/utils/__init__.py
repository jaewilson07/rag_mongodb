"""Sample script utilities for pre-flight checks and common functions."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from mdrag.settings import Settings
from pymongo import AsyncMongoClient
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)
from redis.asyncio import Redis

# Error code for "node is not in primary or recovering state"
_NOT_PRIMARY_OR_SECONDARY = 13436

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_COMPOSE_FILE = _PROJECT_ROOT / "docker-compose.yml"


def _parse_mongodb_uri(uri: str) -> tuple[str | None, int | None]:
    """Parse MongoDB URI; return (hostname, port) or (None, None) if unparseable."""
    parsed = urlparse(uri)
    return (parsed.hostname, parsed.port)


def _is_local_mongodb_uri(uri: str) -> bool:
    """True if URI points to local MongoDB (localhost, 127.0.0.1, or atlas-local)."""
    host, _ = _parse_mongodb_uri(uri)
    return host in ("localhost", "127.0.0.1", "atlas-local") if host else False


def _get_mongodb_container_for_port(port: int) -> str | None:
    """Find container publishing the given port. Returns container name or None."""
    result = subprocess.run(
        ["docker", "ps", "--filter", f"publish={port}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().split("\n")[0] or None


def _try_initiate_replica_set_sync(uri: str) -> bool:
    """Run rs.initiate() on the MongoDB container for the given URI. Returns True if successful.
    Synchronous; use _try_initiate_replica_set from async code."""
    _, port = _parse_mongodb_uri(uri)
    if port is None:
        return False

    # Build connection string for admin db (rs.initiate needs auth)
    parsed = urlparse(uri)
    base = f"{parsed.scheme}://{parsed.netloc}"
    q = parsed.query or ""
    if "authSource=" not in q:
        q = f"{q}&authSource=admin" if q else "authSource=admin"
    conn_str = f"{base}/admin?{q}"

    ev = "try { rs.initiate(); } catch(e) { if (e.codeName === 'AlreadyInitialized') print('OK'); else throw e; }"

    container = _get_mongodb_container_for_port(port)
    if not container:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(_COMPOSE_FILE),
                "exec",
                "-T",
                "atlas-local",
                "mongosh",
                "--quiet",
                conn_str,
                "--eval",
                ev,
            ],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0

    result = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "mongosh",
            "--quiet",
            conn_str,
            "--eval",
            ev,
        ],
        capture_output=True,
        timeout=15,
    )
    return result.returncode == 0


async def _try_initiate_replica_set(uri: str) -> bool:
    """Run rs.initiate() in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(_try_initiate_replica_set_sync, uri)


def _uri_with_direct_connection_for_local(uri: str, is_local: bool) -> str:
    """Add directConnection=true for local URIs to avoid replica set discovery.
    When connecting from host to localhost:7017, the replica set config may list
    unreachable hostnames (e.g. atlas-local:27017); directConnection bypasses
    discovery and prevents 'replicaset members not found' errors."""
    if not is_local or "directConnection=" in uri or "mongodb+srv" in uri:
        return uri
    sep = "&" if "?" in uri else "?"
    return f"{uri}{sep}directConnection=true"


def _uri_with_read_preference(uri: str) -> str:
    """Append readPreference=primaryPreferred for replica set compatibility.
    Skip when directConnection=true to avoid blocking on RSGhost/stale replica set."""
    if "directConnection=true" in uri:
        return uri
    sep = "&" if "?" in uri else "?"
    if "readPreference=" in uri:
        return uri
    return f"{uri}{sep}readPreference=primaryPreferred"


def _try_start_mongodb_sync() -> bool:
    """Attempt to start MongoDB via docker compose. Returns True if compose ran successfully.
    Synchronous; use _try_start_mongodb from async code."""
    if not _COMPOSE_FILE.exists():
        return False
    result = subprocess.run(
        ["docker", "compose", "-f", str(_COMPOSE_FILE), "up", "-d", "atlas-local"],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        timeout=60,
    )
    return result.returncode == 0


async def _try_start_mongodb() -> bool:
    """Attempt to start MongoDB via docker compose. Non-blocking."""
    return await asyncio.to_thread(_try_start_mongodb_sync)


async def _ensure_schema(client: AsyncMongoClient, settings: Settings) -> bool:
    """Create collections if missing and run init_indexes. Returns True if schema is ready."""
    db = client[settings.mongodb_database]
    collections = await db.list_collection_names()
    docs_name = settings.mongodb_collection_documents
    chunks_name = settings.mongodb_collection_chunks

    created = False
    if docs_name not in collections:
        await db.create_collection(docs_name)
        created = True
    if chunks_name not in collections:
        await db.create_collection(chunks_name)
        created = True

    # Run init_indexes to create vector and text search indexes
    init_script = _PROJECT_ROOT / "server" / "maintenance" / "init_indexes.py"
    if init_script.exists():
        proc = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "python",
            str(init_script),
            cwd=str(_PROJECT_ROOT),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        # init_indexes exits 0 even with warnings; we consider it success
        created = created or proc.returncode == 0

    return created


async def check_mongodb(
    settings: Settings,
    *,
    auto_start: bool = True,
    auto_schema: bool = True,
) -> dict[str, Any]:
    """
    Check MongoDB connection and verify required indexes exist.

    When auto_start=True and connection fails for a local URI, attempts to start
    MongoDB via docker compose. When auto_schema=True and collections/indexes
    are missing, creates collections and runs init_indexes.

    Args:
        settings: Application settings with MongoDB configuration
        auto_start: If True, try to start Docker MongoDB on connection failure (local URI only)
        auto_schema: If True, create collections and indexes when missing

    Returns:
        Dictionary with status, message, and optional details
    """
    is_local = _is_local_mongodb_uri(settings.mongodb_connection_string)
    uri = _uri_with_direct_connection_for_local(
        settings.mongodb_connection_string, is_local
    )
    uri = _uri_with_read_preference(uri)

    async def _do_check() -> dict[str, Any]:
        client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        try:
            await client.admin.command("ping")
        except Exception:
            await client.close()
            raise

        db = client[settings.mongodb_database]
        try:
            collections = await db.list_collection_names()
        except Exception:
            await client.close()
            raise

        has_docs = settings.mongodb_collection_documents in collections
        has_chunks = settings.mongodb_collection_chunks in collections

        indexes_ok = True
        missing_indexes = []

        if has_chunks:
            chunks = db[settings.mongodb_collection_chunks]
            # Atlas Search indexes (vector, text) are not in list_indexes(); use $listSearchIndexes
            search_index_names: list[str] = []
            try:
                agg_cursor = await chunks.aggregate([{"$listSearchIndexes": {}}])
                search_indexes = await agg_cursor.to_list(length=None)
                search_index_names = [idx.get("name") for idx in search_indexes if idx.get("name")]
            except Exception:
                pass  # Atlas Search not available (e.g. older MongoDB)
            index_names = search_index_names

            if settings.mongodb_vector_index not in index_names:
                missing_indexes.append(
                    f"Vector index '{settings.mongodb_vector_index}'"
                )
                indexes_ok = False

            if settings.mongodb_text_index not in index_names:
                missing_indexes.append(
                    f"Text index '{settings.mongodb_text_index}'"
                )
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

    last_error: Exception | None = None

    for attempt in range(3):
        try:
            # Auto-start: on first connection failure for local URI, try docker compose
            # (only when URI port matches our project's docker port; other ports may be different compose)
            _, uri_port = _parse_mongodb_uri(settings.mongodb_connection_string)
            uri_uses_project_port = uri_port == settings.mongodb_docker_port
            if attempt == 0 and auto_start and is_local:
                try:
                    return await _do_check()
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    last_error = e
                    if uri_uses_project_port and await _try_start_mongodb():
                        await asyncio.sleep(30)
                        continue
                    break
                except OperationFailure as e:
                    if getattr(e, "code", None) == _NOT_PRIMARY_OR_SECONDARY:
                        last_error = e
                        await _try_initiate_replica_set(settings.mongodb_connection_string)
                        await asyncio.sleep(5)
                        continue
                    last_error = e
                    break
                except Exception as e:
                    last_error = e
                    break

            result = await _do_check()

            # Auto-schema: if collections or indexes missing, create them
            if (
                auto_schema
                and result["status"] in ("warning", "error")
                and "MongoDB connected" in result["message"]
            ):
                client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
                try:
                    await client.admin.command("ping")
                    await _ensure_schema(client, settings)
                    await client.close()
                    return await _do_check()
                except Exception:
                    await client.close()
                    raise

            return result

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            last_error = e
            if attempt < 2:
                await asyncio.sleep(2)
                continue
            break
        except OperationFailure as e:
            if getattr(e, "code", None) == _NOT_PRIMARY_OR_SECONDARY:
                last_error = e
                if attempt == 0 and is_local:
                    # Replica set may not be initialized; try rs.initiate()
                    await _try_initiate_replica_set(settings.mongodb_connection_string)
                    await asyncio.sleep(5)
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
            last_error = e
            break
        except Exception as e:
            last_error = e
            break

    err = last_error or Exception("Unknown error")
    details: dict[str, Any] = {"error": str(err)}
    if "NotPrimaryOrSecondary" in str(err) or "13436" in str(err):
        details["hint"] = (
            "Replica set may need rs.initiate(). "
            f"For this project's Docker MongoDB, use MONGODB_URI with localhost:{settings.mongodb_docker_port}."
        )
    return {
        "status": "error",
        "message": f"MongoDB connection failed: {err}",
        "details": details,
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


def check_rq_workers(redis_url: str, queue_name: str = "default") -> dict[str, Any]:
    """
    Check if RQ workers are listening to the ingestion queue.

    Args:
        redis_url: Redis connection URL
        queue_name: RQ queue name to check (default: "default")

    Returns:
        Dictionary with status and message
    """
    try:
        import redis
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
            return {
                "status": "error",
                "message": f"No RQ workers listening to '{queue_name}' queue",
                "details": {
                    "hint": f"Start a worker: uv run rq worker {queue_name} --url {redis_url}",
                },
            }

        return {
            "status": "ok",
            "message": f"RQ workers active: {count} worker(s) on '{queue_name}' queue",
        }

    except ImportError as e:
        return {
            "status": "error",
            "message": f"RQ not installed: {e}",
            "details": {"hint": "Install with: uv pip install rq"},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"RQ worker check failed: {e}",
            "details": {"error": str(e)},
        }


def check_neo4j(
    neo4j_uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
) -> dict[str, Any]:
    """
    Check Neo4j connection and accessibility.

    Args:
        neo4j_uri: Neo4j bolt:// connection URI
        username: Database username
        password: Database password
        database: Database name

    Returns:
        Dictionary with status and message
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {
            "status": "error",
            "message": "Neo4j package not installed",
            "details": {"hint": "Install with: pip install neo4j"},
        }

    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))
        driver.verify_connectivity()

        # Test database access
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 as test")
            result.single()

        driver.close()

        return {
            "status": "ok",
            "message": f"Neo4j connection successful (database: {database})",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Neo4j connection failed: {e}",
            "details": {"hint": "Ensure Neo4j is running: docker compose up -d neo4j"},
        }


def check_vllm(
    reasoning_url: str,
    embedding_url: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Check vLLM service endpoints are reachable.

    Args:
        reasoning_url: vLLM reasoning endpoint
        embedding_url: vLLM embedding endpoint
        api_key: Optional API key

    Returns:
        Dictionary with status and message
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
        return {
            "status": "error",
            "message": f"vLLM reasoning endpoint failed: {e}",
            "details": {"hint": "Start vLLM: docker compose -f docker-compose.vllm.yml up -d"},
        }

    # Check embedding endpoint
    try:
        with httpx.Client(timeout=10.0, headers=headers) as client:
            response = client.get(f"{embedding_url.rstrip('/')}/health")
            response.raise_for_status()
    except Exception as e:
        return {
            "status": "error",
            "message": f"vLLM embedding endpoint failed: {e}",
            "details": {"hint": "Start vLLM: docker compose -f docker-compose.vllm.yml up -d"},
        }

    return {
        "status": "ok",
        "message": "vLLM services accessible (reasoning + embedding)",
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
            details = result.get("details", {})
            if "hint" in details:
                print(f"   Hint: {details['hint']}")

    print("=" * 60)

    if not all_passed:
        print("\nSome checks failed. Please resolve issues before running this sample.")
        print()

    return all_passed
