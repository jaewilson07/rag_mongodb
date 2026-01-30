# Examples (reference-only) - Agent Guide

## Technical Stack
- Language: Python 3.10+
- Purpose: reference patterns only

## Architecture & Patterns

### File Organization
- examples/agent.py - reference agent patterns
- examples/tools.py - reference search tool patterns
- examples/cli.py - reference CLI patterns
- examples/ingestion/ - reference ingestion patterns

### Code Examples

✅ DO: Use examples to understand patterns before editing src/
- Example: compare examples/tools.py with src/tools.py

❌ DON'T: Modify examples/ for production changes
- This folder is reference-only and should remain unchanged

### Domain Dictionary
- Reference implementation: baseline patterns for comparison

## Service Composition
- Not used in this component.

## Key Files & JIT Search

### Touch Points
- examples/agent.py
- examples/tools.py
- examples/ingestion/ingest.py

### Search Commands
- /bin/grep -R "@rag_agent.tool" -n examples

## Testing & Validation

### Test Command
- None (reference-only)

### Test Strategy
- Review-only: do not execute as production tests

## Component Gotchas

1. Examples may be PostgreSQL-specific; do not copy DB code blindly.
2. Keep examples in sync only when explicitly requested.
