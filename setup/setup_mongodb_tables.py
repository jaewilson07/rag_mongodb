"""
Setup MongoDB collections (tables) required by the RAG agent.

Creates missing collections only—idempotent, no duplicates.
Uses Settings for configuration. Run after MongoDB is available.

Usage:
    uv run python setup/setup_mongodb_tables.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure

# Add src for mdrag imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from mdrag.settings import Settings

# Collections required by the RAG system (from Settings)
_REQUIRED_COLLECTIONS = [
    "mongodb_collection_documents",
    "mongodb_collection_chunks",
    "mongodb_collection_traces",
    "mongodb_collection_feedback",
]


async def _ensure_collection(db, name: str) -> bool:
    """Create collection only if it does not exist. Idempotent."""
    existing = await db.list_collection_names()
    if name in existing:
        return False  # Already exists, no change
    await db.create_collection(name)
    return True


async def setup_collections(settings: Settings) -> dict[str, bool]:
    """
    Ensure all required collections exist. Creates only missing ones.

    Returns:
        Dict mapping collection name -> True if created, False if already existed
    """
    uri = settings.mongodb_uri
    if "directConnection" not in uri and "mongodb+srv" not in uri:
        uri = f"{uri}{'&' if '?' in uri else '?'}directConnection=true"

    client = AsyncMongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[settings.mongodb_database]
    results: dict[str, bool] = {}

    try:
        for attr in _REQUIRED_COLLECTIONS:
            name = getattr(settings, attr)
            created = await _ensure_collection(db, name)
            results[name] = created
    finally:
        await client.close()

    return results


async def run_init_indexes() -> bool:
    """Run server/maintenance/init_indexes for vector and text search indexes."""
    init_script = _ROOT / "server" / "maintenance" / "init_indexes.py"
    if not init_script.exists():
        return False
    proc = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "python",
        str(init_script),
        cwd=str(_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()
    return proc.returncode == 0


async def main() -> int:
    settings = Settings()

    try:
        results = await setup_collections(settings)
        for name, created in results.items():
            status = "created" if created else "exists"
            print(f"  {name}: {status}")

        indexes_ok = await run_init_indexes()
        if indexes_ok:
            print("  Indexes: initialized")
        else:
            print(
                "  Indexes: check server/maintenance/init_indexes.py (may require Atlas Search)"
            )

        return 0
    except ConnectionFailure as e:
        print(f"Error: MongoDB connection failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    print("MongoDB setup (idempotent)...")
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
