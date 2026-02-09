"""Test search functions with MongoDB database.

Usage:
    uv run python sample/retrieval/test_search.py

Requirements:
    - MongoDB with vector and text indexes
    - Embedding API key for generating query embeddings
"""

import asyncio

# Import pre-flight utilities
import sys
from pathlib import Path

from mdrag.dependencies import AgentDependencies
from mdrag.settings import load_settings
from mdrag.tools import hybrid_search, semantic_search

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import check_api_keys, check_mongodb, print_pre_flight_results


class MockContext:
    """Mock context for search functions."""

    def __init__(self, deps):
        self.deps = deps


async def test_database_connection():
    """Test MongoDB connection and check for data."""
    print("Testing MongoDB connection...")
    deps = AgentDependencies()
    await deps.initialize()

    # Check chunk count
    chunk_count = await deps.db.chunks.count_documents({})
    doc_count = await deps.db.documents.count_documents({})

    print(f"Documents in database: {doc_count}")
    print(f"Chunks in database: {chunk_count}")

    await deps.cleanup()
    return chunk_count > 0


async def test_semantic_search():
    """Test semantic search."""
    print("\nTesting semantic search...")
    deps = AgentDependencies()
    await deps.initialize()
    ctx = MockContext(deps)

    results = await semantic_search(ctx, "test query", match_count=5)
    print(f"Semantic search returned {len(results)} results")

    if results:
        print(
            f"Top result: {results[0].document_title} (similarity: {results[0].similarity:.3f})"
        )

    await deps.cleanup()
    return len(results) > 0


async def test_hybrid_search():
    """Test hybrid search."""
    print("\nTesting hybrid search...")
    deps = AgentDependencies()
    await deps.initialize()
    ctx = MockContext(deps)

    results = await hybrid_search(ctx, "MongoDB vector search", match_count=5)
    print(f"Hybrid search returned {len(results)} results")

    if results:
        for i, r in enumerate(results[:3], 1):
            print(f"{i}. {r.document_title} - {r.similarity:.3f}")

    await deps.cleanup()
    return len(results) > 0


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MongoDB RAG Agent - Search Function Tests")
    print("=" * 60)

    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=False, require_embedding=True),
    }

    if not print_pre_flight_results(checks):
        print("Resolve the issues above before running this sample.")
        sys.exit(1)

    try:
        # Test connection
        has_data = await test_database_connection()
        if not has_data:
            print("\n[WARNING] No data in database. Run ingestion first:")
            print("  uv run python -m mdrag.ingestion.ingest -d documents")
            return

        # Test searches
        await test_semantic_search()
        await test_hybrid_search()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
