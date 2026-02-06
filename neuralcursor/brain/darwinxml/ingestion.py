"""
DarwinXML ingestion bridge for NeuralCursor brain.

Orchestrates the ingestion of DarwinXML documents into both Neo4j and MongoDB,
connecting the Docling pipeline with the neuralcursor knowledge graph.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.mongodb.client import MongoDBClient
from neuralcursor.brain.neo4j.models import BaseNode, NodeType, RelationType

from .converter import DarwinXMLConverter, ConversionResult

# Import DarwinXML models
import sys
sys.path.insert(0, '/workspace/src')
from ingestion.docling.darwinxml_models import DarwinXMLDocument

logger = logging.getLogger(__name__)


class IngestionStats(BaseModel):
    """Statistics from DarwinXML ingestion."""

    total_documents: int = 0
    resources_created: int = 0
    para_nodes_created: int = 0
    relationships_created: int = 0
    mongodb_resources_stored: int = 0
    errors: List[str] = []


class DarwinXMLIngestionBridge:
    """
    Bridge between DarwinXML and NeuralCursor brain components.
    
    Handles:
    - Converting DarwinXML to neuralcursor models
    - Storing in Neo4j graph database
    - Storing in MongoDB episodic memory
    - Deduplication and conflict resolution
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        mongodb_client: MongoDBClient,
    ):
        """
        Initialize ingestion bridge.
        
        Args:
            neo4j_client: Connected Neo4j client
            mongodb_client: Connected MongoDB client
        """
        self.neo4j_client = neo4j_client
        self.mongodb_client = mongodb_client
        self.converter = DarwinXMLConverter()

    async def ingest_darwin_document(
        self,
        darwin_doc: DarwinXMLDocument,
        embedding: Optional[List[float]] = None,
    ) -> ConversionResult:
        """
        Ingest a single DarwinXML document into the brain.
        
        Args:
            darwin_doc: DarwinXML document to ingest
            embedding: Optional embedding vector
            
        Returns:
            ConversionResult with created nodes and relationships
        """
        # Convert DarwinXML to neuralcursor models
        result = self.converter.convert_to_neuralcursor(darwin_doc, embedding)
        
        # Store resource node in Neo4j
        resource_uid = await self.neo4j_client.create_node(result.resource_node)
        result.resource_node.uid = resource_uid
        
        logger.info(
            "darwinxml_resource_created",
            extra={
                "resource_uid": resource_uid,
                "document_title": darwin_doc.document_title,
                "chunk_index": darwin_doc.chunk_index,
            },
        )
        
        # Store PARA nodes in Neo4j (with deduplication)
        for para_node in result.para_nodes:
            para_uid = await self._create_or_get_para_node(para_node)
            para_node.uid = para_uid
        
        # Create relationships in Neo4j
        for relationship in result.relationships:
            # Update UIDs for resource and PARA nodes
            if not relationship.from_uid or relationship.from_uid == "":
                relationship.from_uid = resource_uid
            
            # Handle entity references (create entity nodes if needed)
            if relationship.to_uid.startswith("entity:"):
                entity_name = relationship.to_uid.replace("entity:", "")
                entity_uid = await self._create_or_get_entity_node(entity_name)
                relationship.to_uid = entity_uid
            
            # Create relationship
            try:
                await self.neo4j_client.create_relationship(relationship)
                logger.debug(
                    "darwinxml_relationship_created",
                    extra={
                        "from_uid": relationship.from_uid,
                        "to_uid": relationship.to_uid,
                        "type": relationship.relation_type.value,
                    },
                )
            except Exception as e:
                logger.warning(
                    "darwinxml_relationship_failed",
                    extra={
                        "error": str(e),
                        "relationship": relationship.model_dump(),
                    },
                )
        
        # Store external resource in MongoDB
        await self.mongodb_client.save_resource(result.external_resource)
        
        logger.info(
            "darwinxml_mongodb_stored",
            extra={
                "resource_id": result.external_resource.resource_id,
                "title": result.external_resource.title,
            },
        )
        
        return result

    async def ingest_darwin_documents_batch(
        self,
        darwin_docs: List[DarwinXMLDocument],
        embeddings: Optional[List[List[float]]] = None,
    ) -> IngestionStats:
        """
        Ingest multiple DarwinXML documents in batch.
        
        Args:
            darwin_docs: List of DarwinXML documents
            embeddings: Optional list of embedding vectors (same order as docs)
            
        Returns:
            IngestionStats with counts and errors
        """
        stats = IngestionStats(total_documents=len(darwin_docs))
        
        for i, darwin_doc in enumerate(darwin_docs):
            embedding = embeddings[i] if embeddings and i < len(embeddings) else None
            
            try:
                result = await self.ingest_darwin_document(darwin_doc, embedding)
                
                stats.resources_created += 1
                stats.para_nodes_created += len(result.para_nodes)
                stats.relationships_created += len(result.relationships)
                stats.mongodb_resources_stored += 1
                
            except Exception as e:
                error_msg = f"Failed to ingest document '{darwin_doc.document_title}' chunk {darwin_doc.chunk_index}: {str(e)}"
                logger.exception(
                    "darwinxml_ingestion_failed",
                    extra={
                        "document_title": darwin_doc.document_title,
                        "chunk_index": darwin_doc.chunk_index,
                        "error": str(e),
                    },
                )
                stats.errors.append(error_msg)
        
        logger.info(
            "darwinxml_batch_ingestion_complete",
            extra={
                "total_documents": stats.total_documents,
                "resources_created": stats.resources_created,
                "para_nodes_created": stats.para_nodes_created,
                "relationships_created": stats.relationships_created,
                "errors": len(stats.errors),
            },
        )
        
        return stats

    async def _create_or_get_para_node(self, para_node: BaseNode) -> str:
        """
        Create PARA node or return existing UID if node exists.
        
        Performs deduplication by name and type.
        
        Args:
            para_node: PARA node to create or get
            
        Returns:
            UID of created or existing node
        """
        # Check if node exists
        existing_uid = await self.neo4j_client.find_node_by_name(
            para_node.name,
            para_node.node_type,
        )
        
        if existing_uid:
            logger.debug(
                "darwinxml_para_node_exists",
                extra={
                    "name": para_node.name,
                    "type": para_node.node_type.value,
                    "uid": existing_uid,
                },
            )
            return existing_uid
        
        # Create new node
        uid = await self.neo4j_client.create_node(para_node)
        logger.info(
            "darwinxml_para_node_created",
            extra={
                "name": para_node.name,
                "type": para_node.node_type.value,
                "uid": uid,
            },
        )
        
        return uid

    async def _create_or_get_entity_node(self, entity_name: str) -> str:
        """
        Create entity resource node or return existing UID.
        
        Entities are stored as Resource nodes with source_type='entity'.
        
        Args:
            entity_name: Name of entity
            
        Returns:
            UID of created or existing entity node
        """
        from neuralcursor.brain.neo4j.models import ResourceNode
        
        # Check if entity exists
        existing_uid = await self.neo4j_client.find_node_by_name(
            entity_name,
            NodeType.RESOURCE,
        )
        
        if existing_uid:
            return existing_uid
        
        # Create new entity node
        entity_node = ResourceNode(
            name=entity_name,
            description=f"Entity extracted from documents: {entity_name}",
            source_type="entity",
            tags=["entity", "auto-extracted"],
            metadata={"source": "darwinxml"},
        )
        
        uid = await self.neo4j_client.create_node(entity_node)
        logger.info(
            "darwinxml_entity_created",
            extra={"entity_name": entity_name, "uid": uid},
        )
        
        return uid

    async def query_by_para_category(
        self,
        category_name: str,
        category_type: NodeType,
        limit: int = 20,
    ) -> List[dict]:
        """
        Query resources by PARA category.
        
        Args:
            category_name: Name of PARA category
            category_type: Type of category (PROJECT, AREA, RESOURCE, ARCHIVE)
            limit: Maximum results
            
        Returns:
            List of resource nodes connected to the category
        """
        # Find category node
        category_uid = await self.neo4j_client.find_node_by_name(
            category_name,
            category_type,
        )
        
        if not category_uid:
            logger.warning(
                "darwinxml_category_not_found",
                extra={"category_name": category_name, "type": category_type.value},
            )
            return []
        
        # Find resources that belong to this category
        resources = await self.neo4j_client.get_related_nodes(
            category_uid,
            RelationType.BELONGS_TO,
            direction="incoming",  # Resources → BELONGS_TO → Category
            limit=limit,
        )
        
        logger.info(
            "darwinxml_category_query",
            extra={
                "category_name": category_name,
                "type": category_type.value,
                "result_count": len(resources),
            },
        )
        
        return resources

    async def query_by_entity(
        self,
        entity_name: str,
        limit: int = 20,
    ) -> List[dict]:
        """
        Query resources that mention an entity.
        
        Args:
            entity_name: Name of entity
            limit: Maximum results
            
        Returns:
            List of resource nodes that reference the entity
        """
        # Find entity node
        entity_uid = await self.neo4j_client.find_node_by_name(
            entity_name,
            NodeType.RESOURCE,  # Entities are stored as Resource nodes
        )
        
        if not entity_uid:
            logger.warning(
                "darwinxml_entity_not_found",
                extra={"entity_name": entity_name},
            )
            return []
        
        # Find resources that reference this entity
        resources = await self.neo4j_client.get_related_nodes(
            entity_uid,
            RelationType.REFERENCES,
            direction="incoming",
            limit=limit,
        )
        
        logger.info(
            "darwinxml_entity_query",
            extra={
                "entity_name": entity_name,
                "result_count": len(resources),
            },
        )
        
        return resources


__all__ = ["DarwinXMLIngestionBridge", "IngestionStats"]
