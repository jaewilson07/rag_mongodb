"""
Converter from DarwinXML models to NeuralCursor brain models.

Converts DarwinXML semantic annotations into Neo4j PARA nodes and relationships.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel

from neuralcursor.brain.neo4j.models import (
    BaseNode,
    NodeType,
    ProjectNode,
    AreaNode,
    ResourceNode,
    ArchiveNode,
    Relationship,
    RelationType,
)
from neuralcursor.brain.mongodb.client import ExternalResource

# Import DarwinXML models
import sys
sys.path.insert(0, '/workspace/src')
from ingestion.docling.darwinxml_models import (
    DarwinXMLDocument,
    AttributeType,
)

logger = logging.getLogger(__name__)


class ConversionResult(BaseModel):
    """Result of converting DarwinXML to neuralcursor models."""

    resource_node: ResourceNode
    relationships: List[Relationship]
    external_resource: ExternalResource
    para_nodes: List[BaseNode]  # Extracted PARA category nodes


class DarwinXMLConverter:
    """
    Converts DarwinXML documents to NeuralCursor brain models.
    
    Handles:
    - PARA category extraction → Project/Area/Resource/Archive nodes
    - Entity extraction → Resource nodes
    - Chunk metadata → ExternalResource for MongoDB
    - Relationships → Neo4j relationships
    """

    def __init__(self):
        """Initialize converter."""
        pass

    def convert_to_neuralcursor(
        self,
        darwin_doc: DarwinXMLDocument,
        embedding: Optional[List[float]] = None,
    ) -> ConversionResult:
        """
        Convert DarwinXML document to neuralcursor models.
        
        Args:
            darwin_doc: DarwinXML document to convert
            embedding: Optional embedding vector
            
        Returns:
            ConversionResult with Neo4j nodes and MongoDB resource
        """
        # Create main resource node
        resource_node = self._create_resource_node(darwin_doc)
        
        # Extract PARA category nodes
        para_nodes = self._extract_para_nodes(darwin_doc)
        
        # Create relationships
        relationships = self._create_relationships(darwin_doc, resource_node, para_nodes)
        
        # Create MongoDB external resource
        external_resource = self._create_external_resource(darwin_doc, embedding)
        
        return ConversionResult(
            resource_node=resource_node,
            relationships=relationships,
            external_resource=external_resource,
            para_nodes=para_nodes,
        )

    def _create_resource_node(self, darwin_doc: DarwinXMLDocument) -> ResourceNode:
        """Create a ResourceNode from DarwinXML document."""
        # Determine source type from provenance
        source_type = darwin_doc.provenance.source_type
        if source_type == "web":
            resource_type = "article"
        elif source_type == "gdrive":
            resource_type = "documentation"
        else:
            resource_type = "documentation"
        
        # Extract tags from provenance
        tags = darwin_doc.provenance.tags.copy()
        
        # Add content type tags
        for ann in darwin_doc.annotations:
            if ann.type.value == "table":
                tags.append("content:table")
            elif ann.type.value == "code":
                tags.append("content:code")
        
        return ResourceNode(
            name=darwin_doc.document_title,
            description=f"Document chunk {darwin_doc.chunk_index}: {darwin_doc.content[:200]}...",
            source_type=resource_type,
            source_url=darwin_doc.provenance.source_url,
            content_hash=darwin_doc.provenance.content_hash,
            tags=tags,
            metadata={
                "chunk_uuid": darwin_doc.chunk_uuid,
                "chunk_index": darwin_doc.chunk_index,
                "validation_status": darwin_doc.provenance.validation_status.value,
                "schema_version": darwin_doc.schema_version,
            },
        )

    def _extract_para_nodes(self, darwin_doc: DarwinXMLDocument) -> List[BaseNode]:
        """Extract PARA category nodes from DarwinXML attributes."""
        para_nodes = []
        
        # Scan all annotations for PARA category attributes
        for ann in darwin_doc.annotations:
            for attr in ann.attributes:
                if attr.type != AttributeType.CATEGORY:
                    continue
                
                # Parse PARA category format: "Project:Name" or "Area:Name"
                if ":" in attr.value:
                    category_type, category_name = attr.value.split(":", 1)
                    category_type = category_type.strip().lower()
                    category_name = category_name.strip()
                    
                    if category_type == "project":
                        para_nodes.append(
                            ProjectNode(
                                name=category_name,
                                description=f"Project extracted from {darwin_doc.document_title}",
                                status="active",
                                metadata={"source": "darwinxml", "document_title": darwin_doc.document_title},
                            )
                        )
                    elif category_type == "area":
                        para_nodes.append(
                            AreaNode(
                                name=category_name,
                                description=f"Area of focus extracted from {darwin_doc.document_title}",
                                metadata={"source": "darwinxml", "document_title": darwin_doc.document_title},
                            )
                        )
                    elif category_type == "resource":
                        # Already handled by main resource node
                        pass
                    elif category_type == "archive":
                        para_nodes.append(
                            ArchiveNode(
                                name=category_name,
                                description=f"Archived item from {darwin_doc.document_title}",
                                archived_from=NodeType.RESOURCE,
                                archive_reason="Extracted from document tags",
                                metadata={"source": "darwinxml", "document_title": darwin_doc.document_title},
                            )
                        )
        
        return para_nodes

    def _create_relationships(
        self,
        darwin_doc: DarwinXMLDocument,
        resource_node: ResourceNode,
        para_nodes: List[BaseNode],
    ) -> List[Relationship]:
        """Create relationships between nodes."""
        relationships = []
        
        # Create BELONGS_TO relationships from resource to PARA categories
        for para_node in para_nodes:
            if para_node.node_type in (NodeType.PROJECT, NodeType.AREA):
                relationships.append(
                    Relationship(
                        from_uid=resource_node.uid or "",
                        to_uid=para_node.uid or "",
                        relation_type=RelationType.BELONGS_TO,
                        properties={
                            "chunk_index": darwin_doc.chunk_index,
                            "confidence": 1.0,
                        },
                    )
                )
        
        # Extract entity relationships from annotations
        for ann in darwin_doc.annotations:
            for attr in ann.attributes:
                if attr.type == AttributeType.ENTITY:
                    # Create REFERENCES relationship to entity
                    relationships.append(
                        Relationship(
                            from_uid=resource_node.uid or "",
                            to_uid=f"entity:{attr.value}",
                            relation_type=RelationType.REFERENCES,
                            properties={
                                "entity_name": attr.value,
                                "confidence": attr.confidence or 0.8,
                                "annotation_id": ann.id,
                            },
                        )
                    )
        
        # Use DarwinXML relationships
        for ann in darwin_doc.annotations:
            for rel in ann.relationships:
                # Map DarwinXML relationship types to neuralcursor types
                rel_type = self._map_relationship_type(rel.type.value)
                if rel_type:
                    relationships.append(
                        Relationship(
                            from_uid=rel.source_id,
                            to_uid=rel.target_id,
                            relation_type=rel_type,
                            properties=rel.properties,
                        )
                    )
        
        return relationships

    def _create_external_resource(
        self,
        darwin_doc: DarwinXMLDocument,
        embedding: Optional[List[float]],
    ) -> ExternalResource:
        """Create MongoDB ExternalResource from DarwinXML."""
        # Determine resource type
        source_type = darwin_doc.provenance.source_type
        if source_type == "web":
            resource_type = "article"
        elif source_type == "gdrive":
            resource_type = "documentation"
        else:
            resource_type = "documentation"
        
        return ExternalResource(
            resource_id=darwin_doc.chunk_uuid,
            resource_type=resource_type,
            title=f"{darwin_doc.document_title} (Chunk {darwin_doc.chunk_index})",
            url=darwin_doc.provenance.source_url,
            content=darwin_doc.content,
            summary=self._generate_summary(darwin_doc),
            embedding=embedding,
            tags=darwin_doc.provenance.tags,
            metadata={
                "chunk_index": darwin_doc.chunk_index,
                "schema_version": darwin_doc.schema_version,
                "validation_status": darwin_doc.provenance.validation_status.value,
                "content_hash": darwin_doc.provenance.content_hash,
                "annotations": len(darwin_doc.annotations),
                "darwin_metadata": darwin_doc.to_dict(),
            },
        )

    def _generate_summary(self, darwin_doc: DarwinXMLDocument) -> str:
        """Generate a summary from DarwinXML annotations."""
        # Start with document title and chunk index
        summary_parts = [f"{darwin_doc.document_title} - Chunk {darwin_doc.chunk_index}"]
        
        # Add heading path if available
        if darwin_doc.annotations:
            main_ann = darwin_doc.annotations[0]
            heading_path = main_ann.metadata.get("heading_path", [])
            if heading_path:
                summary_parts.append(" > ".join(heading_path))
        
        # Add content preview
        content_preview = darwin_doc.content[:200].strip()
        if len(darwin_doc.content) > 200:
            content_preview += "..."
        summary_parts.append(content_preview)
        
        return "\n\n".join(summary_parts)

    @staticmethod
    def _map_relationship_type(darwin_rel_type: str) -> Optional[RelationType]:
        """Map DarwinXML relationship type to neuralcursor RelationType."""
        mapping = {
            "parent": RelationType.CONTAINS,
            "child": RelationType.BELONGS_TO,
            "reference": RelationType.REFERENCES,
            "citation": RelationType.REFERENCES,
            "depends_on": RelationType.DEPENDS_ON,
            "related_to": RelationType.RELATES_TO,
        }
        return mapping.get(darwin_rel_type.lower())


__all__ = ["DarwinXMLConverter", "ConversionResult"]
