# Sample Scripts - Agent Guide

## Purpose
Curated sample and validation scripts grouped by domain.

## Layout
- sample/rag/ - end-to-end and conversational agent checks
- sample/retrieval/ - search and pipeline validation
- sample/ingestion/ - ingestion-related validation utilities
- sample/mongodb/ - cluster and index inspection
- sample/eval/ - gold dataset evaluation

## Run Examples
- uv run python sample/rag/comprehensive_e2e_test.py
- uv run python sample/retrieval/test_search.py
- uv run python sample/ingestion/validate_source_urls.py
- uv run python sample/mongodb/check_indexes.py
- uv run python sample/eval/run_gold_eval.py

## Notes
- These scripts require a configured .env and MongoDB with indexes.
- They are not part of pytest or CI.
