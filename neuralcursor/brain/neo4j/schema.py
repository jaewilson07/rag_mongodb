"""
Neo4j schema initialization and validation.

Defines constraints, indexes, and the PARA ontology structure.
"""

from typing import Any

from neo4j import AsyncGraphDatabase, AsyncSession


# Cypher queries for schema initialization
SCHEMA_QUERIES = [
    # === Constraints (Unique IDs) ===
    "CREATE CONSTRAINT project_uid IF NOT EXISTS FOR (p:Project) REQUIRE p.uid IS UNIQUE",
    "CREATE CONSTRAINT area_uid IF NOT EXISTS FOR (a:Area) REQUIRE a.uid IS UNIQUE",
    "CREATE CONSTRAINT resource_uid IF NOT EXISTS FOR (r:Resource) REQUIRE r.uid IS UNIQUE",
    "CREATE CONSTRAINT archive_uid IF NOT EXISTS FOR (ar:Archive) REQUIRE ar.uid IS UNIQUE",
    "CREATE CONSTRAINT decision_uid IF NOT EXISTS FOR (d:Decision) REQUIRE d.uid IS UNIQUE",
    "CREATE CONSTRAINT requirement_uid IF NOT EXISTS FOR (req:Requirement) REQUIRE req.uid IS UNIQUE",
    "CREATE CONSTRAINT code_entity_uid IF NOT EXISTS FOR (ce:CodeEntity) REQUIRE ce.uid IS UNIQUE",
    "CREATE CONSTRAINT file_uid IF NOT EXISTS FOR (f:File) REQUIRE f.uid IS UNIQUE",
    "CREATE CONSTRAINT conversation_uid IF NOT EXISTS FOR (c:Conversation) REQUIRE c.uid IS UNIQUE",
    # === Indexes for Common Queries ===
    "CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status)",
    "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.file_path)",
    "CREATE INDEX code_entity_file IF NOT EXISTS FOR (ce:CodeEntity) ON (ce.file_path)",
    "CREATE INDEX resource_tags IF NOT EXISTS FOR (r:Resource) ON (r.tags)",
    "CREATE INDEX decision_created IF NOT EXISTS FOR (d:Decision) ON (d.created_at)",
    # === Full-text Search Indexes ===
    "CREATE FULLTEXT INDEX node_search IF NOT EXISTS FOR (n:Project|Area|Resource|Archive|Decision|Requirement|CodeEntity|Conversation) ON EACH [n.name, n.description]",
]


async def initialize_schema(driver: Any) -> None:
    """
    Initialize Neo4j schema with constraints and indexes.
    
    Args:
        driver: Neo4j async driver instance
        
    Raises:
        Exception: If schema initialization fails
    """
    async with driver.session() as session:
        for query in SCHEMA_QUERIES:
            try:
                await session.run(query)
            except Exception as e:
                # Some constraints/indexes may already exist, that's okay
                if "already exists" not in str(e).lower():
                    raise


async def validate_schema(driver: Any) -> dict[str, Any]:
    """
    Validate that the schema is properly configured.
    
    Args:
        driver: Neo4j async driver instance
        
    Returns:
        Dictionary with validation results
    """
    async with driver.session() as session:
        # Check constraints
        constraints_result = await session.run("SHOW CONSTRAINTS")
        constraints = [record async for record in constraints_result]

        # Check indexes
        indexes_result = await session.run("SHOW INDEXES")
        indexes = [record async for record in indexes_result]

        # Count nodes by type
        node_counts = {}
        for node_type in [
            "Project",
            "Area",
            "Resource",
            "Archive",
            "Decision",
            "Requirement",
            "CodeEntity",
            "File",
            "Conversation",
        ]:
            count_result = await session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
            record = await count_result.single()
            node_counts[node_type] = record["count"] if record else 0

        # Count relationships
        rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_record = await rel_result.single()
        relationship_count = rel_record["count"] if rel_record else 0

        return {
            "constraints": len(constraints),
            "indexes": len(indexes),
            "node_counts": node_counts,
            "total_nodes": sum(node_counts.values()),
            "total_relationships": relationship_count,
            "schema_valid": len(constraints) >= 9 and len(indexes) >= 6,
        }


async def get_schema_visualization() -> str:
    """
    Generate a Mermaid diagram of the current schema.
    
    Returns:
        Mermaid markdown string
    """
    mermaid = """
graph TB
    %% PARA Methodology
    Project[Project: Goal with Deadline]
    Area[Area: Standard to Maintain]
    Resource[Resource: Reference Material]
    Archive[Archive: Inactive Items]
    
    %% Architectural Entities
    Decision[Decision: Why We Built It]
    Requirement[Requirement: What We Need]
    CodeEntity[CodeEntity: The Actual Code]
    File[File: Tracked Files]
    Conversation[Conversation: Distilled Chats]
    
    %% Relationships
    Project -->|CONTAINS| CodeEntity
    Project -->|IMPLEMENTS| Requirement
    Decision -->|LEADS_TO| Requirement
    Requirement -->|IMPLEMENTED_BY| CodeEntity
    CodeEntity -->|REFERENCES| Resource
    Decision -->|SUPERSEDES| Decision
    CodeEntity -->|DEPENDS_ON| CodeEntity
    File -->|CONTAINS| CodeEntity
    Conversation -->|INSPIRED_BY| Resource
    Conversation -->|RELATES_TO| Decision
    Project -->|BELONGS_TO| Area
    
    %% Archive connections
    Archive -.->|archived_from| Project
    Archive -.->|archived_from| Area
    Archive -.->|archived_from| Resource
    
    style Project fill:#4CAF50
    style Area fill:#2196F3
    style Resource fill:#FF9800
    style Archive fill:#9E9E9E
    style Decision fill:#E91E63
    style Requirement fill:#9C27B0
    style CodeEntity fill:#00BCD4
"""
    return mermaid
