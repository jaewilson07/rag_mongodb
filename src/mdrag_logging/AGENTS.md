# Logging Layer (src/mdrag_logging) - Agent Guide

## Purpose

Centralized async logging with dc_logger, correlation ID injection, and decorator-based call tracing. Single source of truth for all server logging.

## Architecture

```mermaid
classDiagram
    class get_logger {
        <<function>>
        +name: str
        returns Logger
    }

    class log_call {
        <<decorator>>
        +action_name: str
        note: wraps FastAPI endpoint with timing + error logging
    }

    class log_service_class {
        <<decorator>>
        note: wraps all async methods of a class with logging
    }

    class log_service {
        <<decorator>>
        note: wraps a single async function with timing
    }

    class get_correlation_id {
        <<function>>
        returns str
        note: from contextvars
    }

    log_call --> get_correlation_id : injects
    log_service --> get_correlation_id : injects
    log_service_class --> log_service : applies to methods
```

## Durable Lessons

1. **One logger factory.** Always use `get_logger(__name__)` from this module. Never call `logging.basicConfig()` elsewhere — it creates inconsistent formats.

2. **Correlation IDs tie requests together.** `get_correlation_id()` reads from `contextvars`. Set it once per request (middleware) and every log in the call chain carries it.

3. **Decorators over manual logging.** `@log_call` for API endpoints, `@log_service` for service functions, `@log_service_class` for entire classes. They capture timing, arguments, results, and errors automatically.

4. **Async-native.** dc_logger is async. The logging decorators await log calls. Never use synchronous `logger.info()` in async code paths without `log_async()`.
