"""Pre-built Cypher queries for common Second Brain operations."""

from typing import Optional, Dict, Any


class SecondBrainQueries:
    """
    Collection of Cypher queries for NeuralCursor Second Brain operations.
    
    These queries implement the core "Architectural Intuition" functionality:
    - Multi-hop relationship traversal
    - Context discovery
    - Decision history tracking
    - Cross-project pattern matching
    """

    @staticmethod
    def find_why_code_exists(file_path: str, line_number: Optional[int] = None) -> tuple[str, Dict[str, Any]]:
        """
        Find the architectural reasoning behind a specific code entity.
        
        This is the signature query: "Why does this code exist?"
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH path = (req:Requirement)-[:IMPLEMENTS]->(dec:Decision)-[:IMPLEMENTS]->(code:CodeEntity)
        WHERE code.file_path = $file_path
        """
        
        if line_number is not None:
            query += " AND code.line_number <= $line_number AND (code.line_number + 50) >= $line_number"
        
        query += """
        OPTIONAL MATCH (dec)-[:SUPERSEDES]->(old_dec:Decision)
        OPTIONAL MATCH (dec)<-[:INSPIRED_BY]-(res:Resource)
        RETURN path, collect(DISTINCT old_dec) as superseded_decisions, collect(DISTINCT res) as inspirations
        ORDER BY dec.decided_at DESC
        LIMIT 5
        """
        
        params = {"file_path": file_path}
        if line_number is not None:
            params["line_number"] = line_number
            
        return query, params

    @staticmethod
    def find_project_context(project_uuid: str) -> tuple[str, Dict[str, Any]]:
        """
        Get complete context for a project including all related entities.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (p:Project {uuid: $project_uuid})
        OPTIONAL MATCH (p)-[:HAS_REQUIREMENT]->(req:Requirement)
        OPTIONAL MATCH (p)-[:HAS_DECISION]->(dec:Decision)
        OPTIONAL MATCH (p)-[:CONTAINS]->(code:CodeEntity)
        OPTIONAL MATCH (p)-[:REFERENCES]->(res:Resource)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(area:Area)
        
        RETURN p,
               collect(DISTINCT req) as requirements,
               collect(DISTINCT dec) as decisions,
               collect(DISTINCT code) as code_entities,
               collect(DISTINCT res) as resources,
               collect(DISTINCT area) as areas
        """
        
        return query, {"project_uuid": project_uuid}

    @staticmethod
    def find_active_project_files() -> tuple[str, Dict[str, Any]]:
        """
        Get all files associated with active projects.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (p:Project {status: 'active'})-[:CONTAINS]->(code:CodeEntity)
        RETURN DISTINCT code.file_path as file_path,
               p.name as project_name,
               p.uuid as project_uuid,
               code.updated_at as last_updated
        ORDER BY code.updated_at DESC
        """
        
        return query, {}

    @staticmethod
    def find_decision_history(code_entity_uuid: str) -> tuple[str, Dict[str, Any]]:
        """
        Get the decision history for a specific code entity.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (code:CodeEntity {uuid: $code_entity_uuid})<-[:IMPLEMENTS]-(dec:Decision)
        OPTIONAL MATCH (dec)-[:SUPERSEDES*]->(old_dec:Decision)
        OPTIONAL MATCH (dec)<-[:INSPIRED_BY]-(res:Resource)
        
        RETURN dec,
               collect(DISTINCT old_dec) as previous_decisions,
               collect(DISTINCT res) as inspirations
        ORDER BY dec.decided_at DESC
        """
        
        return query, {"code_entity_uuid": code_entity_uuid}

    @staticmethod
    def find_cross_project_patterns(
        entity_type: str = "function", min_usage: int = 2
    ) -> tuple[str, Dict[str, Any]]:
        """
        Find code entities used across multiple projects.
        
        Args:
            entity_type: Type of code entity (function, class, module)
            min_usage: Minimum number of projects using this pattern
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (code:CodeEntity {entity_type: $entity_type})
        MATCH (p:Project)-[:CONTAINS]->(code)
        WITH code, collect(DISTINCT p) as projects
        WHERE size(projects) >= $min_usage
        RETURN code.name as entity_name,
               code.file_path as file_path,
               projects,
               size(projects) as usage_count
        ORDER BY usage_count DESC
        """
        
        return query, {"entity_type": entity_type, "min_usage": min_usage}

    @staticmethod
    def find_related_resources(decision_uuid: str) -> tuple[str, Dict[str, Any]]:
        """
        Find all resources (videos, docs, etc.) that inspired a decision.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (dec:Decision {uuid: $decision_uuid})
        MATCH (res:Resource)-[:INSPIRED_BY]->(dec)
        RETURN res.resource_type as type,
               res.name as name,
               res.url as url,
               res.key_points as key_points,
               res.created_at as discovered_at
        ORDER BY res.created_at DESC
        """
        
        return query, {"decision_uuid": decision_uuid}

    @staticmethod
    def find_architectural_conflicts(file_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Find potential conflicts between current code and requirements.
        
        This query helps detect "contextual drift" where code deviates
        from stated requirements or decisions.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (code:CodeEntity {file_path: $file_path})
        MATCH (code)<-[:IMPLEMENTS]-(dec:Decision)
        MATCH (req:Requirement)-[:IMPLEMENTS]->(dec)
        
        WHERE req.status IN ['accepted', 'implemented']
        
        RETURN code.name as code_entity,
               dec.name as decision,
               dec.rationale as decision_rationale,
               req.name as requirement,
               req.acceptance_criteria as acceptance_criteria,
               req.priority as priority
        """
        
        return query, {"file_path": file_path}

    @staticmethod
    def find_dependency_chain(code_entity_uuid: str, max_depth: int = 3) -> tuple[str, Dict[str, Any]]:
        """
        Find the full dependency chain for a code entity.
        
        Args:
            code_entity_uuid: Starting code entity
            max_depth: Maximum depth to traverse
            
        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
        MATCH path = (code:CodeEntity {{uuid: $code_entity_uuid}})-[:DEPENDS_ON*1..{max_depth}]->(dep:CodeEntity)
        RETURN path,
               length(path) as depth,
               dep.name as dependency_name,
               dep.file_path as dependency_path
        ORDER BY depth
        """
        
        return query, {"code_entity_uuid": code_entity_uuid}

    @staticmethod
    def search_graph_semantic(
        search_text: str, node_types: Optional[list[str]] = None, limit: int = 10
    ) -> tuple[str, Dict[str, Any]]:
        """
        Semantic text search across graph nodes.
        
        Args:
            search_text: Text to search for
            node_types: Optional list of node types to filter
            limit: Maximum results
            
        Returns:
            Tuple of (query, parameters)
        """
        label_filter = ""
        if node_types:
            labels = "|".join(node_types)
            label_filter = f":{labels}"
        
        query = f"""
        CALL db.index.fulltext.queryNodes('node_search', $search_text)
        YIELD node, score
        WHERE node{label_filter}
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        return query, {"search_text": search_text, "limit": limit}

    @staticmethod
    def find_stale_decisions(days_threshold: int = 90) -> tuple[str, Dict[str, Any]]:
        """
        Find decisions that haven't been updated in a long time.
        
        Args:
            days_threshold: Number of days to consider stale
            
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (dec:Decision)
        WHERE duration.between(datetime(dec.updated_at), datetime()).days > $days_threshold
        OPTIONAL MATCH (dec)-[:IMPLEMENTS]->(code:CodeEntity)
        RETURN dec.uuid as uuid,
               dec.name as name,
               dec.decided_at as decided_at,
               dec.updated_at as last_updated,
               count(code) as affected_code_count
        ORDER BY dec.updated_at ASC
        """
        
        return query, {"days_threshold": days_threshold}

    @staticmethod
    def archive_completed_project(project_uuid: str) -> tuple[str, Dict[str, Any]]:
        """
        Archive a completed project while preserving relationships.
        
        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (p:Project {uuid: $project_uuid})
        SET p.status = 'archived', p:Archive
        WITH p
        MATCH (p)-[:CONTAINS]->(code:CodeEntity)
        SET code:Archive
        RETURN p, collect(code) as archived_code
        """
        
        return query, {"project_uuid": project_uuid}
