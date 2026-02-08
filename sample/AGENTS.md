# Sample Scripts - Agent Guide

## Purpose
Curated sample and validation scripts grouped by domain. Each script demonstrates a specific capability and can be run independently.

## Table of Contents
See [changelog.md](changelog.md) for the complete index of all sample scripts with descriptions and run commands. **Always update changelog.md when adding or modifying samples.**

## Layout
- sample/wiki/ — wiki structure generation, page streaming, chat
- sample/readings/ — save-and-research pipeline (URLs, YouTube, tweets)
- sample/youtube/ — YouTube metadata and transcript extraction
- sample/crawl4ai/ — web crawling and save-to-reading
- sample/rag/ — end-to-end and conversational agent checks
- sample/retrieval/ — search and pipeline validation
- sample/searxng/ — SearXNG web meta-search
- sample/ingestion/ — ingestion-related validation utilities
- sample/mongodb/ — cluster and index inspection
- sample/docling/ — document processing and chunking
- sample/google_drive/ — Google Drive integration
- sample/eval/ — gold dataset evaluation

## Run Examples
```bash
# Wiki generation
uv run python sample/wiki/generate_wiki.py
uv run python sample/wiki/generate_page.py --title "Architecture"
uv run python sample/wiki/chat_wiki.py --question "How does auth work?"

# Save & Research
uv run python sample/readings/save_url.py --url "https://example.com"
uv run python sample/readings/save_url.py --url "https://youtu.be/PAh870We7tI"
uv run python sample/readings/list_readings.py

# YouTube extraction
uv run python sample/youtube/extract_video.py --url "https://youtu.be/PAh870We7tI"

# Web crawling
uv run python sample/crawl4ai/crawl_and_save.py --url "https://docs.python.org"
uv run python sample/crawl4ai/crawl4ai_ingest.py --url "https://example.com"

# RAG query
uv run python sample/rag/query_rag.py
uv run python sample/retrieval/test_search.py

# MongoDB
uv run python sample/mongodb/check_indexes.py
```

## Script Style Guide

All samples follow these conventions:
1. Module docstring with `Usage:` section showing `uv run python ...` commands
2. `argparse` for CLI arguments with sensible defaults
3. `asyncio.run(_run())` as entry point
4. Structured output with labels, separators, and sections
5. `try/finally` for cleanup of async services
6. `from mdrag.*` imports for internal modules

## Notes
- These scripts require a configured .env and MongoDB with indexes.
- They are not part of pytest or CI.
- Always update [changelog.md](changelog.md) when adding new samples.
