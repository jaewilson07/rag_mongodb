# Document Ingestion Design Pattern

## Overview
This document describes how document ingestion works in the MongoDB RAG Agent and captures lessons learned from recent refactors. The pipeline converts raw documents into structured, metadata-rich chunks with embeddings, then persists them using a two-collection pattern for reliable retrieval.

## Goals
- Preserve document context and metadata end-to-end.
- Create structure-aware, search-friendly chunks.
- Avoid duplicate chunk records where possible.
- Keep ingestion resilient (log and continue on conversion errors).

## High-Level Flow
1. **Ingest source**: A document (file, URL, or integration export) is loaded with source metadata.
2. **Convert**: Docling converts the document into a structured representation.
3. **Chunk**: The document is split into `DoclingChunks` (structure-aware chunks).
4. **Embed**: Embeddings are generated for each chunk.
5. **Persist**: Chunks and documents are stored in MongoDB using the two-collection pattern.

## Key Models
### DoclingChunks (Chunk Model)
- `DoclingChunks` is the canonical chunk model.
- It **inherits from `ExtractSource`** and includes the full `MetadataPassport` and `frontmatter`.
- This ensures every chunk carries identifying metadata and provenance.

### ExtractSource and Metadata
- `ExtractSource` captures origin information (e.g., URL or file identity).
- `ExtractDocument` captures derived outputs (e.g., Google Doc tabs) that share a source identity.
- `MetadataPassport` captures structured metadata derived from the document.
- `frontmatter` captures export metadata for integrations.

## Deduplication Strategy
### Current Behavior
- Deduplication uses **upsert on `content_hash`**, derived from the chunk body.
- This prevents *exact* duplicate chunks from being inserted.
- Minor text changes will produce new hashes, which is acceptable for versioned content.

### Optional Source-Identity Deduplication
For stricter identity-based deduplication, a source-level key (such as URL or a stable document ID) can be used as an alternate or additional key. This can reduce duplicates across re-ingestion when content changes slightly.

## Document Identification
To reliably identify documents and chunks:
- Use **source identity** (URL, file path, or integration document ID) when available.
- Preserve **`ExtractSource` fields** across conversion, chunking, and persistence.
- Ensure **`MetadataPassport`** is attached to every chunk for downstream filtering and auditing.

## Intelligent Chunking
For large documents, a structure-aware subset step is used before chunking. This reduces noise and improves chunk quality by prioritizing headings and relevant sections.

See: `sample/docling/chunk_pydantic_sample.py` for a working example of heading-based subsetting before chunking.

## Lessons Learned
- **Keep metadata on every chunk**: Downstream search and tracing depend on it.
- **DoclingChunks is the single source of truth** for chunk shape and semantics.
- **Deduplication should be explicit**: content-hash by default, source-identity optional.
- **Structure-aware subsetting** improves relevance for large documents.

## Touch Points
- Chunking: `src/ingestion/docling/chunker.py`
- Embeddings: `src/ingestion/embedder.py`
- Ingestion pipeline: `src/ingestion/ingest.py`

## Docker Configuration (Project Convention)
- Host ports for local Docker services should live in the 7000–7500 range to avoid conflicts.
- Current compose defaults:
	- MongoDB: host 7017 -> container 27017
	- Mongot (Atlas Search): host 7027 -> container 27027
	- SearXNG: host 7080 -> container 8080
- Use `.env` + `env_file` in compose to centralize configuration and reduce inline env overload.

## See Also

- [Ingestion Pipeline Validation](ingestion-validation.md) - Pre-flight validation for ingestion flows
- [Docker Compose Patterns](docker-compose.md) - Docker configuration conventions

---

_Last updated: 2026-02-09_
