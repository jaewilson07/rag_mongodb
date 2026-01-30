# Test Scripts - Agent Guide

## Technical Stack
- Language: Python 3.10+
- Purpose: ad-hoc validation and E2E checks

## Architecture & Patterns

### File Organization
- test_agent_e2e.py - agent end-to-end checks
- test_rag_pipeline.py - ingestion/search pipeline validation
- test_search.py - search-only checks
- comprehensive_e2e_test.py - full suite

### Code Examples

✅ DO: Run targeted scripts for the area you changed
- Example: use test_search.py after modifying src/tools.py

❌ DON'T: Treat these scripts as unit tests
- They require live MongoDB and external APIs

### Domain Dictionary
- E2E: requires live MongoDB + embedding provider

## Service Composition
- Not used in this component.

## Key Files & JIT Search

### Touch Points
- test_scripts/test_search.py
- test_scripts/comprehensive_e2e_test.py

### Search Commands
- /bin/grep -R "E2E" -n test_scripts

## Testing & Validation

### Test Commands
- uv run python test_scripts/test_search.py
- uv run python test_scripts/comprehensive_e2e_test.py

### Test Strategy
- Smoke: run individual scripts by area
- Full: comprehensive_e2e_test.py before release

## Component Gotchas

1. Scripts require valid .env and MongoDB indexes.
2. Some tests incur API usage costs.
