# Logging Instructions

> Source of truth: src/logging/service_logging.py

## Purpose
Use the shared logging service for all runtime logging. It provides:
- `ColoredLogger` with level filtering and correlation ID injection
- Decorators for structured logging
- Safe sanitization for HTTP responses

## Core Usage

### 1) Initialize once at startup
Call `setup_logging()` during app startup/lifespan so the global logger is ready.

### 2) Get a logger
Use `get_logger(__name__)` in modules. It returns the global `ColoredLogger`.

### 3) Async vs sync logging
- In async code, `await logger.info(...)` / `await logger.error(...)`.
- In sync code, use `log_async(logger, "info", "message", **context)`.

### 4) Structured context
Always pass structured fields as keyword args (no secrets). Example fields: `action`, `duration_ms`, `request_id`, `user_email`, `document_id`.

## Decorator Guidance

### Use `log_call` for structured logging
`log_call` wraps function entry/exit, duration, entity extraction, and result processing.

- Provide `LogDecoratorConfig` with:
  - `LambdaEntityExtractor()` to auto-detect entities (workflow, image, document, conversation, calendar).
  - `HTTPResponseProcessor()` when logging HTTP responses.

### Use `log_route_execution` for lightweight route timing
Use in API routes where you want lightweight start/end/error logs without full extractor/processor configuration.

### `log_service` and `log_service_class`
These are no-op decorators that preserve compatibility with integrations or sample scripts. They are safe but do not add structured logging.

## Integration Functions vs Docling Ingestion

### Integration functions (external services)
**Goal**: Structured logs with sanitization and domain entity capture.

- Prefer `log_call` with:
  - `LogDecoratorConfig(entity_extractor=LambdaEntityExtractor(), result_processor=HTTPResponseProcessor())` for HTTP-based integrations.
- For non-HTTP integrations, use `LambdaEntityExtractor()` alone or a custom extractor.
- Keep logs non-blocking and avoid logging payload bodies unless sanitized.
- For sync integration helpers, use `log_async()` to avoid blocking.

**DO**
- Log the external action name and duration.
- Include stable IDs (doc_id, workflow_id, prompt_id).

**DON’T**
- Log API keys, tokens, or raw document content.

### Docling ingestion layer
**Goal**: Minimal, performance-aware logging with chunk-level context.

- Prefer plain logger calls (`await logger.info(...)`) at pipeline boundaries:
  - Document conversion start/finish
  - Chunking start/finish
  - Embedding start/finish
  - Upsert completion
- Avoid `log_call` on tight loops (chunk-level functions) to prevent overhead.
- Use batch summaries instead of per-chunk logs (e.g., chunk counts, total bytes).
- Never log chunk text or full document bodies. Log hashes or counts only.

**DO**
- Log `source_id`, `document_id`, `chunk_count`, `duration_ms`.

**DON’T**
- Log extracted text, embeddings, or frontmatter content.

## Quick Reference

- `setup_logging(log_level="INFO")` — initialize
- `get_logger(__name__)` — get logger
- `await logger.info("message", **context)` — async log
- `log_async(logger, "info", "message", **context)` — sync log
- `log_call(...)` — structured logging with extractors/processors
- `log_route_execution(...)` — light route logging

## Related Files
- src/logging/service_logging.py
- src/logging/context.py (correlation ID)
