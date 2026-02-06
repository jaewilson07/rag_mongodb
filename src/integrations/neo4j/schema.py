"""Neo4j schema definitions and constraints for PARA methodology."""

from typing import List


class PARASchema:
    """
    PARA (Projects, Areas, Resources, Archives) schema for Neo4j.
    
    This schema enforces the organizational structure for the Second Brain,
    ensuring consistent knowledge graph topology.
    """

    @staticmethod
    def get_constraints() -> List[str]:
        """
        Get Cypher queries to create uniqueness constraints.
        
        Returns:
            List of Cypher CREATE CONSTRAINT queries
        """
        return [
            # Project constraints
            "CREATE CONSTRAINT project_uuid IF NOT EXISTS FOR (p:Project) REQUIRE p.uuid IS UNIQUE",
            "CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS NOT NULL",
            # Area constraints
            "CREATE CONSTRAINT area_uuid IF NOT EXISTS FOR (a:Area) REQUIRE a.uuid IS UNIQUE",
            "CREATE CONSTRAINT area_name IF NOT EXISTS FOR (a:Area) REQUIRE a.name IS NOT NULL",
            # Decision constraints
            "CREATE CONSTRAINT decision_uuid IF NOT EXISTS FOR (d:Decision) REQUIRE d.uuid IS UNIQUE",
            "CREATE CONSTRAINT decision_name IF NOT EXISTS FOR (d:Decision) REQUIRE d.name IS NOT NULL",
            # Requirement constraints
            "CREATE CONSTRAINT requirement_uuid IF NOT EXISTS FOR (r:Requirement) REQUIRE r.uuid IS UNIQUE",
            "CREATE CONSTRAINT requirement_name IF NOT EXISTS FOR (r:Requirement) REQUIRE r.name IS NOT NULL",
            # CodeEntity constraints
            "CREATE CONSTRAINT code_entity_uuid IF NOT EXISTS FOR (c:CodeEntity) REQUIRE c.uuid IS UNIQUE",
            "CREATE CONSTRAINT code_entity_path IF NOT EXISTS FOR (c:CodeEntity) REQUIRE c.file_path IS NOT NULL",
            # Resource constraints
            "CREATE CONSTRAINT resource_uuid IF NOT EXISTS FOR (r:Resource) REQUIRE r.uuid IS UNIQUE",
            # Archive constraints
            "CREATE CONSTRAINT archive_uuid IF NOT EXISTS FOR (a:Archive) REQUIRE a.uuid IS UNIQUE",
        ]

    @staticmethod
    def get_indexes() -> List[str]:
        """
        Get Cypher queries to create performance indexes.
        
        Returns:
            List of Cypher CREATE INDEX queries
        """
        return [
            # Text search indexes
            "CREATE TEXT INDEX project_name_text IF NOT EXISTS FOR (p:Project) ON (p.name)",
            "CREATE TEXT INDEX project_description_text IF NOT EXISTS FOR (p:Project) ON (p.description)",
            "CREATE TEXT INDEX decision_rationale_text IF NOT EXISTS FOR (d:Decision) ON (d.rationale)",
            "CREATE TEXT INDEX requirement_description_text IF NOT EXISTS FOR (r:Requirement) ON (r.description)",
            "CREATE TEXT INDEX code_entity_name_text IF NOT EXISTS FOR (c:CodeEntity) ON (c.name)",
            "CREATE TEXT INDEX resource_description_text IF NOT EXISTS FOR (r:Resource) ON (r.description)",
            # Property indexes for filtering
            "CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status)",
            "CREATE INDEX area_active IF NOT EXISTS FOR (a:Area) ON (a.active)",
            "CREATE INDEX requirement_status IF NOT EXISTS FOR (r:Requirement) ON (r.status)",
            "CREATE INDEX requirement_priority IF NOT EXISTS FOR (r:Requirement) ON (r.priority)",
            "CREATE INDEX code_entity_type IF NOT EXISTS FOR (c:CodeEntity) ON (c.entity_type)",
            "CREATE INDEX resource_type IF NOT EXISTS FOR (r:Resource) ON (r.resource_type)",
            # Temporal indexes
            "CREATE INDEX node_created_at IF NOT EXISTS FOR (n) ON (n.created_at)",
            "CREATE INDEX node_updated_at IF NOT EXISTS FOR (n) ON (n.updated_at)",
            # Relationship indexes
            "CREATE INDEX rel_created_at IF NOT EXISTS FOR ()-[r]-() ON (r.created_at)",
        ]

    @staticmethod
    def get_sample_queries() -> dict:
        """
        Get sample Cypher queries for common operations.
        
        Returns:
            Dictionary of query names to Cypher strings
        """
        return {
            "find_project_decisions": """
                MATCH (p:Project {uuid: $project_uuid})-[:HAS_DECISION]->(d:Decision)
                RETURN d
                ORDER BY d.decided_at DESC
            """,
            "find_requirement_dependencies": """
                MATCH path = (r:Requirement {uuid: $requirement_uuid})-[:DEPENDS_ON*1..3]->(dep)
                RETURN path
            """,
            "find_code_entity_decisions": """
                MATCH (c:CodeEntity {uuid: $code_entity_uuid})<-[:IMPLEMENTS]-(d:Decision)
                RETURN d, c
                ORDER BY d.decided_at DESC
            """,
            "find_architectural_path": """
                MATCH path = (req:Requirement)-[:IMPLEMENTS]->(d:Decision)-[:IMPLEMENTS]->(c:CodeEntity)
                WHERE c.file_path = $file_path
                RETURN path
            """,
            "find_resource_inspirations": """
                MATCH (res:Resource)-[:INSPIRED_BY]->(decision:Decision)-[:IMPLEMENTS]->(code:CodeEntity)
                WHERE res.resource_type = 'video'
                RETURN res, decision, code
            """,
            "find_project_context": """
                MATCH (p:Project {uuid: $project_uuid})
                OPTIONAL MATCH (p)-[:HAS_REQUIREMENT]->(req:Requirement)
                OPTIONAL MATCH (p)-[:HAS_DECISION]->(dec:Decision)
                OPTIONAL MATCH (p)-[:CONTAINS]->(code:CodeEntity)
                RETURN p, collect(DISTINCT req) as requirements, 
                       collect(DISTINCT dec) as decisions,
                       collect(DISTINCT code) as code_entities
            """,
            "find_related_projects": """
                MATCH (p1:Project {uuid: $project_uuid})
                MATCH (p1)-[:CONTAINS]->(c1:CodeEntity)-[:DEPENDS_ON]->(c2:CodeEntity)<-[:CONTAINS]-(p2:Project)
                WHERE p1 <> p2
                RETURN DISTINCT p2, count(c2) as shared_dependencies
                ORDER BY shared_dependencies DESC
            """,
            "find_superseded_decisions": """
                MATCH (old:Decision)-[:SUPERSEDES]->(new:Decision)
                WHERE new.uuid = $decision_uuid
                RETURN old
                ORDER BY old.decided_at DESC
            """,
        }

    @staticmethod
    def initialize_schema_script() -> str:
        """
        Get complete initialization script for Neo4j database.
        
        Returns:
            Multi-line Cypher script to initialize database
        """
        constraints = PARASchema.get_constraints()
        indexes = PARASchema.get_indexes()
        
        script = "// Neo4j PARA Schema Initialization\n"
        script += "// Constraints\n"
        script += "\n".join(constraints)
        script += "\n\n// Indexes\n"
        script += "\n".join(indexes)
        
        return script
