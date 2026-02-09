"""MemGPT system tools for interacting with Second Brain."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.memory_gateway.gateway import MemoryGateway
from src.memory_gateway.models import (
    MemoryRequest,
    MemoryType,
    MemoryOperation,
    ArchitecturalQuery,
)
from src.integrations.neo4j.models import (
    Decision,
    Requirement,
    CodeEntity,
    Resource,
    NodeType,
    RelationType,
)

logger = logging.getLogger(__name__)


class MemoryTools:
    """
    MemGPT system tools for Second Brain operations.
    
    These tools are registered with MemGPT to allow it to:
    - Save architectural decisions to Neo4j
    - Query the knowledge graph
    - Store episodic memories in MongoDB
    - Manage the Working Set
    """

    def __init__(self, memory_gateway: MemoryGateway):
        """
        Initialize memory tools.
        
        Args:
            memory_gateway: Memory gateway instance
        """
        self.gateway = memory_gateway

    async def save_decision(
        self,
        name: str,
        rationale: str,
        context: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        consequences: Optional[List[str]] = None,
        project_uuid: Optional[str] = None,
    ) -> str:
        """
        Save an architectural decision to the knowledge graph.
        
        Args:
            name: Decision name
            rationale: Why this decision was made
            context: Additional context
            alternatives: Alternative approaches considered
            consequences: Known consequences
            project_uuid: Associated project UUID
            
        Returns:
            Decision UUID
        """
        decision = Decision(
            name=name,
            rationale=rationale,
            description=context,
            alternatives_considered=alternatives or [],
            consequences=consequences or [],
        )
        
        request = MemoryRequest(
            operation=MemoryOperation.CREATE,
            memory_type=MemoryType.STRUCTURAL,
            entity_type=NodeType.DECISION,
            data=decision.model_dump(),
        )
        
        response = await self.gateway.execute(request)
        
        if response.success:
            decision_uuid = response.data
            logger.info("memgpt_decision_saved", extra={"uuid": decision_uuid})
            
            # Link to project if provided
            if project_uuid:
                await self.gateway.neo4j_client.create_relationship(
                    project_uuid,
                    decision_uuid,
                    RelationType.HAS_DECISION,
                )
            
            return decision_uuid
        else:
            logger.error("memgpt_decision_save_failed", extra={"error": response.error})
            raise RuntimeError(f"Failed to save decision: {response.error}")

    async def save_requirement(
        self,
        name: str,
        description: str,
        requirement_type: str = "functional",
        priority: str = "medium",
        acceptance_criteria: Optional[List[str]] = None,
        project_uuid: Optional[str] = None,
    ) -> str:
        """
        Save a requirement to the knowledge graph.
        
        Args:
            name: Requirement name
            description: Requirement description
            requirement_type: functional, non-functional, constraint
            priority: low, medium, high, critical
            acceptance_criteria: List of acceptance criteria
            project_uuid: Associated project UUID
            
        Returns:
            Requirement UUID
        """
        requirement = Requirement(
            name=name,
            description=description,
            requirement_type=requirement_type,
            priority=priority,
            acceptance_criteria=acceptance_criteria or [],
        )
        
        request = MemoryRequest(
            operation=MemoryOperation.CREATE,
            memory_type=MemoryType.STRUCTURAL,
            entity_type=NodeType.REQUIREMENT,
            data=requirement.model_dump(),
        )
        
        response = await self.gateway.execute(request)
        
        if response.success:
            req_uuid = response.data
            logger.info("memgpt_requirement_saved", extra={"uuid": req_uuid})
            
            # Link to project if provided
            if project_uuid:
                await self.gateway.neo4j_client.create_relationship(
                    project_uuid,
                    req_uuid,
                    RelationType.HAS_REQUIREMENT,
                )
            
            return req_uuid
        else:
            raise RuntimeError(f"Failed to save requirement: {response.error}")

    async def save_code_entity(
        self,
        name: str,
        entity_type: str,
        file_path: str,
        line_number: Optional[int] = None,
        description: Optional[str] = None,
        code_snippet: Optional[str] = None,
        decision_uuid: Optional[str] = None,
    ) -> str:
        """
        Save a code entity to the knowledge graph.
        
        Args:
            name: Entity name (function/class name)
            entity_type: function, class, module, file
            file_path: File path
            line_number: Starting line number
            description: Entity description
            code_snippet: Actual code
            decision_uuid: Associated decision UUID
            
        Returns:
            Code entity UUID
        """
        code_entity = CodeEntity(
            name=name,
            entity_type=entity_type,
            file_path=file_path,
            line_number=line_number,
            description=description,
            code_snippet=code_snippet,
        )
        
        request = MemoryRequest(
            operation=MemoryOperation.CREATE,
            memory_type=MemoryType.STRUCTURAL,
            entity_type=NodeType.CODE_ENTITY,
            data=code_entity.model_dump(),
        )
        
        response = await self.gateway.execute(request)
        
        if response.success:
            entity_uuid = response.data
            logger.info("memgpt_code_entity_saved", extra={"uuid": entity_uuid})
            
            # Link to decision if provided
            if decision_uuid:
                await self.gateway.neo4j_client.create_relationship(
                    decision_uuid,
                    entity_uuid,
                    RelationType.IMPLEMENTS,
                )
            
            return entity_uuid
        else:
            raise RuntimeError(f"Failed to save code entity: {response.error}")

    async def save_resource(
        self,
        name: str,
        resource_type: str,
        url: Optional[str] = None,
        description: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        mongodb_ref: Optional[str] = None,
        inspired_decision: Optional[str] = None,
    ) -> str:
        """
        Save an external resource (video, article, etc.) to the knowledge graph.
        
        Args:
            name: Resource name
            resource_type: url, document, video, paper, book, tutorial
            url: Resource URL
            description: Resource description
            key_points: Key takeaways
            mongodb_ref: Reference to MongoDB document_id
            inspired_decision: Decision UUID that this resource inspired
            
        Returns:
            Resource UUID
        """
        resource = Resource(
            name=name,
            resource_type=resource_type,
            url=url,
            description=description,
            key_points=key_points or [],
            mongodb_ref=mongodb_ref,
        )
        
        request = MemoryRequest(
            operation=MemoryOperation.CREATE,
            memory_type=MemoryType.STRUCTURAL,
            entity_type=NodeType.RESOURCE,
            data=resource.model_dump(),
        )
        
        response = await self.gateway.execute(request)
        
        if response.success:
            resource_uuid = response.data
            logger.info("memgpt_resource_saved", extra={"uuid": resource_uuid})
            
            # Link to decision if provided
            if inspired_decision:
                await self.gateway.neo4j_client.create_relationship(
                    resource_uuid,
                    inspired_decision,
                    RelationType.INSPIRED_BY,
                )
            
            return resource_uuid
        else:
            raise RuntimeError(f"Failed to save resource: {response.error}")

    async def query_why_code_exists(
        self, file_path: str, line_number: Optional[int] = None
    ) -> str:
        """
        Query why specific code exists.
        
        This is the signature Second Brain query.
        
        Args:
            file_path: File path to query
            line_number: Optional line number
            
        Returns:
            Human-readable explanation
        """
        query = ArchitecturalQuery(
            file_path=file_path,
            line_number=line_number,
            include_history=True,
            include_resources=True,
        )
        
        context = await self.gateway.get_architectural_context(query)
        
        # Format response
        explanation = [f"# Architectural Context for {file_path}"]
        
        if context.decisions:
            explanation.append("\n## Decisions:")
            for dec in context.decisions:
                explanation.append(f"- **{dec.get('name')}**: {dec.get('rationale')}")
        
        if context.requirements:
            explanation.append("\n## Requirements:")
            for req in context.requirements:
                explanation.append(f"- {req.get('name')}: {req.get('description')}")
        
        if context.resources:
            explanation.append("\n## Inspirations:")
            for res in context.resources:
                explanation.append(f"- {res.get('name')} ({res.get('resource_type')}): {res.get('url')}")
        
        if not context.decisions and not context.requirements:
            explanation.append("\nNo architectural context found. This code may need documentation.")
        
        return "\n".join(explanation)

    async def get_active_projects(self) -> str:
        """
        Get list of active projects from working set.
        
        Returns:
            Formatted list of active projects
        """
        working_set = await self.gateway.get_working_set()
        
        if not working_set.active_projects:
            return "No active projects in working set."
        
        output = ["# Active Projects:"]
        for project_uuid in working_set.active_projects:
            node = await self.gateway.neo4j_client.get_node(project_uuid, NodeType.PROJECT)
            if node:
                output.append(f"- **{node.get('name')}**: {node.get('description', 'No description')}")
        
        return "\n".join(output)

    async def save_episodic_memory(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save an episodic memory to MongoDB.
        
        Args:
            content: Memory content
            metadata: Additional metadata
            
        Returns:
            MongoDB document ID
        """
        data = {
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        request = MemoryRequest(
            operation=MemoryOperation.CREATE,
            memory_type=MemoryType.EPISODIC,
            entity_type="episodic_memories",
            data=data,
        )
        
        response = await self.gateway.execute(request)
        
        if response.success:
            logger.info("memgpt_episodic_saved", extra={"id": response.data["inserted_id"]})
            return response.data["inserted_id"]
        else:
            raise RuntimeError(f"Failed to save episodic memory: {response.error}")
