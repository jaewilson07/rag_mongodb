# Plan: Getting All Sample Scripts Working

**Created**: February 8, 2026  
**Goal**: Make all 37 sample scripts production-ready with correct imports, pre-flight checks, and full validation against live services.

---

## Executive Summary

Transform the sample/ directory into a reliable, self-documenting collection of working examples. Each sample will validate dependencies before execution and provide clear error messages when services are unavailable.

**Approach**: Incremental implementation with foundation first, then progressive enhancement.

---

## Implementation Status

### ✅ Phase 1: Foundation & Cleanup (COMPLETE)

**Objectives**: Fix inconsistencies, establish patterns, create tooling.

#### Completed Tasks:

1. **Fixed Import Inconsistencies** - 10 files updated
   - Changed `from src.*` to `from mdrag.*` in:
     - Retrieval samples (2)
     - RAG samples (3)
     - Eval samples (1)
     - Ingestion samples (1)
     - MongoDB utilities (3)

2. **Removed Type Ignore Comments** - 4 files cleaned
   - Removed unnecessary `# type: ignore` comments from:
     - `sample/docling/chunk_pydantic_sample.py`
     - `sample/rag/count_chunks.py`
     - `sample/crawl4ai/export_domo_release_notes.py`
     - `sample/searxng/query_searxng.py`

3. **Updated .gitignore**
   - Added `sample/**/EXPORTS/` to prevent tracking generated files

4. **Created Pre-flight Check Utility**
   - New module: `sample/utils/__init__.py`
   - Functions: `check_mongodb()`, `check_redis()`, `check_searxng()`, `check_playwright()`, `check_google_credentials()`, `check_api_keys()`
   - Helpers: `print_service_error()`, `print_pre_flight_results()`

5. **Demonstrated Pre-flight Pattern**
   - Updated `sample/retrieval/test_search.py` as reference implementation

6. **Created Documentation**
   - [sample/README.md](sample/README.md) - Comprehensive setup guide (423 lines)
   - Updated [sample/changelog.md](sample/changelog.md) - Recent changes
   - [sample/IMPLEMENTATION_PROGRESS.md](sample/IMPLEMENTATION_PROGRESS.md) - Detailed progress tracker

**Deliverables**: ✅ All foundation work complete

---

## ✅ Phase 2: Add Pre-flight Checks (COMPLETE)

**Objective**: Add dependency checks to all applicable samples.

### Task Breakdown by Priority

#### High Priority - Multi-Service Dependencies

| Category | Scripts | Services Required | Status |
|----------|---------|-------------------|--------|
| **Wiki** | 4 scripts | MongoDB + LLM | ✅ DONE |
| **Readings** | 2 scripts | MongoDB + Redis + SearXNG + Crawl4AI + LLM | ✅ DONE |
| **Crawl4AI** | 3 scripts | Playwright + MongoDB (some) | ✅ DONE |

#### Medium Priority - Core RAG Functionality

| Category | Scripts | Services Required | Status |
|----------|---------|-------------------|--------|
| **RAG Query** | 4 scripts | MongoDB + indexes + LLM + embeddings | ✅ DONE |
| **Retrieval** | 2 scripts | MongoDB + indexes + embeddings | ✅ DONE |
| **Docling** | 2 scripts | MongoDB + Docling | ✅ DONE |

#### Lower Priority - Simple Dependencies

| Category | Scripts | Services Required | Status |
|----------|---------|-------------------|--------|
| **SearXNG** | 1 script | SearXNG | ✅ DONE |
| **Google Drive** | 3 scripts | Google credentials + MongoDB | ✅ DONE |
| **Eval** | 1 script | MongoDB + LLM | ✅ DONE |
| **Ingestion** | 1 script | MongoDB only | ✅ DONE |

#### Not Needed - Standalone Scripts

| Category | Scripts | Reason | Status |
|----------|---------|--------|--------|
| **MongoDB Utils** | 3 scripts | Simple diagnostics, no checks needed | ✅ N/A |
| **YouTube** | 1 script | No external services (uses yt-dlp) | ✅ N/A |
| **DarwinXML** | 1 script | Demonstration only | ✅ N/A |
| **Count Chunks** | 1 script | Simple utility | ✅ N/A |

### Implementation Pattern

For each sample script:

```python
# 1. Add comprehensive docstring
"""
Brief description of what this sample does.

Usage:
    uv run python sample/category/script.py [options]

Requirements:
    - MongoDB with vector/text indexes
    - LLM API key (if applicable)
    - Embedding API key (if applicable)
    - [Other services as needed]
"""

# 2. Import pre-flight utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import check_mongodb, check_api_keys, print_pre_flight_results
from mdrag.settings import load_settings

# 3. Add checks before main logic
async def main():
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        return  # Exit gracefully with helpful error messages
    
    # Original sample logic continues here...
```

**Progress**: 25/25 samples have pre-flight checks (100%)

**Completed Samples:**
- Wiki: 4/4 (generate_wiki, generate_page, list_projects, chat_wiki)
- RAG: 5/5 (query_rag, comprehensive_e2e_test, test_agent_e2e, additional_tests)
- Retrieval: 2/2 (test_search, test_rag_pipeline)
- Readings: 2/2 (save_url, list_readings)
- Crawl4AI: 3/3 (crawl4ai_ingest, crawl_and_save, export_domo_release_notes)
- Docling: 2/2 (docling_ingest, chunk_pydantic_sample)
- Google Drive: 3/3 (google_drive_ingest, multi_folder download, single_file download)
- SearXNG: 1/1 (query_searxng)
- Eval: 1/1 (run_gold_eval)
- Ingestion: 1/1 (validate_source_urls)

---

## ⏳ Phase 3: Validation & Testing (PENDING)

**Objective**: Verify all samples work with real services.

### Tasks:

1. **Service Setup**
   - [ ] MongoDB Atlas with vector + text indexes
   - [ ] SearXNG via `docker-compose up -d searxng`
   - [ ] Redis via `docker-compose up -d redis`
   - [ ] Playwright: `playwright install`
   - [ ] Google Drive auth (both service account and OAuth)

2. **Category Testing**
   - [ ] Test MongoDB utilities (check_indexes, check_version, check_cluster_info)
   - [ ] Test retrieval scripts (test_search, test_rag_pipeline)
   - [ ] Test RAG scripts (query_rag, test_agent_e2e, comprehensive_e2e_test)
   - [ ] Test wiki scripts (generate_wiki, generate_page, chat_wiki)
   - [ ] Test readings scripts (save_url, list_readings)
   - [ ] Test YouTube script (extract_video)
   - [ ] Test Crawl4AI scripts (all 3)
   - [ ] Test SearXNG script (query_searxng)
   - [ ] Test Docling scripts (docling_ingest, chunk_pydantic_sample)
   - [ ] Test Google Drive scripts (all 3)
   - [ ] Test eval script (run_gold_eval)

3. **Validation Criteria**
   - [ ] Pre-flight checks catch missing services
   - [ ] Error messages are helpful and actionable
   - [ ] Scripts execute correctly with services available
   - [ ] No cryptic error messages
   - [ ] Documentation matches actual behavior

**Progress**: 0% (Phase 2 must complete first)

---

## 🚀 Phase 4: Advanced Improvements (OPTIONAL)

**Objective**: Enhance sample reliability and maintainability.

### Optional Enhancements:

1. **Integration Tests**
   - Create `tests/samples/` directory
   - Import validation tests
   - Basic execution tests with mocked services
   - Service availability tests

2. **Enhanced Checks**
   - Validate MongoDB index field mappings (not just names)
   - Check embedding dimensions match model
   - Verify sufficient data exists in collections
   - Test API key permissions/quotas

3. **User Experience**
   - Add `--dry-run` mode to samples
   - Add `--verbose` flag for debugging
   - Standardize output formatting
   - Add progress indicators for long operations

**Progress**: Not started (optional enhancements)

---

## 📊 Overall Progress

| Metric | Count | Progress |
|--------|-------|----------|
| Total Samples | 37 | 100% |
| Import Fixes | 10/10 | ✅ 100% |
| Type Ignore Removal | 4/4 | ✅ 100% |
| Pre-flight Checks | 25/25 | ✅ 100% |
| Documentation | 4 files | ✅ 100% |
| Validation | 0/12 categories | ⏳ 0% |

**Overall Completion**: ~70% (Phases 1 & 2 complete, Phase 3 pending)

---

## 🎯 Next Steps

### Immediate Actions (Phase 3 - Validation):

1. **Set up test environment** with all services
   - MongoDB Atlas with vector + text indexes
   - SearXNG via docker-compose
   - Redis via docker-compose
   - Playwright browser driver
   - Google Drive authentication (both methods)

2. **Test each sample category systematically**
   - MongoDB utilities
   - Retrieval & RAG scripts
   - Wiki scripts
   - Readings scripts
   - Ingestion scripts (Crawl4AI, Docling, Google Drive)
   - Search & Eval scripts

3. **Document issues and iterate**
   - Flag any broken samples
   - Verify error messages are helpful
   - Update documentation based on real-world testing
   - Confirm setup instructions are accurate

### Optional Actions (Phase 4):

4. **Consider advanced improvements**
   - Integration test suite
   - Enhanced validation checks
   - User experience enhancements

---

## 🔍 Success Criteria

A sample is considered "working" when:

- ✅ Imports resolve correctly (`from mdrag.*`)
- ✅ Pre-flight checks catch missing services
- ✅ Error messages are helpful with setup instructions
- ✅ Script executes correctly with real services
- ✅ Documentation accurately reflects behavior
- ✅ No cryptic or confusing error messages
- ✅ Follows established patterns consistently

---

## 📚 Documentation

### Created Documentation:

1. **[sample/README.md](sample/README.md)**
   - Comprehensive setup guide
   - Service dependency matrix
   - Configuration requirements
   - Sample categories with run commands
   - Pre-flight check examples
   - Troubleshooting guide

2. **[sample/changelog.md](sample/changelog.md)**
   - Recent updates section
   - Complete sample inventory by category
   - Run commands for all samples

3. **[sample/IMPLEMENTATION_PROGRESS.md](sample/IMPLEMENTATION_PROGRESS.md)**
   - Detailed task breakdowns
   - Statistics and metrics
   - Design decisions
   - Implementation patterns

4. **[sample/PLAN.md](sample/PLAN.md)** (this file)
   - High-level plan overview
   - Phase breakdowns
   - Progress tracking
   - Next steps

### Reference Documentation:

- **[AGENTS.md](../AGENTS.md)**: Project behavioral protocols
- **[CLAUDE.md](../CLAUDE.md)**: Development instructions
- **[docs/design_patterns.md](../docs/design_patterns.md)**: Architecture patterns

---

## 🛠️ Tools Created

### Pre-flight Check Utility (`sample/utils/__init__.py`)

Provides reusable functions for dependency validation:

- `check_mongodb(settings)` → Check MongoDB + indexes
- `check_redis(redis_url)` → Check Redis availability
- `check_searxng(searxng_url)` → Check SearXNG availability
- `check_playwright()` → Check Playwright installation
- `check_google_credentials(settings)` → Check Google Drive auth
- `check_api_keys(settings, ...)` → Check LLM/embedding keys
- `print_service_error(...)` → Consistent error formatting
- `print_pre_flight_results(checks)` → Display check summary

**Usage Example**:
```python
from utils import check_mongodb, print_pre_flight_results
from mdrag.settings import load_settings

settings = load_settings()
checks = {"MongoDB": await check_mongodb(settings)}

if not print_pre_flight_results(checks):
    return  # Graceful exit with helpful errors
```

---

## 💡 Key Design Decisions

1. **Pre-flight checks over fallback modes**
   - Clear error messages > mock data or degraded functionality
   - Users know exactly what to fix

2. **No pytest tests for samples**
   - Samples are self-documenting validation scripts
   - Avoid duplication of validation logic

3. **Keep EXPORTS/ as examples**
   - Show expected output format
   - Add to .gitignore to prevent tracking changes

4. **Graceful degradation not needed**
   - Full validation mode only
   - Scripts require their dependencies

---

## 📝 Notes

### Discovered Issues:

1. Some samples used `src.*` imports (now fixed)
2. Type ignore comments were masking import issues (now resolved)
3. No consistent pattern for dependency checking (now standardized)
4. EXPORTS/ directories were being tracked in git (now ignored)

### Lessons Learned:

1. Import consistency is critical for maintainability
2. Pre-flight checks greatly improve user experience
3. Documentation is essential for complex sample collections
4. Standardized patterns make adding samples easier

### Future Considerations:

1. Consider extracting common sample patterns into base classes
2. May need to adjust import strategy if package structure changes
3. Pre-flight checks could be extended with health/performance checks
4. Sample test suite would catch regressions early

---

## 🤝 Contributing

When adding new samples:

1. Follow the implementation pattern above
2. Add pre-flight checks for all dependencies
3. Update [changelog.md](changelog.md) with script entry
4. Test with real services before committing
5. Update [README.md](README.md) if introducing new patterns

---

## 🎉 Summary

**Phase 1 (Foundation)**: ✅ COMPLETE  
**Phase 2 (Pre-flight Checks)**: ✅ COMPLETE (100%, 25/25 samples)  
**Phase 3 (Validation)**: ⏳ PENDING (next priority)  
**Phase 4 (Enhancements)**: ⏳ OPTIONAL

**Next Action**: Move to Phase 3 by setting up test environment and systematically validating all samples with real services.
