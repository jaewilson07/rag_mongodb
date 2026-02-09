# Sample Scripts Implementation Progress

**Date**: February 8, 2026  
**Status**: Phase 2 Complete - All Ingestion Samples Ready (100%)

## ✅ Completed Tasks

### 1. Fixed Import Inconsistencies (10 files)
All sample scripts now use `mdrag.*` imports instead of `src.*`:

- ✅ `sample/retrieval/test_search.py`
- ✅ `sample/retrieval/test_rag_pipeline.py`
- ✅ `sample/rag/comprehensive_e2e_test.py`
- ✅ `sample/rag/test_agent_e2e.py`
- ✅ `sample/rag/additional_tests.py`
- ✅ `sample/eval/run_gold_eval.py`
- ✅ `sample/ingestion/validate_source_urls.py`
- ✅ `sample/mongodb/check_indexes.py`
- ✅ `sample/mongodb/check_cluster_info.py`
- ✅ `sample/mongodb/check_version.py`

**Impact**: All samples now follow project standards and are consistent with the main codebase.

### 2. Removed Type Ignore Comments (4 files)
Cleaned up type checking suppressions:

- ✅ `sample/docling/chunk_pydantic_sample.py` (5 occurrences + pyright directive)
- ✅ `sample/rag/count_chunks.py`
- ✅ `sample/crawl4ai/export_domo_release_notes.py`
- ✅ `sample/searxng/query_searxng.py`

**Impact**: Cleaner code without type checking workarounds.

### 3. Updated .gitignore
Added pattern to ignore generated exports:

```gitignore
# Sample script exports (generated content)
sample/**/EXPORTS/
```

**Impact**: Prevents tracking of generated files while keeping existing exports as examples.

### 4. Created Pre-flight Check Utility (`sample/utils/__init__.py`)
Comprehensive utility module with functions for:

- ✅ `check_mongodb()` - Verify MongoDB connection and indexes
- ✅ `check_redis()` - Verify Redis availability
- ✅ `check_searxng()` - Verify SearXNG availability
- ✅ `check_playwright()` - Verify Playwright installation
- ✅ `check_google_credentials()` - Verify Google Drive auth
- ✅ `check_api_keys()` - Verify LLM/embedding API keys
- ✅ `print_service_error()` - Consistent error formatting
- ✅ `print_pre_flight_results()` - Results summary

**Impact**: Samples can now gracefully check dependencies before execution with helpful error messages.

### 5. Added Pre-flight Checks to Sample Script
Demonstrated pattern in `sample/retrieval/test_search.py`:

- ✅ Added docstring with Usage and Requirements sections
- ✅ Integrated pre-flight checks for MongoDB and API keys
- ✅ Clear error messages if services are unavailable

**Example Output**:
```
============================================================
PRE-FLIGHT CHECKS
============================================================
✓ MongoDB: MongoDB connection successful
✓ API Keys: API keys configured
============================================================
```

### 6. Created Comprehensive Documentation

#### `sample/README.md` (423 lines)
Comprehensive setup guide covering:

- ✅ Quick start instructions
- ✅ Directory structure overview
- ✅ External service dependencies matrix
- ✅ Configuration requirements (all env vars)
- ✅ MongoDB Atlas setup (vector + text indexes)
- ✅ Service setup (Docker, Playwright, Google Drive)
- ✅ Sample categories with run commands
- ✅ Pre-flight check examples
- ✅ Troubleshooting section
- ✅ Adding new samples guide

**Impact**: Clear entry point for anyone using sample scripts.

#### Updated `sample/changelog.md`
- ✅ Added "Recent Updates" section documenting all changes
- ✅ Listed all fixed files with descriptions
- ✅ Added next steps roadmap

**Impact**: Clear history of sample script improvements.

### 7. Validation
- ✅ Syntax validation passed for all updated scripts
- ✅ Fixed linting errors in utility module
- ✅ No compilation errors in updated files

### ✅ Phase 2: Pre-flight Checks Added (72% Complete)

**Wiki Samples (4/4 - 100%)**
- ✅ [sample/wiki/generate_wiki.py](sample/wiki/generate_wiki.py) - MongoDB + LLM
- ✅ [sample/wiki/generate_page.py](sample/wiki/generate_page.py) - MongoDB + indexes + LLM + embeddings
- ✅ [sample/wiki/list_projects.py](sample/wiki/list_projects.py) - MongoDB only
- ✅ [sample/wiki/chat_wiki.py](sample/wiki/chat_wiki.py) - MongoDB + indexes + LLM + embeddings

**RAG & Retrieval Samples (7/7 - 100%)**
- ✅ [sample/rag/query_rag.py](sample/rag/query_rag.py) - MongoDB + indexes + LLM + embeddings
- ✅ [sample/rag/comprehensive_e2e_test.py](sample/rag/comprehensive_e2e_test.py) - Full stack
- ✅ [sample/rag/test_agent_e2e.py](sample/rag/test_agent_e2e.py) - Full stack
- ✅ [sample/rag/additional_tests.py](sample/rag/additional_tests.py) - Full stack
- ✅ [sample/eval/run_gold_eval.py](sample/eval/run_gold_eval.py) - Full stack
- ✅ [sample/retrieval/test_search.py](sample/retrieval/test_search.py) - MongoDB + indexes + embeddings
- ✅ [sample/retrieval/test_rag_pipeline.py](sample/retrieval/test_rag_pipeline.py) - MongoDB + indexes + embeddings

**Readings Samples (2/2 - 100%)**
- ✅ [sample/readings/save_url.py](sample/readings/save_url.py) - MongoDB + Redis + SearXNG + LLM + Crawl4AI
- ✅ [sample/readings/list_readings.py](sample/readings/list_readings.py) - MongoDB only

**Ingestion Samples (9/9 - 100%)** ✅
- ✅ [sample/crawl4ai/crawl4ai_ingest.py](sample/crawl4ai/crawl4ai_ingest.py) - MongoDB + Playwright + embeddings
- ✅ [sample/crawl4ai/crawl_and_save.py](sample/crawl4ai/crawl_and_save.py) - MongoDB + Redis + SearXNG + Playwright + LLM
- ✅ [sample/crawl4ai/export_domo_release_notes.py](sample/crawl4ai/export_domo_release_notes.py) - Playwright only
- ✅ [sample/docling/docling_ingest.py](sample/docling/docling_ingest.py) - MongoDB + embeddings
- ✅ [sample/docling/chunk_pydantic_sample.py](sample/docling/chunk_pydantic_sample.py) - Local file check
- ✅ [sample/google_drive/google_drive_ingest.py](sample/google_drive/google_drive_ingest.py) - MongoDB + Google creds + embeddings
- ✅ [sample/google_drive/multi_folder/download_multi_folder.py](sample/google_drive/multi_folder/download_multi_folder.py) - Google OAuth
- ✅ [sample/google_drive/single_file/download_single_doc.py](sample/google_drive/single_file/download_single_doc.py) - Google OAuth
- ✅ [sample/ingestion/validate_source_urls.py](sample/ingestion/validate_source_urls.py) - MongoDB only

**Search Samples (1/1 - 100%)**
- ✅ [sample/searxng/query_searxng.py](sample/searxng/query_searxng.py) - SearXNG only

**Impact**: 18 high-priority samples now have pre-flight checks with helpful error messages and setup instructions.

## 📋 Remaining Tasks

### Phase 2: Add Pre-flight Checks to All Sample Categories

The following sample categories need pre-flight checks added:

#### High Priority (Require Multiple Services)
- [ ] **Wiki samples (4 scripts)**: MongoDB + LLM API
  - `wiki/generate_wiki.py`
  - `wiki/generate_page.py`
  - `wiki/list_projects.py`
  - `wiki/chat_wiki.py`

- [ ] **Readings samples (2 scripts)**: MongoDB + Redis + SearXNG + Crawl4AI + LLM
  - `readings/save_url.py`
  - `readings/list_readings.py`

- [ ] **Crawl4AI samples (3 scripts)**: Playwright + MongoDB (where applicable)
  - `crawl4ai/crawl4ai_ingest.py`
  - `crawl4ai/crawl_and_save.py`
  - `crawl4ai/export_domo_release_notes.py`

#### Medium Priority (Core Functionality)
- [ ] **RAG samples (4 scripts)**: MongoDB + indexes + LLM + embedding
  - `rag/query_rag.py` (if exists)
  - `rag/comprehensive_e2e_test.py`
  - `rag/test_agent_e2e.py`
  - `rag/additional_tests.py`

- [ ] **Retrieval samples (1 remaining)**: MongoDB + indexes + embedding
  - `retrieval/test_rag_pipeline.py`

- [ ] **Docling samples (2 scripts)**: MongoDB + Docling
  - `docling/docling_ingest.py`
  - `docling/chunk_pydantic_sample.py`

#### Lower Priority (Simpler Dependencies)
- [ ] **SearXNG sample (1 script)**: SearXNG only
  - `searxng/query_searxng.py`

- [ ] **Google Drive samples (3 scripts)**: Google credentials + MongoDB
  - `google_drive/google_drive_ingest.py`
  - `google_drive/multi_folder/download_multi_folder.py`
  - `google_drive/single_file/download_single_doc.py`

- [ ] **Eval sample (1 script)**: MongoDB + LLM
  - `eval/run_gold_eval.py`

#### Optional (Utility Scripts)
- [ ] **MongoDB utilities (2 remaining)**: MongoDB only
  - `mongodb/check_cluster_info.py`
  - `mongodb/check_version.py`
  - Note: `check_indexes.py` might benefit from checks

- [ ] **Ingestion validation (1 script)**: MongoDB only
  - `ingestion/validate_source_urls.py`

#### Not Needed (Standalone)
- ✅ **YouTube sample**: No external services required
  - `youtube/extract_video.py` (standalone, uses yt-dlp)

- ✅ **DarwinXML demo**: No external services required
  - `darwinxml_demo.py` (demonstration only)

- ✅ **Count chunks**: Simple utility
  - `rag/count_chunks.py` (just counts, no operations)

### Phase 3: Full Validation & Testing

- [ ] **End-to-End Testing**
  - [ ] Set up test environment with all services
  - [ ] Test each sample category with real services
  - [ ] Verify pre-flight checks catch missing services
  - [ ] Verify error messages are helpful
  - [ ] Document any issues found

- [ ] **Service Configuration Testing**
  - [ ] MongoDB Atlas with indexes
  - [ ] SearXNG via Docker
  - [ ] Redis via Docker
  - [ ] Playwright installation
  - [ ] Google Drive authentication (both methods)

- [ ] **Documentation Validation**
  - [ ] Verify all run commands work
  - [ ] Test troubleshooting steps
  - [ ] Ensure all env vars documented
  - [ ] Check setup instructions accuracy

### Phase 4: Advanced Improvements (Optional)

- [ ] **Integration Tests**
  - [ ] Create `tests/samples/` directory
  - [ ] Add import validation tests
  - [ ] Add basic execution tests with mocks
  - [ ] Add service availability tests

- [ ] **Enhanced Pre-flight Checks**
  - [ ] Check MongoDB index field mappings
  - [ ] Validate embedding dimensions match model
  - [ ] Check for sufficient data in collections
  - [ ] Verify API key permissions/quotas

- [ ] **Sample Improvements**
  - [ ] Add `--dry-run` mode for samples
  - [ ] Add `--verbose` flag for debugging
  - [ ] Standardize output formatting across all samples
  - [ ] Add progress indicators for long-running samples

## 📊 Statistics25/25 (100% complete)
- **Documentation Created**: 3 major files (README + PLAN + changelog)

**Pre-flight Checks by Category:**
- ✅ Wiki samples: 4/4 (100%)
- ✅ RAG samples: 5/5 (100%)
- ✅ Retrieval samples: 2/2 (100%)
- ✅ Readings samples: 2/2 (100%)
- ✅ Crawl4AI samples: 3/3 (100%)
- ✅ Docling samples: 2/2 (100%)
- ✅ Google Drive samples: 3/3 (100%)
- ✅ SearXNG samples: 1/1 (100%)
- ✅ Eval samples: 1/1 (100%)
- ✅ Ingestion validation: 1/1 (100%)
- ⏳ MongoDB utilities: 0/3 (optional - simple diagnostics)
- ✅ YouTube sample: N/A (standalone - no services needed)
- ✅ DarwinXML demo: N/A (demonstration only)
- ✅ Count chunks: N/A (simple utility
- ⏳ Eval samples: Already covered (included in RAG)
- ⏳ MongoDB utilities: 0/3 (optional)
- ⏳ Ingestion validation: 0/1 (optional)
- ⏳ YouTube sample: N/A (standalone)
- ⏳ DarwinXML demo: N/A (standalone)

## 🎯 Next Immediate Actions

1. **Add pre-flight checks to high-priority samples** (wiki, readings, crawl4ai)
2. **Test updated samples** with real services to verify they work
3. **Document any issues** found during testing
4. **Iterate on pre-flight utilities** based on real-world usage

## 📝 Notes

### Design Decisions Made

1. **Pre-flight over fallbacks**: Clear error messages better than mock data or degraded functionality
2. **No pytest tests for samples**: Samples serve as self-documenting validation scripts
3. **Keep EXPORTS as examples**: Show expected output format, just ignore future changes
4. **Path hack for imports**: `sys.path.insert(0, ...)` allows samples to import utils without package installation

### Potential Issues to Watch

1. **Import path complexity**: Samples use relative imports for utils; may need adjustment
2. **Service availability assumptions**: Some samples may fail silently without pre-flight checks
3. **MongoDB index validation**: Need to ensure index field mappings are correct, not just names
4. **API key validation**: Should verify keys work, not just that they're set

### Success Criteria

A sample is considered "working" when:
- ✅ Imports resolve correctly
- ✅ Pre-flight checks catch missing services
- ✅ Error messages are helpful and actionable
- ✅ Script executes correctly with real services
- ✅ Documentation matches actual behavior
- ✅ No cryptic error messages

## 🚀 Implementation Pattern

For each remaining sample, follow this pattern:

1. Read the sample to understand dependencies
2. Add docstring with Usage/Requirements
3. Import pre-flight utilities
4. Call appropriate check functions
5. Print results and exit if failed
6. Continue with original logic
7. Test with real services
8. Update documentation if needed

**Example Template**:
```python
"""Brief description.

Usage:
    uv run python sample/category/script.py [options]

Requirements:
    - MongoDB with indexes
    - LLM API key
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import check_mongodb, check_api_keys, print_pre_flight_results
from mdrag.settings import load_settings

async def main():
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True),
    }
    
    if not print_pre_flight_results(checks):
        return
    
    # Original logic...

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔗 Related Documentation

- **[sample/README.md](sample/README.md)**: Comprehensive setup guide
- **[sample/changelog.md](sample/changelog.md)**: Change history
- **[sample/AGENTS.md](sample/AGENTS.md)**: Sample-specific patterns
- **[AGENTS.md](../AGENTS.md)**: Project guidelines
- **[CLAUDE.md](../CLAUDE.md)**: Development instructions
