# Sample Scripts Changelog

> This file serves as a **table of contents** for all sample scripts.
> Every new sample must be listed here with a brief description and run command.
> When adding a sample, append it under the appropriate section below.

---

## Recent Updates

### February 8, 2026 - Sample Script Validation & Cleanup

**Phase 1: Foundation (Complete)**
- Updated 10 scripts from `src.*` to `mdrag.*` imports for consistency with project standards
- Removed all `# type: ignore` comments from 4 files (resolved import path issues)
- Added `sample/**/EXPORTS/` to `.gitignore` to prevent tracking generated files
- Created pre-flight service check utility: `sample/utils/__init__.py`

**Phase 2: Pre-flight Checks (Complete - 25/25 samples)**

*Wiki Samples (4/4)*
- ✅ `wiki/generate_wiki.py` - MongoDB + LLM
- ✅ `wiki/generate_page.py` - MongoDB + indexes + LLM + embeddings
- ✅ `wiki/list_projects.py` - MongoDB only
- ✅ `wiki/chat_wiki.py` - MongoDB + indexes + LLM + embeddings

*RAG & Retrieval Samples (7/7)*
- ✅ `rag/query_rag.py` - Full stack
- ✅ `rag/comprehensive_e2e_test.py` - Full stack
- ✅ `rag/test_agent_e2e.py` - Full stack
- ✅ `rag/additional_tests.py` - Full stack
- ✅ `eval/run_gold_eval.py` - Full stack
- ✅ `retrieval/test_search.py` - MongoDB + indexes + embeddings
- ✅ `retrieval/test_rag_pipeline.py` - MongoDB + indexes + embeddings

*Readings Samples (2/2)*
- ✅ `readings/save_url.py` - MongoDB + Redis + SearXNG + LLM + Crawl4AI
- ✅ `readings/list_readings.py` - MongoDB only

*Ingestion Samples (9/9)* - **All Complete!**
- ✅ `crawl4ai/crawl4ai_ingest.py` - MongoDB + Playwright + embeddings
- ✅ `crawl4ai/crawl_and_save.py` - MongoDB + Redis + SearXNG + Playwright + LLM
- ✅ `crawl4ai/export_domo_release_notes.py` - Playwright only
- ✅ `docling/docling_ingest.py` - MongoDB + embeddings
- ✅ `docling/chunk_pydantic_sample.py` - File existence check
- ✅ `google_drive/google_drive_ingest.py` - MongoDB + Google service account + embeddings
- ✅ `google_drive/multi_folder/download_multi_folder.py` - Google OAuth
- ✅ `google_drive/single_file/download_single_doc.py` - Google OAuth
- ✅ `ingestion/validate_source_urls.py` - MongoDB only

*Search Samples (1/1)*
- ✅ `searxng/query_searxng.py` - SearXNG only

**Key Improvements:**
- All 25 functional samples now have pre-flight checks with helpful error messages
- Clear service status indicators (✓ or ❌) for each dependency
- Step-by-step setup instructions when checks fail
- Consistent error formatting across all samples

**Next Steps:**
- Phase 3: Validation and testing with real services
- Optional: Add pre-flight checks to MongoDB utility scripts

---

## Wiki Generation

| Script | Description | Run Command |
|--------|-------------|-------------|
| [wiki/generate_wiki.py](wiki/generate_wiki.py) | Generate a wiki structure from ingested documents; prints sections, pages, and importance levels | `uv run python sample/wiki/generate_wiki.py` |
| [wiki/generate_page.py](wiki/generate_page.py) | Stream-generate content for a single wiki page via RAG | `uv run python sample/wiki/generate_page.py --title "Architecture Overview"` |
| [wiki/list_projects.py](wiki/list_projects.py) | List wiki projects derived from document groups in MongoDB | `uv run python sample/wiki/list_projects.py` |
| [wiki/chat_wiki.py](wiki/chat_wiki.py) | Chat with the knowledge base using wiki context; streams response | `uv run python sample/wiki/chat_wiki.py --question "How does auth work?"` |

## Readings (Save & Research)

| Script | Description | Run Command |
|--------|-------------|-------------|
| [readings/save_url.py](readings/save_url.py) | Save any URL: crawl, summarize, find related links, ingest. Supports web pages, YouTube, and tweets | `uv run python sample/readings/save_url.py --url "https://example.com"` |
| [readings/list_readings.py](readings/list_readings.py) | List saved readings from MongoDB with summaries and metadata | `uv run python sample/readings/list_readings.py` |

## YouTube

| Script | Description | Run Command |
|--------|-------------|-------------|
| [youtube/extract_video.py](youtube/extract_video.py) | Extract YouTube metadata, chapters, and transcript without API keys | `uv run python sample/youtube/extract_video.py --url "https://youtu.be/PAh870We7tI"` |

## Web Crawling

| Script | Description | Run Command |
|--------|-------------|-------------|
| [crawl4ai/crawl4ai_ingest.py](crawl4ai/crawl4ai_ingest.py) | Ingest a web page via Crawl4AI into the RAG pipeline | `uv run python sample/crawl4ai/crawl4ai_ingest.py --url "https://example.com"` |
| [crawl4ai/crawl_and_save.py](crawl4ai/crawl_and_save.py) | Crawl a URL and save as a reading with AI summary and related links | `uv run python sample/crawl4ai/crawl_and_save.py --url "https://docs.python.org"` |
| [crawl4ai/export_domo_release_notes.py](crawl4ai/export_domo_release_notes.py) | Export Domo release notes via Crawl4AI | `uv run python sample/crawl4ai/export_domo_release_notes.py` |

## RAG Query

| Script | Description | Run Command |
|--------|-------------|-------------|
| [rag/query_rag.py](rag/query_rag.py) | Query the RAG pipeline and print answer with citations | `uv run python sample/rag/query_rag.py` |
| [rag/comprehensive_e2e_test.py](rag/comprehensive_e2e_test.py) | End-to-end RAG validation with multiple query types | `uv run python sample/rag/comprehensive_e2e_test.py` |
| [rag/test_agent_e2e.py](rag/test_agent_e2e.py) | Pydantic AI agent end-to-end test | `uv run python sample/rag/test_agent_e2e.py` |
| [rag/count_chunks.py](rag/count_chunks.py) | Count chunks in MongoDB | `uv run python sample/rag/count_chunks.py` |
| [rag/additional_tests.py](rag/additional_tests.py) | Additional RAG validation tests | `uv run python sample/rag/additional_tests.py` |

## Retrieval

| Script | Description | Run Command |
|--------|-------------|-------------|
| [retrieval/test_search.py](retrieval/test_search.py) | Test semantic, text, and hybrid search pipelines | `uv run python sample/retrieval/test_search.py` |
| [retrieval/test_rag_pipeline.py](retrieval/test_rag_pipeline.py) | Full retrieval pipeline validation | `uv run python sample/retrieval/test_rag_pipeline.py` |

## SearXNG

| Script | Description | Run Command |
|--------|-------------|-------------|
| [searxng/query_searxng.py](searxng/query_searxng.py) | Query SearXNG and export results with Source frontmatter | `uv run python sample/searxng/query_searxng.py --query "AI developments"` |

## Document Ingestion

| Script | Description | Run Command |
|--------|-------------|-------------|
| [docling/docling_ingest.py](docling/docling_ingest.py) | Ingest local documents via Docling | `uv run python sample/docling/docling_ingest.py` |
| [docling/chunk_pydantic_sample.py](docling/chunk_pydantic_sample.py) | Structure-aware chunking with heading subsetting | `uv run python sample/docling/chunk_pydantic_sample.py` |
| [ingestion/validate_source_urls.py](ingestion/validate_source_urls.py) | Validate source URLs in ingested documents | `uv run python sample/ingestion/validate_source_urls.py` |

## Google Drive

| Script | Description | Run Command |
|--------|-------------|-------------|
| [google_drive/google_drive_ingest.py](google_drive/google_drive_ingest.py) | Ingest Google Drive files into RAG | `uv run python sample/google_drive/google_drive_ingest.py` |

## MongoDB

| Script | Description | Run Command |
|--------|-------------|-------------|
| [mongodb/check_indexes.py](mongodb/check_indexes.py) | Check MongoDB Atlas index configuration | `uv run python sample/mongodb/check_indexes.py` |
| [mongodb/check_cluster_info.py](mongodb/check_cluster_info.py) | Display MongoDB cluster information | `uv run python sample/mongodb/check_cluster_info.py` |
| [mongodb/check_version.py](mongodb/check_version.py) | Check MongoDB server version | `uv run python sample/mongodb/check_version.py` |

## Evaluation

| Script | Description | Run Command |
|--------|-------------|-------------|
| [eval/run_gold_eval.py](eval/run_gold_eval.py) | Run gold dataset evaluation against RAG pipeline | `uv run python sample/eval/run_gold_eval.py` |
