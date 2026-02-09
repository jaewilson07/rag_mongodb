"""Knowledge distiller for extracting structured entities from text."""

import logging
from typing import List, Dict, Any, Optional
import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.settings import Settings
from src.memory_gateway.gateway import MemoryGateway
from src.memory_gateway.models import MemoryRequest, MemoryType, MemoryOperation
from src.integrations.neo4j.models import (
    Decision,
    Requirement,
    CodeEntity,
    Resource,
    NodeType,
)

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    """
    Extracts structured knowledge from unstructured text.
    
    Uses LLM to identify:
    - Architectural decisions and rationale
    - Requirements and acceptance criteria
    - Code entities and their purpose
    - External resources and their relevance
    """

    def __init__(self, settings: Settings, memory_gateway: MemoryGateway):
        """
        Initialize knowledge distiller.
        
        Args:
            settings: Application settings
            memory_gateway: Memory gateway instance
        """
        self.settings = settings
        self.gateway = memory_gateway
        
        from mdrag.llm.completion_client import get_llm_init_kwargs
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            **get_llm_init_kwargs(settings),
        )

    async def extract_entities_from_text(
        self, text: str
    ) -> List[Dict[str, Any]]:
        """
        Extract structured entities from text.
        
        Args:
            text: Raw text to analyze
            
        Returns:
            List of extracted entities
        """
        system_prompt = """You are an expert at extracting architectural knowledge from conversations and notes.

Your task is to identify:

1. **Decisions**: Architectural or design choices made
   - Name: Short title
   - Rationale: Why this was chosen
   - Alternatives: Other options considered
   - Consequences: Known impacts

2. **Requirements**: Functional or non-functional needs
   - Name: Short title
   - Description: What is needed
   - Type: functional, non-functional, constraint
   - Priority: low, medium, high, critical
   - Acceptance criteria: How to verify

3. **Code Entities**: Specific code discussed
   - Name: Function/class/file name
   - Type: function, class, module, file
   - File path: Location
   - Description: Purpose

4. **Resources**: External references
   - Name: Title
   - Type: video, article, paper, tutorial
   - URL: Link if mentioned
   - Key points: Important takeaways

Return your analysis as a JSON array of entities. Each entity should have:
```json
{
  "entity_type": "decision|requirement|code_entity|resource",
  "name": "...",
  "description": "...",
  "metadata": { /* entity-specific fields */ }
}
```

If no entities are found, return an empty array: []

Be precise. Only extract entities that are explicitly discussed or decided.
"""

        user_prompt = f"""Analyze this text and extract structured entities:

---
{text[:4000]}  # Limit text length
---

Return JSON array of entities."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON from response
            content = response.content
            
            # Try to extract JSON array
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                entities = json.loads(json_match.group())
                logger.info(
                    "distiller_entities_extracted",
                    extra={"count": len(entities)},
                )
                return entities
            else:
                logger.warning("distiller_no_json_found")
                return []
                
        except Exception as e:
            logger.exception("distiller_extraction_failed", extra={"error": str(e)})
            return []

    async def create_graph_node(self, entity: Dict[str, Any]) -> Optional[str]:
        """
        Create a graph node from extracted entity.
        
        Args:
            entity: Extracted entity dictionary
            
        Returns:
            Node UUID or None if creation failed
        """
        entity_type = entity.get("entity_type")
        name = entity.get("name")
        description = entity.get("description")
        metadata = entity.get("metadata", {})
        
        if not entity_type or not name:
            logger.warning(
                "distiller_invalid_entity",
                extra={"entity": entity},
            )
            return None
        
        try:
            if entity_type == "decision":
                node = Decision(
                    name=name,
                    description=description,
                    rationale=metadata.get("rationale", ""),
                    alternatives_considered=metadata.get("alternatives", []),
                    consequences=metadata.get("consequences", []),
                )
                node_type = NodeType.DECISION
                
            elif entity_type == "requirement":
                node = Requirement(
                    name=name,
                    description=description,
                    requirement_type=metadata.get("type", "functional"),
                    priority=metadata.get("priority", "medium"),
                    acceptance_criteria=metadata.get("acceptance_criteria", []),
                )
                node_type = NodeType.REQUIREMENT
                
            elif entity_type == "code_entity":
                node = CodeEntity(
                    name=name,
                    description=description,
                    entity_type=metadata.get("type", "function"),
                    file_path=metadata.get("file_path", "unknown"),
                    line_number=metadata.get("line_number"),
                )
                node_type = NodeType.CODE_ENTITY
                
            elif entity_type == "resource":
                node = Resource(
                    name=name,
                    description=description,
                    resource_type=metadata.get("type", "url"),
                    url=metadata.get("url"),
                    key_points=metadata.get("key_points", []),
                )
                node_type = NodeType.RESOURCE
                
            else:
                logger.warning(
                    "distiller_unknown_entity_type",
                    extra={"entity_type": entity_type},
                )
                return None
            
            # Create node
            request = MemoryRequest(
                operation=MemoryOperation.CREATE,
                memory_type=MemoryType.STRUCTURAL,
                entity_type=node_type,
                data=node.model_dump(),
                metadata={"source": "librarian_distillation"},
            )
            
            response = await self.gateway.execute(request)
            
            if response.success:
                uuid = response.data
                logger.info(
                    "distiller_node_created",
                    extra={"entity_type": entity_type, "uuid": uuid},
                )
                return uuid
            else:
                logger.error(
                    "distiller_node_creation_failed",
                    extra={"error": response.error},
                )
                return None
                
        except Exception as e:
            logger.exception("distiller_create_node_exception", extra={"error": str(e)})
            return None

    async def deduplicate_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate entities based on name similarity.
        
        Args:
            entities: List of extracted entities
            
        Returns:
            Deduplicated list
        """
        seen_names = set()
        unique_entities = []
        
        for entity in entities:
            name = entity.get("name", "").lower().strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_entities.append(entity)
        
        logger.info(
            "distiller_deduplicated",
            extra={
                "original_count": len(entities),
                "unique_count": len(unique_entities),
            },
        )
        
        return unique_entities
