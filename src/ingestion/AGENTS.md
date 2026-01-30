# Ingestion Pipeline (src/ingestion) - Agent Guide

## Technical Stack
- Framework: Docling 2.14+ (document conversion + HybridChunker)
- Language: Python 3.10+
- Key Dependencies:
  - Transformers - tokenizer for HybridChunker
  - OpenAI SDK - embeddings
  - PyMongo 4.10+ - async ingestion writes

## Architecture & Patterns

### File Organization
- ingest.py - end-to-end ingestion pipeline
- chunker.py - Docling HybridChunker wrapper
- embedder.py - batch embeddings for chunks
- init_indexes.py - index initialization helpers (if used)

### Code Examples

✅ DO: Pass DoclingDocument into chunker
- Example in src/ingestion/ingest.py: chunker.chunk_document(..., docling_doc=docling_doc)

❌ DON'T: Pass raw markdown into HybridChunker
- Anti-pattern: chunker.chunk(dl_doc=markdown_text)

### Domain Dictionary
- DoclingDocument: structured document from Docling converter
- DocumentChunk: chunk with metadata and optional embedding
- HybridChunker: token-aware chunking with context

## Service Composition
- Not used in this component.

## Key Files & JIT Search

### Touch Points
- Pipeline: src/ingestion/ingest.py
- Chunking: src/ingestion/chunker.py
- Embeddings: src/ingestion/embedder.py

### Search Commands
- /bin/grep -R "class DoclingHybridChunker" -n src/ingestion
- /bin/grep -R "class EmbeddingGenerator" -n src/ingestion

## Testing & Validation

### Test Command
- uv run python -m src.ingestion.ingest -d ./documents

### Test Strategy
- Unit: chunker output shape and metadata
- Integration: ingest sample documents into MongoDB

### Test Locations
- test_scripts/ (pipeline validation)

## Component Gotchas

1. Audio transcription requires Path objects for Docling.
2. HybridChunker needs DoclingDocument; fallback is last resort.
3. Embeddings must be list[float] for MongoDB vector search.
4. Chunk sizes should respect embedding model token limits.
5. Ingestion is non-destructive by default; use `--clean` to wipe collections.
