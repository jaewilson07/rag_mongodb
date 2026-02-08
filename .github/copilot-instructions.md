# GitHub Copilot Instructions

> Note: This is a summarized version. See [AGENTS.md](../AGENTS.md) as source of truth.

## Workflow
- Use feature branches for new work; avoid committing directly to main.
- Open a PR for any new feature or multi-file change.

## Safety
- Never run destructive commands without explicit confirmation.
- Do not attempt to create Atlas Vector/Search indexes programmatically.
- Never log or commit secrets (.env contents).

## Style
- Keep edits small and targeted; avoid unrelated refactors.
- Prefer existing patterns in src/ before introducing new ones.

## Sample Scripts

When adding new functionality, **always create a sample script** that demonstrates it.

### How to write a sample

1. **Follow the existing style.** Study scripts in `sample/` before writing:
   - Use `argparse` for CLI arguments with sensible defaults.
   - Use `asyncio.run(_run())` as the entry point for async scripts.
   - Include a module docstring with usage examples (3+ `uv run python ...` lines).
   - Print clear, structured output (labels, separators, sections).
   - Wrap service calls in `try/finally` for cleanup.
   - Reference `from mdrag.*` imports for internal modules.

2. **Place in the right directory:**
   - `sample/wiki/` — wiki generation, page streaming, chat
   - `sample/readings/` — save-and-research pipeline (URLs, YouTube)
   - `sample/youtube/` — YouTube extraction, transcripts
   - `sample/crawl4ai/` — web crawling and ingestion
   - `sample/rag/` — RAG query and agent tests
   - `sample/retrieval/` — search pipeline validation
   - `sample/searxng/` — web meta-search
   - `sample/mongodb/` — database inspection
   - `sample/eval/` — evaluation against gold datasets
   - `sample/docling/` — document processing and chunking
   - `sample/google_drive/` — Google Drive integration
   - `sample/ingestion/` — ingestion pipeline utilities

3. **Update the changelog.** After creating or modifying a sample, add or update its entry in [`sample/changelog.md`](../sample/changelog.md). The changelog is the **table of contents** for all samples:
   - Add the script to the correct section table.
   - Include a cross-link: `[folder/script.py](folder/script.py)`
   - Include a one-line description and the `uv run python ...` command.
   - If creating a new section (new domain), add a new `##` heading.

4. **Template:**
   ```python
   """Sample script to <do X>.

   Demonstrates <what pipeline/feature>:
   1. <Step 1>
   2. <Step 2>

   Usage:
       uv run python sample/<folder>/<script>.py
       uv run python sample/<folder>/<script>.py --arg value
   """

   from __future__ import annotations

   import argparse
   import asyncio

   from mdrag.<module> import <Class>

   DEFAULT_VALUE = "<sensible default>"

   def _parse_args() -> argparse.Namespace:
       parser = argparse.ArgumentParser(description="<description>")
       parser.add_argument("--arg", default=DEFAULT_VALUE, help="<help>")
       return parser.parse_args()

   async def _run() -> None:
       args = _parse_args()
       # ... demonstrate the feature ...

   if __name__ == "__main__":
       asyncio.run(_run())
   ```
