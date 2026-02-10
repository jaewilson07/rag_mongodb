#!/usr/bin/env python
"""Test embedding configuration and connectivity."""

import asyncio
import sys
from mdrag.config.settings import load_settings
from mdrag.capabilities.retrieval.embeddings import EmbeddingClient


async def test_embedding_config():
    """Test current embedding configuration."""
    settings = load_settings()

    print("=" * 70)
    print("EMBEDDING CONFIGURATION TEST")
    print("=" * 70)

    print("\nConfiguration:")
    print(f"  Provider: {settings.embedding_provider}")
    print(f"  Model: {settings.embedding_model}")
    print(f"  Base URL: {settings.embedding_base_url}")
    print(f"  Dimension: {settings.embedding_dimension}")
    print(f"  API Key: {'***hidden***' if settings.embedding_api_key else '(not set)'}")

    print("\nTesting connectivity...")
    client = EmbeddingClient(settings=settings)

    try:
        # Test single embedding
        print("  • Testing single embedding...", end=" ")
        embedding = await client.embed_text("test message")
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) == settings.embedding_dimension, \
            f"Expected {settings.embedding_dimension} dimensions, got {len(embedding)}"
        print(f"✓ ({len(embedding)} dims)")

        # Test batch embedding
        print("  • Testing batch embedding...", end=" ")
        embeddings = await client.embed_texts([
            "first document",
            "second document",
            "third document"
        ])
        assert len(embeddings) == 3, "Should return 3 embeddings"
        assert all(len(e) == settings.embedding_dimension for e in embeddings), \
            "All embeddings should have same dimension"
        print(f"✓ ({len(embeddings)} items)")

        # Test with longer text
        print("  • Testing with longer text...", end=" ")
        long_text = "This is a longer test. " * 50
        embedding = await client.embed_text(long_text)
        assert len(embedding) == settings.embedding_dimension, \
            "Long text should still produce correct dimensions"
        print(f"✓ (truncated to {len(long_text)} chars)")

        await client.close()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        print("\nEmbedding service is working correctly!")
        print("You can now run the ingestion pipeline:")
        print("  uv run python sample/crawl4ai/crawl4ai_ingest.py --url <url>")
        return True

    except Exception as e:
        await client.close()
        print(f"✗ FAILED")
        print("\n" + "=" * 70)
        print("✗ EMBEDDING TEST FAILED")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Check EMBEDDING_API_KEY in .env")
        print("  2. Check EMBEDDING_BASE_URL is accessible")
        print("  3. For local services, ensure they are running:")
        print("     - docker-compose up embedding-server")
        print("     - ollama serve")
        print("  4. See EMBEDDING_SETUP.md for configuration options")
        return False


async def main():
    """Run embedding test."""
    try:
        success = await test_embedding_config()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
