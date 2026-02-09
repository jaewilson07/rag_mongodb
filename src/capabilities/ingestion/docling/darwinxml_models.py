"""
DarwinXML Pydantic models for semantic document wrapping.

DarwinXML provides a rich metadata layer for document chunks, enabling:
- Hierarchical annotations (structure, relationships)
- Sub-annotations (attributes, tags, semantic markers)
- Provenance metadata (source, lineage, validation status)
- Graph-ready relationships for Neo4j integration
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from mdrag.capabilities.ingestion.models import GraphTriple


class AnnotationType(str, Enum):
    """Types of annotations supported in DarwinXML."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    QUOTE = "quote"
    SECTION = "section"
    METADATA = "metadata"
    RELATIONSHIP = "relationship"


class AttributeType(str, Enum):
    """Types of attributes for semantic tagging."""

    TAG = "tag"
    CATEGORY = "category"
    STATUS = "status"
    ENTITY = "entity"
    LOCATION = "location"
    TEMPORAL = "temporal"
    CUSTOM = "custom"


class RelationshipType(str, Enum):
    """Types of relationships between chunks/entities."""

    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    REFERENCE = "reference"
    CITATION = "citation"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"


class ValidationStatus(str, Enum):
    """Validation status for ingested content."""

    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    VERIFIED = "verified"
    REJECTED = "rejected"


class BoundingBox(BaseModel):
    """Bounding box coordinates for spatial annotations."""

    x: float
    y: float
    width: float
    height: float
    page: Optional[int] = None


class DarwinAttribute(BaseModel):
    """
    Attribute for semantic tagging within DarwinXML.

    Attributes store rich metadata like tags, categories, entities, etc.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: AttributeType
    name: str
    value: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Ensure confidence is between 0 and 1."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")
        return v


class DarwinRelationship(BaseModel):
    """
    Relationship between chunks or entities in the document graph.

    Relationships enable Neo4j integration and graph-based retrieval.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: RelationshipType
    source_id: str
    target_id: str
    label: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class DarwinAnnotation(BaseModel):
    """
    Hierarchical annotation in DarwinXML.

    Annotations describe structural elements (headings, tables, sections)
    and can contain sub-annotations (attributes, relationships).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: AnnotationType
    content: str
    bounding_box: Optional[BoundingBox] = None
    attributes: List[DarwinAttribute] = Field(default_factory=list)
    relationships: List[DarwinRelationship] = Field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProvenanceMetadata(BaseModel):
    """
    Provenance metadata for tracking data lineage and quality.

    Tracks when/where/why data was ingested and its validation status.
    """

    ingestion_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    document_uid: Optional[str] = None
    source_url: str
    source_type: str
    source_id: Optional[str] = None
    source_group: Optional[str] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    crawl_session_id: Optional[str] = None
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    processor_version: str = "docling-2.14"
    chunker_version: str = "hierarchical-v1"
    embedding_model: Optional[str] = None
    content_hash: str
    lineage: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class DarwinXMLDocument(BaseModel):
    """
    Complete DarwinXML document wrapping a Docling chunk.

    This is the top-level container that stores:
    - Raw content (text)
    - Annotations (structure, hierarchy)
    - Attributes (semantic tags)
    - Relationships (graph edges)
    - Provenance (lineage, validation)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0"
    document_title: str
    chunk_index: int
    chunk_uuid: str  # Links to MongoDB chunk
    content: str
    annotations: List[DarwinAnnotation] = Field(default_factory=list)
    provenance: ProvenanceMetadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.model_dump(mode="json")

    def to_xml(self) -> str:
        """
        Convert to XML string representation.

        Note: Basic XML generation. For production, consider using lxml.
        """
        from xml.etree.ElementTree import Element, SubElement, tostring

        root = Element("darwin-document")
        root.set("id", self.id)
        root.set("schema-version", self.schema_version)

        # Metadata
        metadata_elem = SubElement(root, "metadata")
        SubElement(metadata_elem, "document-title").text = self.document_title
        SubElement(metadata_elem, "chunk-index").text = str(self.chunk_index)
        SubElement(metadata_elem, "chunk-uuid").text = self.chunk_uuid

        # Content
        SubElement(root, "content").text = self.content

        # Provenance
        prov_elem = SubElement(root, "provenance")
        SubElement(prov_elem, "ingestion-timestamp").text = (
            self.provenance.ingestion_timestamp
        )
        SubElement(prov_elem, "source-url").text = self.provenance.source_url
        SubElement(prov_elem, "source-type").text = self.provenance.source_type
        SubElement(prov_elem, "validation-status").text = (
            self.provenance.validation_status.value
        )
        SubElement(prov_elem, "content-hash").text = self.provenance.content_hash

        # Annotations
        annotations_elem = SubElement(root, "annotations")
        for ann in self.annotations:
            ann_elem = SubElement(annotations_elem, "annotation")
            ann_elem.set("id", ann.id)
            ann_elem.set("type", ann.type.value)
            SubElement(ann_elem, "content").text = ann.content

            # Attributes
            if ann.attributes:
                attrs_elem = SubElement(ann_elem, "attributes")
                for attr in ann.attributes:
                    attr_elem = SubElement(attrs_elem, "attribute")
                    attr_elem.set("type", attr.type.value)
                    attr_elem.set("name", attr.name)
                    attr_elem.text = attr.value

            # Relationships
            if ann.relationships:
                rels_elem = SubElement(ann_elem, "relationships")
                for rel in ann.relationships:
                    rel_elem = SubElement(rels_elem, "relationship")
                    rel_elem.set("type", rel.type.value)
                    rel_elem.set("source-id", rel.source_id)
                    rel_elem.set("target-id", rel.target_id)
                    if rel.label:
                        rel_elem.set("label", rel.label)

        return tostring(root, encoding="unicode")

    def extract_graph_triples(
        self,
        *,
        include_provenance: bool = True,
        include_tags: bool = True,
    ) -> List[GraphTriple]:
        """
        Extract graph triples for Neo4j ingestion.

        Args:
            include_provenance: Whether to include provenance triples.
            include_tags: Whether to include tag relationships.

        Returns:
            List of graph triples.
        """
        triples: List[GraphTriple] = []

        triples.append(
            GraphTriple(
                subject=self.document_title,
                predicate="HAS_CHUNK",
                object=self.chunk_uuid,
                properties={
                    "chunk_index": self.chunk_index,
                    "document_uid": self.provenance.document_uid,
                },
            )
        )

        for ann in self.annotations:
            for rel in ann.relationships:
                triples.append(
                    GraphTriple(
                        subject=rel.source_id,
                        predicate=rel.type.value.upper(),
                        object=rel.target_id,
                        properties=rel.properties,
                    )
                )

            for attr in ann.attributes:
                if attr.type == AttributeType.ENTITY:
                    triples.append(
                        GraphTriple(
                            subject=self.chunk_uuid,
                            predicate="MENTIONS",
                            object=attr.value,
                            properties={"confidence": attr.confidence},
                        )
                    )

        if include_provenance:
            triples.append(
                GraphTriple(
                    subject=self.chunk_uuid,
                    predicate="HAS_PROVENANCE",
                    object=f"provenance:{self.provenance.content_hash}",
                    properties={
                        "source_url": self.provenance.source_url,
                        "source_type": self.provenance.source_type,
                        "source_id": self.provenance.source_id,
                        "document_uid": self.provenance.document_uid,
                        "ingestion_timestamp": self.provenance.ingestion_timestamp,
                        "validation_status": self.provenance.validation_status.value,
                    },
                )
            )

        if include_tags:
            for tag in self.provenance.tags:
                triples.append(
                    GraphTriple(
                        subject=self.chunk_uuid,
                        predicate="HAS_TAG",
                        object=f"tag:{tag}",
                        properties={},
                    )
                )

        return triples


__all__ = [
    "AnnotationType",
    "AttributeType",
    "BoundingBox",
    "DarwinAnnotation",
    "DarwinAttribute",
    "DarwinRelationship",
    "DarwinXMLDocument",
    "ProvenanceMetadata",
    "RelationshipType",
    "ValidationStatus",
]
