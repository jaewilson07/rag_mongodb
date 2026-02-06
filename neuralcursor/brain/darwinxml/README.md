## DarwinXML Integration for NeuralCursor Brain

### Overview

This module bridges the Docling document ingestion pipeline with the NeuralCursor knowledge graph, providing:
- **PARA ontology extraction** from document annotations
- **Entity linking** to Neo4j resource nodes
- **Semantic relationship mapping** between chunks and PARA categories
- **Episodic memory storage** in MongoDB with full Darwin XML metadata

### Components

#### 1. `converter.py` - DarwinXMLConverter

Converts DarwinXML documents to NeuralCursor brain models:

```python
from neuralcursor.brain.darwinxml.converter import DarwinXMLConverter

converter = DarwinXMLConverter()
result = converter.convert_to_neuralcursor(darwin_doc, embedding=embedding_vector)

# Result contains:
# - resource_node: ResourceNode for Neo4j
# - para_nodes: List of extracted Project/Area/Resource/Archive nodes
# - relationships: Graph relationships
# - external_resource: MongoDB ExternalResource document
```

**PARA Category Extraction:**
- Detects `#p/ProjectName` → Creates ProjectNode in Neo4j
- Detects `#a/AreaName` → Creates AreaNode in Neo4j
- Detects `#r/ResourceName` → Tags as resource category
- Detects `#archive` → Creates ArchiveNode in Neo4j

**Entity Extraction:**
- Extracts named entities from DarwinXML attributes
- Creates Entity Resource nodes in Neo4j
- Links documents to entities via REFERENCES relationship

#### 2. `ingestion.py` - DarwinXMLIngestionBridge

Orchestrates ingestion into both Neo4j and MongoDB:

```python
from neuralcursor.brain.darwinxml.ingestion import DarwinXMLIngestionBridge

bridge = DarwinXMLIngestionBridge(
    neo4j_client=neo4j_client,
    mongodb_client=mongodb_client,
)

# Ingest single document
result = await bridge.ingest_darwin_document(darwin_doc, embedding)

# Ingest batch
stats = await bridge.ingest_darwin_documents_batch(darwin_docs, embeddings)
```

**Features:**
- Deduplication by name for PARA nodes
- Automatic entity node creation
- Relationship validation
- Error handling and retry logic

#### 3. Query Methods

**Query by PARA category:**
```python
# Find all resources in a project
resources = await bridge.query_by_para_category(
    category_name="Sellaronda",
    category_type=NodeType.PROJECT,
    limit=20,
)
```

**Query by entity:**
```python
# Find all documents mentioning an entity
resources = await bridge.query_by_entity("Italy", limit=20)
```

### Integration with Existing Pipeline

The DarwinXML bridge works with the existing Docling ingestion pipeline:

```
Documents → Docling Processor → HierarchicalChunker → DarwinXML Wrapper
                                                              ↓
                                                    DarwinXMLValidator
                                                              ↓
                                              DarwinXMLIngestionBridge
                                                       ↙          ↘
                                               Neo4j Graph    MongoDB Content
```

### Usage Example

See `/workspace/neuralcursor/ingest_with_darwin.py` for a complete ingestion script:

```bash
# Ingest directory
python neuralcursor/ingest_with_darwin.py -d ./documents

# Ingest single file
python neuralcursor/ingest_with_darwin.py -d ./documents -f ./documents/planning.md

# With strict validation
python neuralcursor/ingest_with_darwin.py -d ./documents --strict
```

### Data Flow

1. **Document Processing:**
   - Docling converts document to markdown + structure
   - HierarchicalChunker creates semantic chunks

2. **DarwinXML Wrapping:**
   - Chunks wrapped with semantic annotations
   - PARA categories and entities extracted
   - Hierarchical relationships preserved

3. **Validation:**
   - Schema validation (required fields, types)
   - Content validation (non-empty, reasonable length)
   - Relationship validation (no cycles)

4. **Storage:**
   - **Neo4j:** PARA nodes + Resource nodes + Relationships
   - **MongoDB:** Full chunk content + embeddings + Darwin metadata

### Graph Schema

**Nodes:**
- `Project` - PARA projects extracted from `#p/` tags
- `Area` - PARA areas extracted from `#a/` tags
- `Resource` - Document chunks and entities
- `Archive` - Archived items from `#archive` tags

**Relationships:**
- `BELONGS_TO` - Resource → Project/Area
- `REFERENCES` - Resource → Entity
- `CONTAINS` - Parent → Child (hierarchy)
- `RELATES_TO` - Resource → Resource (related chunks)

### MongoDB Schema

Documents stored in `resources` collection:

```python
{
    "resource_id": "chunk-uuid",
    "resource_type": "documentation",
    "title": "Document Title (Chunk 0)",
    "url": "source-url",
    "content": "full chunk text",
    "summary": "AI-generated summary",
    "embedding": [0.1, 0.2, ...],  # 1536-dim vector
    "tags": ["para:project", "neuralcursor", "entity:Italy"],
    "metadata": {
        "chunk_index": 0,
        "darwin_metadata": {...},  # Full DarwinXML structure
        "validation_status": "validated"
    }
}
```

### Query Patterns

**Find all chunks in a project:**
```cypher
MATCH (p:Project {name: 'NeuralCursor'})<-[:BELONGS_TO]-(r:Resource)
RETURN r.name, r.uid
```

**Find documents mentioning an entity:**
```cypher
MATCH (r:Resource)-[:REFERENCES]->(e:Resource {name: 'Italy'})
WHERE 'entity' IN e.tags
RETURN r.name, r.url
```

**Multi-hop reasoning:**
```cypher
MATCH path = (p:Project)-[:CONTAINS*1..3]-(r:Resource)-[:REFERENCES]->(e:Resource)
WHERE p.name = 'NeuralCursor' AND 'entity' IN e.tags
RETURN path
```

### Configuration

Required environment variables (`.env`):

```bash
# Neo4j
NEURALCURSOR_NEO4J_URI=bolt://localhost:7687
NEURALCURSOR_NEO4J_USERNAME=neo4j
NEURALCURSOR_NEO4J_PASSWORD=your_password
NEURALCURSOR_NEO4J_DATABASE=neo4j

# MongoDB
NEURALCURSOR_MONGODB_URI=mongodb://localhost:27017
NEURALCURSOR_MONGODB_DATABASE=neuralcursor

# Embeddings (from src/settings.py)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_openai_key
```

### Future Enhancements

- [ ] Automatic PARA category inference from content
- [ ] Advanced entity resolution with knowledge base
- [ ] Temporal relationship tracking (document evolution)
- [ ] Cross-document entity co-reference resolution
- [ ] GraphRAG query optimization hints
