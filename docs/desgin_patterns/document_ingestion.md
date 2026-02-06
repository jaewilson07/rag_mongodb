# Document Ingestion Design Pattern

## Overview
This document describes how document ingestion works in the MongoDB RAG Agent and captures lessons learned from recent refactors. The pipeline converts raw documents into structured, metadata-rich chunks with embeddings, then persists them using a two-collection pattern for reliable retrieval.

## Goals
- Preserve document context and metadata end-to-end.
- Create structure-aware, search-friendly chunks.
- Avoid duplicate chunk records where possible.
- Keep ingestion resilient (log and continue on conversion errors).

## High-Level Flow
1. **Collect**: A collector returns `CollectedSource` with `SourceFrontmatter`.
2. **Convert**: Docling converts the source into an `IngestionDocument`.
3. **Chunk**: The document is split into `DoclingChunks` (structure-aware chunks).
4. **Embed**: Embeddings are generated for each chunk.
5. **Persist**: Storage adapters write documents and chunks to MongoDB.

## Key Models
### DoclingChunks (Chunk Model)
- `DoclingChunks` is the canonical chunk model.
- It **inherits from `Source`** and includes the full `MetadataPassport` and `frontmatter`.
- Each chunk carries a `document_uid` to link MongoDB, Neo4j, and Obsidian outputs.

### Source and Metadata
- `CollectedSource` is the standardized collector output.
- `DocumentIdentity` + `Namespace` provide cross-store linkage (`document_uid`).
- `MetadataPassport` is attached to every chunk for citation and tracing.

## Deduplication Strategy
### Current Behavior
- Deduplication uses **upsert on `document_uid`**, derived from source identity + content hash.
- This prevents duplicate documents while keeping versioned content distinct.

### Optional Source-Identity Deduplication
For stricter identity-based deduplication, a source-level key (such as URL or a stable document ID) can be used as an alternate or additional key. This can reduce duplicates across re-ingestion when content changes slightly.

## Document Identification
To reliably identify documents and chunks:
- Use **document_uid** as the canonical cross-store identifier.
- Preserve **source identity** (URL, file path, or integration document ID).
- Ensure **MetadataPassport** is attached to every chunk for downstream filtering and auditing.

## Intelligent Chunking
For large documents, a structure-aware subset step is used before chunking. This reduces noise and improves chunk quality by prioritizing headings and relevant sections.

See: `sample/docling/chunk_pydantic_sample.py` for a working example of heading-based subsetting before chunking.

## Lessons Learned
- **Keep metadata on every chunk**: Downstream search and tracing depend on it.
- **DoclingChunks is the single source of truth** for chunk shape and semantics.
- **Deduplication should be explicit**: content-hash by default, source-identity optional.
- **Structure-aware subsetting** improves relevance for large documents.

## Touch Points
- Collection: `src/ingestion/sources/`
- Processing: `src/ingestion/docling/processor.py`
- Chunking: `src/ingestion/docling/chunker.py`
- Embeddings: `src/ingestion/embedder.py`
- Storage: `src/ingestion/storage.py`

## Docker Configuration (Project Convention)
- Host ports for local Docker services should live in the 7000–7500 range to avoid conflicts.
- Current compose defaults:
	- MongoDB: host 7017 -> container 27017
	- Mongot (Atlas Search): host 7027 -> container 27027
	- SearXNG: host 7080 -> container 8080
- Use `.env` + `env_file` in compose to centralize configuration and reduce inline env overload.
