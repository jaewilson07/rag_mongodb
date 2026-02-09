# Design Patterns for MongoDB RAG Agent

This directory contains design patterns and architectural guidelines for the MongoDB RAG Agent project. Each pattern document focuses on a specific aspect of the system architecture.

## Pattern Documents

### [Docker Compose Patterns](docker-compose.md)
Configuration patterns for Docker Compose, including:
- Service port mapping (7000-7500 range convention)
- Environment variable management
- Service dependencies and health checks
- Conflict avoidance strategies
- Best practices for multi-service orchestration

### [Ingestion Pipeline Validation](ingestion-validation.md)
Validation architecture for the document ingestion pipeline:
- Core validation checks (MongoDB, Redis, Embedding API)
- Collector-specific validation (Crawl4AI, Google Drive, YouTube)
- Validation matrix by entry point
- ReadingsService validation patterns
- Error message formatting standards

### [Document Ingestion](document_ingestion.md)
End-to-end document ingestion flow:
- Docling conversion pipeline
- Structure-aware chunking with DoclingChunks
- Metadata preservation (ExtractSource, MetadataPassport)
- Deduplication strategies
- Two-collection persistence pattern
- Lessons learned and best practices

## Navigation

For behavioral protocols and development guidelines, see:
- [AGENTS.md](../../AGENTS.md) - Agent behavioral protocols and tech stack
- [CLAUDE.md](../../CLAUDE.md) - Development instructions and patterns
- [README.md](../../README.md) - Project overview and quick start

## Contributing

When adding new design patterns:
1. Create a descriptive markdown file in this directory
2. Add an entry to this README with a brief summary
3. Update references in relevant AGENTS.md files
4. Include diagrams (Mermaid preferred) for complex architectures
5. Add "Last updated" date at the bottom of the file

---

_Last updated: 2026-02-09_
