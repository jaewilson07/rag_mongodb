# Server Layer (src/server) - Agent Guide

## Purpose

FastAPI application with REST API endpoints for ingestion, querying, wiki generation, and the save-and-research reading pipeline. All business logic lives in `services/`; routes are thin wrappers.

## Architecture

```mermaid
classDiagram
    class FastAPI_App {
        +lifespan()
        +CORS middleware
    }

    class WikiService {
        +generate_structure() dict
        +stream_page_content() AsyncGenerator
        +stream_chat_response() AsyncGenerator
        +list_projects() list
    }

    class ReadingsService {
        +save_reading(url) dict
        +list_readings() dict
        +get_reading(id) dict
        -_extract_youtube(url) dict
        -_crawl_url(url) dict
        -_generate_summary() dict
        -_research_topic() list
    }

    class QueryAPIService {
        +handle_query(request) QueryResponse
    }

    class IngestJobService {
        +queue_web(url) dict
        +queue_drive(...) dict
        +queue_upload(path) dict
        +get_job(id) JobState
    }

    FastAPI_App --> WikiService : /api/v1/wiki/*
    FastAPI_App --> ReadingsService : /api/v1/readings/*
    FastAPI_App --> QueryAPIService : /api/v1/query
    FastAPI_App --> IngestJobService : /api/v1/ingest/*
```

## API Route Map

```mermaid
flowchart LR
    subgraph Wiki
        WS[POST /wiki/structure]
        WG[POST /wiki/generate]
        WC[POST /wiki/chat]
        WP[GET /wiki/projects]
    end

    subgraph Readings
        RS[POST /readings/save]
        RL[GET /readings]
        RD[GET /readings/:id]
    end

    subgraph Ingestion
        IW[POST /ingest/web]
        ID[POST /ingest/drive]
        IU[POST /ingest/upload]
        IJ[GET /jobs/:id]
    end

    subgraph Query
        QQ[POST /query]
    end

    subgraph Health
        HH[GET /health]
    end

    WS --> WikiService
    WG --> WikiService
    WC --> WikiService
    RS --> ReadingsService
    QQ --> QueryAPIService
    IW --> IngestJobService
```

## Services Detail

### WikiService
Generates structured wikis from ingested data. Discovers documents in MongoDB, uses LLM to organize into sections/pages, streams page content via RAG (hybrid search → LLM).

### ReadingsService
Save-and-research pipeline (Wallabag/Instapaper style). Auto-detects YouTube URLs. Pipeline: crawl/extract → LLM summary → SearXNG research → MongoDB store → RAG ingestion queue. **Validation**: Runs `validate_readings(settings, url_type, searxng_url=...)` at start of `save_reading`; validates MongoDB, Redis, LLM API, plus Playwright/SearXNG (web) or yt-dlp/youtube-transcript-api (YouTube). Raises `ValidationError` on failure. See [docs/design-patterns/ingestion-validation.md](../../docs/design-patterns/ingestion-validation.md).

### QueryAPIService
Grounded RAG query with citations. Delegates to `QueryService` which runs search → generation → grounding verification → trace storage.

### IngestJobService
Job queue via Redis/RQ. Queues ingestion work for async processing. Jobs transition through PENDING → STARTED → FINISHED/FAILED. **Validation**: Queue-based flows (ReadingsService, API ingest) require Redis + at least one RQ worker listening to `default`. Run `uv run rq worker default --url redis://localhost:6379/0` in a separate terminal.

## Durable Lessons

1. **Routes are thin, services are fat.** Every router file is under 60 lines. All logic lives in `services/`. This keeps routing testable and logic reusable.

2. **Streaming via `StreamingResponse`.** Wiki page generation and chat both use FastAPI's `StreamingResponse` with async generators. This gives the frontend real-time token streaming.

3. **CORS is configured for the frontend.** Origins `localhost:3000` and `127.0.0.1:3000` are allowed. Update when deploying to production.

4. **Lifespan validation.** The `lifespan` context manager pings MongoDB at startup and fails fast if the database is unreachable. Don't remove this.

5. **API versioning via prefix.** All routes use `/api/v1/` prefix from `APIConfig`. When v2 arrives, add new routers without breaking existing clients.

6. **Media-type routing in ReadingsService.** `is_youtube_url()` at the top of `save_reading()` routes to the YouTube extraction pipeline. Add new media detectors here (podcasts, PDFs, etc.).

7. **ReadingsService validation.** Validation runs before extraction; URL type determines collector-specific checks (Playwright for web, yt-dlp for YouTube). Don't skip validation—callers must handle `ValidationError` (API returns 500, samples exit 1).
