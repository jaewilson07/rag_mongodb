# Config Layer (src/config)

## Purpose

Bootstrap configuration: Pydantic Settings, env loading, and config validation entry point. No runtime business logic.

## Architecture

### Class Overview

```mermaid
classDiagram
    class Settings {
        +str mongodb_uri
        +str mongodb_host
        +int mongodb_port
        +str mongodb_database
        +str mongodb_collection_documents
        +str mongodb_collection_chunks
        +str mongodb_vector_index
        +str mongodb_text_index
        +str mongodb_connection_string
        +int default_match_count
        +int max_match_count
        +... llm, embedding, redis fields
    }

    class ConfigError {
        +str message
        +Exception original_error
    }

    MDRAGException <|-- ConfigError
```

### Process Flow

```mermaid
flowchart LR
    A[.env] --> B[load_dotenv]
    B --> C[Settings]
    C --> D[load_settings]
    D --> E[validate_config]
```

## Key Files

| File | Contents |
|------|----------|
| `settings.py` | `Settings` (BaseSettings), `load_settings()` |
| `validate_config.py` | Entry point: `uv run python -m mdrag.config.validate_config` |
| `exceptions.py` | `ConfigError` (subclasses `MDRAGException`) |

## Commands

```bash
# Validate config (MongoDB connection, env vars)
uv run python -m mdrag.config.validate_config
```

## Patterns

- **DO**: Use `load_settings()` for runtime config; avoid ad-hoc env reads.
- **DO**: Add new config fields to `Settings` with `Field(description=...)`.
- **DON'T**: Hardcode connection strings; use `Settings.mongodb_connection_string`.

## JIT Search

```
rg "class Settings" src/config
rg "load_settings" src
```
