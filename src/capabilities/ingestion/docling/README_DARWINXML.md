# DarwinXML Wrapper for Docling Chunks

## Quick Start

### Enable DarwinXML During Ingestion

```bash
# Basic usage
uv run python -m src.ingestion.ingest \
  -d ./documents \
  --enable-darwinxml

# With validation
uv run python -m src.ingestion.ingest \
  -d ./documents \
  --enable-darwinxml \
  --darwinxml-validate \
  --darwinxml-strict
```

### Programmatic Usage

```python
from mdrag.ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from mdrag.ingestion.docling.darwinxml_validator import DarwinXMLValidator
from mdrag.ingestion.docling.darwinxml_storage import DarwinXMLStorage

# Create wrapper
wrapper = DarwinXMLWrapper(
    embedding_model="text-embedding-3-small",
    enable_entity_extraction=True,
    enable_category_tagging=True,
)

# Wrap single chunk
darwin_doc = wrapper.wrap_chunk(
    chunk=docling_chunk,
    document_uid="doc_123",
)

# Wrap batch (preserves hierarchy)
darwin_docs = wrapper.wrap_chunks_batch(
    chunks=docling_chunks,
    document_uid="doc_123",
)

# Validate
validator = DarwinXMLValidator()
result = validator.validate(darwin_doc)

if result.is_valid:
    print("✓ Valid")
else:
    for error in result.errors:
        print(f"✗ {error}")

# Store in MongoDB
storage = DarwinXMLStorage(chunks_collection=db.chunks)
doc_id = await storage.store_darwin_document(
    darwin_doc=darwin_doc,
    embedding=embedding_vector,
)

# Query by tags
results = await storage.query_by_tags(["para:project"])

# Extract graph triples for Neo4j
triples = darwin_doc.extract_graph_triples()
```

## Architecture

```
DoclingChunks → DarwinXMLWrapper → DarwinXMLDocument
                                   ↓
                              DarwinXMLValidator
                                   ↓
                              DarwinXMLStorage
                                   ↓
                            MongoDB + Neo4j
```

## Components

### 1. DarwinXML Models (`darwinxml_models.py`)

Core data structures:
- `DarwinXMLDocument`: Top-level container
- `DarwinAnnotation`: Hierarchical structural elements
- `DarwinAttribute`: Semantic tags (categories, entities, temporal)
- `DarwinRelationship`: Graph edges (parent, child, sibling)
- `ProvenanceMetadata`: Source lineage and validation status

### 2. DarwinXML Wrapper (`darwinxml_wrapper.py`)

Converts DoclingChunks to DarwinXML:
- Automatic annotation extraction
- PARA category tagging (#p/, #a/, #r/, #archive)
- Entity extraction (proper nouns)
- Temporal marker detection (dates, relative times)
- Relationship building (parent-child, siblings)

### 3. Validator (`darwinxml_validator.py`)

Multi-level validation:
- Schema validation (required fields, types)
- Content validation (non-empty, reasonable length)
- Annotation validation (IDs, parent references)
- Provenance validation (metadata completeness)
- Relationship validation (no cycles, valid references)

### 4. Storage (`darwinxml_storage.py`)

MongoDB integration:
- Upsert by content hash
- Semantic queries (by tag, category, entity, status)
- Graph triple extraction
- Validation status management

## Features

### PARA Category Tagging

Automatically detects PARA markers:

```markdown
# Budget #p/Sellaronda
This is a project budget.

## Research #r/Italy
Reference material.
```

**Extracted:**
- Tags: `["para:project", "para:resource"]`
- Attributes: `{"type": "category", "value": "Project:Sellaronda"}`

### Entity Extraction

Identifies proper nouns:

```markdown
The Sellaronda in the Dolomites...
```

**Extracted:**
- Entities: `["Sellaronda", "Dolomites"]`
- Attributes: `{"type": "entity", "value": "Sellaronda", "confidence": 0.8}`

### Hierarchical Relationships

Preserves document structure:

```
Document
  ├─ Chunk 0: "# Overview" (parent: None)
  └─ Chunk 1: "## Details" (parent: Chunk 0)
```

**Relationships:**
- `{"type": "parent", "source_id": "chunk-1", "target_id": "chunk-0"}`

### Graph Triple Extraction

For Neo4j integration:

```python
triples = darwin_doc.extract_graph_triples()

# Example:
{
    "subject": "Trip Planning",
    "predicate": "HAS_CHUNK",
    "object": "chunk-uuid",
    "properties": {"chunk_index": 0}
}
```

## Configuration

### Ingestion Config

```python
from mdrag.ingestion.ingest import IngestionConfig

config = IngestionConfig(
    chunk_size=1000,
    max_tokens=512,
    enable_darwinxml=True,
    darwinxml_validate=True,
    darwinxml_strict=False,
)
```

### Wrapper Options

```python
wrapper = DarwinXMLWrapper(
    embedding_model="text-embedding-3-small",
    processor_version="docling-2.14",
    enable_entity_extraction=True,  # Extract proper nouns
    enable_category_tagging=True,   # Detect PARA tags
)
```

### Validator Options

```python
validator = DarwinXMLValidator(
    strict_mode=False,           # Warnings don't fail validation
    require_annotations=True,    # Require at least one annotation
    require_provenance=True,     # Require complete provenance
)
```

## Success Criteria

✅ **100% Schema Validation**: All ingested chunks pass validation

✅ **Hierarchy Preservation**: Every chunk retains parent information

✅ **<500ms Retrieval**: Agents find correct section via metadata queries

✅ **Semantic Queries**: Query by tag, entity, category return relevant chunks

## Examples

See:
- `/workspace/sample/darwinxml_demo.py` - Full demo script
- `/workspace/docs/darwinxml.md` - Complete documentation
- `/workspace/tests/test_darwinxml.py` - Unit tests

## Neo4j Integration

Extract and store graph triples:

```python
# Extract triples
triples = await storage.get_graph_triples(darwin_doc)

# Create Cypher queries
for triple in triples:
    cypher = f"""
    MERGE (s:Node {{id: $subject}})
    MERGE (o:Node {{id: $object}})
    MERGE (s)-[:{triple['predicate']}]->(o)
    """
```

## MongoDB Schema

DarwinXML documents are stored with this structure:

```python
{
    "chunk_uuid": "uuid",
    "content": "text",
    "embedding": [0.1, 0.2, ...],
    "darwin_metadata": {
        "id": "uuid",
        "schema_version": "1.0",
        "document_title": "Title",
        "annotations": [...],
        "provenance": {...}
    },
    "tags": ["para:project", ...],
    "attributes": [{"type": "entity", "value": "Italy"}],
    "validation_status": "validated"
}
```

## Troubleshooting

### No Annotations Generated

Check:
1. DoclingDocument was passed to chunker (not raw markdown)
2. Document has structure (headings, sections)
3. Content is not empty or whitespace-only

### Validation Failures

```python
result = validator.validate(darwin_doc)

for error in result.errors:
    print(f"Error: {error}")

for warning in result.warnings:
    print(f"Warning: {warning}")
```

### Import Errors

Ensure package is installed:

```bash
uv pip install -e .
```

Or use PYTHONPATH:

```bash
PYTHONPATH=/workspace/src python3 script.py
```

## References

- **Main Documentation**: `/workspace/docs/darwinxml.md`
- **V7 Darwin**: https://www.v7labs.com/darwin
- **PARA Method**: https://fortelabs.com/blog/para/
- **Docling**: https://github.com/DS4SD/docling
