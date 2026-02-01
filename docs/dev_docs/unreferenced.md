# Unreferenced Files / Code Audit

Date: 2026-01-31

## Scope & Method
- Static pass over imports and direct references (manual grep + directory scan).
- Entry points documented in README and AGENTS were treated as “referenced.”
- “Unreferenced” here means: not imported by runtime code or not mentioned as an entry point.

## Findings

### 1) Source files in src not referenced by runtime imports
- [tests/test_protocol_compliance.py](tests/test_protocol_compliance.py)
  - Status: Not imported by runtime code (pytest-only).
  - Recommendation: Keep under tests/ and ensure pytest discovery includes it.

- [server/maintenance/init_indexes.py](server/maintenance/init_indexes.py)
  - Status: Maintenance script not referenced in README or elsewhere.
  - Recommendation: Document it in README (e.g., “uv run python server/maintenance/init_indexes.py”), or fold index creation into the existing ingestion CLI.

### 2) Example / validation scripts (not part of runtime)
- sample/ (all scripts)
  - Examples:
    - [sample/docling/chunk_pydantic_sample.py](sample/docling/chunk_pydantic_sample.py)
    - [sample/crawl4ai/export_domo_release_notes.py](sample/crawl4ai/export_domo_release_notes.py)
    - [sample/google_drive/single_file/download_single_doc.py](sample/google_drive/single_file/download_single_doc.py)
  - Status: Not imported by runtime code; referenced only as examples in docs/AGENTS.
  - Recommendation: Keep as examples, or convert into documented CLI subcommands under src/cli.py.

- sample/ (validation scripts)
  - Examples:
    - [sample/rag/comprehensive_e2e_test.py](sample/rag/comprehensive_e2e_test.py)
    - [sample/retrieval/test_search.py](sample/retrieval/test_search.py)
    - [sample/retrieval/test_rag_pipeline.py](sample/retrieval/test_rag_pipeline.py)
  - Status: Not included in pytest discovery or CI.
  - Recommendation: Keep as manual smoke scripts and document in README.

### 3) Docs likely not referenced
- [docs/desgin_patterns/document_ingestion.md](docs/desgin_patterns/document_ingestion.md)
  - Status: Located in a misspelled directory; no inbound references were found.
  - Recommendation: Move to docs/design_patterns/ and update links, or remove if it is outdated.

### 4) Generated / local artifacts (should not be tracked)
- [mdrag.egg-info/](mdrag.egg-info/)
- [mdbrag.egg-info/](mdbrag.egg-info/)
- [src/mongodb_rag_agent.egg-info/](src/mongodb_rag_agent.egg-info/)
- [data/__do_not_delete_](data/__do_not_delete_)
- sample/**/EXPORTS/
- .ruff_cache/ and .venv/ (workspace artifacts)

Recommendation: Ensure these are in .gitignore, and delete them from the repository if they were accidentally committed.

## Next Steps (Suggested)
1) Decide whether to keep example/test scripts as-is or integrate them into CLI/tests.
2) Fix the docs/desgin_patterns path (rename + link updates).
3) Remove generated artifacts from version control and update .gitignore if needed.
