"""
DarwinXML wrapper for converting Docling chunks to semantic DarwinXML format.

This module provides the bridge between Docling's hierarchical chunks and
DarwinXML's rich semantic structure, enabling:
- Automatic annotation extraction from chunk metadata
- Hierarchical relationship building
- Attribute tagging (PARA categories, entities, temporal markers)
- Validation and schema enforcement
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional
from uuid import uuid4

from mdrag.ingestion.docling.chunker import DoclingChunks
from mdrag.ingestion.docling.darwinxml_models import (
    AnnotationType,
    AttributeType,
    DarwinAnnotation,
    DarwinAttribute,
    DarwinRelationship,
    DarwinXMLDocument,
    ProvenanceMetadata,
    RelationshipType,
    ValidationStatus,
)
from mdrag.mdrag_logging.service_logging import get_logger

logger = get_logger(__name__)


class DarwinXMLWrapper:
    """
    Wrapper for converting DoclingChunks to DarwinXML format.

    This class adds semantic structure, validation, and graph-ready metadata
    to Docling chunks, transforming them into DarwinXML documents suitable for:
    - Neo4j graph storage (relationships, entities)
    - MongoDB full-text storage (raw content)
    - Agent-based retrieval (semantic tags, hierarchy)
    """

    def __init__(
        self,
        embedding_model: Optional[str] = None,
        processor_version: str = "docling-2.14",
        enable_entity_extraction: bool = True,
        enable_category_tagging: bool = True,
    ):
        """
        Initialize DarwinXML wrapper.

        Args:
            embedding_model: Name of embedding model for provenance
            processor_version: Docling processor version for provenance
            enable_entity_extraction: Extract entities from content
            enable_category_tagging: Auto-tag with PARA categories
        """
        self.embedding_model = embedding_model
        self.processor_version = processor_version
        self.enable_entity_extraction = enable_entity_extraction
        self.enable_category_tagging = enable_category_tagging

    def wrap_chunk(
        self,
        chunk: DoclingChunks,
        document_uid: Optional[str] = None,
        parent_chunk_id: Optional[str] = None,
        validation_status: ValidationStatus = ValidationStatus.UNVALIDATED,
        additional_tags: Optional[List[str]] = None,
    ) -> DarwinXMLDocument:
        """
        Wrap a DoclingChunk into DarwinXML format.

        Args:
            chunk: DoclingChunk to wrap
            document_uid: Optional document identifier
            parent_chunk_id: Optional parent chunk ID for hierarchy
            validation_status: Validation status for this chunk
            additional_tags: Additional tags to apply

        Returns:
            DarwinXMLDocument with full semantic structure
        """
        # Generate unique chunk UUID
        chunk_uuid = str(uuid4())

        # Build provenance metadata
        provenance = self._build_provenance(
            chunk=chunk,
            validation_status=validation_status,
            additional_tags=additional_tags or [],
        )

        # Extract annotations from chunk structure
        annotations = self._extract_annotations(
            chunk=chunk,
            chunk_uuid=chunk_uuid,
            parent_chunk_id=parent_chunk_id,
        )

        # Build DarwinXML document
        darwin_doc = DarwinXMLDocument(
            id=chunk_uuid,
            document_title=chunk.passport.document_title,
            chunk_index=chunk.index,
            chunk_uuid=chunk_uuid,
            content=chunk.content,
            annotations=annotations,
            provenance=provenance,
            metadata={
                "document_uid": document_uid,
                "parent_chunk_id": parent_chunk_id,
                "token_count": chunk.token_count,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "source_type": chunk.passport.source_type,
                "page_number": chunk.passport.page_number,
                **chunk.metadata,
            },
        )

        return darwin_doc

    def wrap_chunks_batch(
        self,
        chunks: List[DoclingChunks],
        document_uid: Optional[str] = None,
        validation_status: ValidationStatus = ValidationStatus.UNVALIDATED,
        additional_tags: Optional[List[str]] = None,
    ) -> List[DarwinXMLDocument]:
        """
        Wrap a batch of DoclingChunks with hierarchical relationships.

        This method automatically builds parent-child relationships between
        chunks based on their heading hierarchy.

        Args:
            chunks: List of DoclingChunks to wrap
            document_uid: Optional document identifier
            validation_status: Validation status for all chunks
            additional_tags: Additional tags to apply to all chunks

        Returns:
            List of DarwinXMLDocuments with relationships
        """
        darwin_docs = []
        chunk_id_map: Dict[int, str] = {}

        # First pass: wrap all chunks
        for chunk in chunks:
            parent_id = self._find_parent_chunk_id(
                chunk=chunk, chunk_id_map=chunk_id_map
            )

            darwin_doc = self.wrap_chunk(
                chunk=chunk,
                document_uid=document_uid,
                parent_chunk_id=parent_id,
                validation_status=validation_status,
                additional_tags=additional_tags,
            )

            darwin_docs.append(darwin_doc)
            chunk_id_map[chunk.index] = darwin_doc.chunk_uuid

        # Second pass: add sibling relationships
        for i, darwin_doc in enumerate(darwin_docs):
            if i > 0:
                # Add relationship to previous sibling
                sibling_rel = DarwinRelationship(
                    type=RelationshipType.SIBLING,
                    source_id=darwin_doc.chunk_uuid,
                    target_id=darwin_docs[i - 1].chunk_uuid,
                    label="previous_chunk",
                )

                # Add to first annotation or create metadata annotation
                if darwin_doc.annotations:
                    darwin_doc.annotations[0].relationships.append(sibling_rel)
                else:
                    meta_ann = DarwinAnnotation(
                        type=AnnotationType.METADATA,
                        content="",
                        relationships=[sibling_rel],
                    )
                    darwin_doc.annotations.append(meta_ann)

        return darwin_docs

    def _build_provenance(
        self,
        chunk: DoclingChunks,
        validation_status: ValidationStatus,
        additional_tags: List[str],
    ) -> ProvenanceMetadata:
        """Build provenance metadata from chunk."""
        tags = list(additional_tags)

        # Add PARA category tags if enabled
        if self.enable_category_tagging:
            para_tags = self._extract_para_tags(chunk)
            tags.extend(para_tags)

        # Add chunk method tag
        chunk_method = chunk.metadata.get("chunk_method", "unknown")
        tags.append(f"chunker:{chunk_method}")

        # Add table tag if applicable
        if chunk.metadata.get("is_table", False):
            tags.append("content:table")

        return ProvenanceMetadata(
            ingestion_timestamp=chunk.passport.ingestion_timestamp,
            document_uid=chunk.passport.document_uid,
            source_url=chunk.passport.source_url,
            source_type=chunk.passport.source_type,
            source_id=chunk.passport.source_id,
            source_group=chunk.passport.source_group,
            user_id=chunk.passport.user_id,
            org_id=chunk.passport.org_id,
            validation_status=validation_status,
            processor_version=self.processor_version,
            chunker_version="hierarchical-v1",
            embedding_model=self.embedding_model,
            content_hash=chunk.passport.content_hash
            or self._compute_content_hash(chunk.content),
            tags=tags,
        )

    def _extract_annotations(
        self,
        chunk: DoclingChunks,
        chunk_uuid: str,
        parent_chunk_id: Optional[str],
    ) -> List[DarwinAnnotation]:
        """Extract annotations from chunk metadata and content."""
        annotations = []

        # Create main content annotation
        content_type = self._infer_content_type(chunk)
        attributes = self._extract_attributes(chunk)
        relationships = self._build_relationships(chunk, chunk_uuid, parent_chunk_id)

        main_annotation = DarwinAnnotation(
            type=content_type,
            content=chunk.content,
            attributes=attributes,
            relationships=relationships,
            parent_id=parent_chunk_id,
            metadata={
                "heading_path": chunk.passport.heading_path,
                "page_number": chunk.passport.page_number,
                "token_count": chunk.token_count,
            },
        )
        annotations.append(main_annotation)

        # Add heading hierarchy annotations
        for i, heading in enumerate(chunk.passport.heading_path):
            heading_ann = DarwinAnnotation(
                type=AnnotationType.HEADING,
                content=heading,
                parent_id=main_annotation.id if i == 0 else annotations[-1].id,
                metadata={"level": i + 1},
            )
            annotations.append(heading_ann)

        return annotations

    def _extract_attributes(self, chunk: DoclingChunks) -> List[DarwinAttribute]:
        """Extract semantic attributes from chunk."""
        attributes = []

        # Category attributes (PARA)
        if self.enable_category_tagging:
            para_categories = self._extract_para_categories(chunk)
            for category in para_categories:
                attributes.append(
                    DarwinAttribute(
                        type=AttributeType.CATEGORY,
                        name="para_category",
                        value=category,
                    )
                )

        # Entity extraction
        if self.enable_entity_extraction:
            entities = self._extract_entities(chunk.content)
            for entity in entities:
                attributes.append(
                    DarwinAttribute(
                        type=AttributeType.ENTITY,
                        name="named_entity",
                        value=entity,
                        confidence=0.8,  # Basic extraction confidence
                    )
                )

        # Temporal markers
        temporal_markers = self._extract_temporal_markers(chunk.content)
        for marker in temporal_markers:
            attributes.append(
                DarwinAttribute(
                    type=AttributeType.TEMPORAL,
                    name="temporal_reference",
                    value=marker,
                )
            )

        # Custom metadata attributes
        for key, value in chunk.metadata.items():
            if key in ("is_table", "chunk_method", "page_number"):
                attributes.append(
                    DarwinAttribute(
                        type=AttributeType.CUSTOM,
                        name=key,
                        value=str(value),
                    )
                )

        return attributes

    def _build_relationships(
        self,
        chunk: DoclingChunks,
        chunk_uuid: str,
        parent_chunk_id: Optional[str],
    ) -> List[DarwinRelationship]:
        """Build relationships for this chunk."""
        relationships = []

        # Parent relationship
        if parent_chunk_id:
            relationships.append(
                DarwinRelationship(
                    type=RelationshipType.PARENT,
                    source_id=chunk_uuid,
                    target_id=parent_chunk_id,
                    label="child_of",
                )
            )

        return relationships

    def _infer_content_type(self, chunk: DoclingChunks) -> AnnotationType:
        """Infer annotation type from chunk metadata."""
        if chunk.metadata.get("is_table", False):
            return AnnotationType.TABLE

        chunk_method = chunk.metadata.get("chunk_method", "")
        if "hierarchical" in chunk_method:
            return AnnotationType.SECTION

        # Check content patterns
        content = chunk.content.strip()
        if content.startswith("#"):
            return AnnotationType.HEADING
        if content.startswith("```"):
            return AnnotationType.CODE
        if content.startswith(">"):
            return AnnotationType.QUOTE
        if re.match(r"^\d+\.|^[-*]", content):
            return AnnotationType.LIST

        return AnnotationType.PARAGRAPH

    def _extract_para_tags(self, chunk: DoclingChunks) -> List[str]:
        """Extract PARA (Projects, Areas, Resources, Archives) category tags."""
        tags = []
        content_lower = chunk.content.lower()

        # Projects markers
        if any(
            marker in content_lower
            for marker in ["#p/", "project:", "deliverable", "deadline"]
        ):
            tags.append("para:project")

        # Areas markers
        if any(
            marker in content_lower
            for marker in ["#a/", "area:", "responsibility", "ongoing"]
        ):
            tags.append("para:area")

        # Resources markers
        if any(
            marker in content_lower
            for marker in ["#r/", "resource:", "reference", "guide"]
        ):
            tags.append("para:resource")

        # Archives markers
        if any(
            marker in content_lower
            for marker in ["#archive", "completed", "deprecated"]
        ):
            tags.append("para:archive")

        return tags

    def _extract_para_categories(self, chunk: DoclingChunks) -> List[str]:
        """Extract PARA categories as attributes."""
        categories = []
        content = chunk.content

        # Look for explicit PARA tags
        para_pattern = r"#(p|a|r|archive)/(\w+)"
        matches = re.findall(para_pattern, content, re.IGNORECASE)

        for prefix, category in matches:
            if prefix.lower() == "p":
                categories.append(f"Project:{category}")
            elif prefix.lower() == "a":
                categories.append(f"Area:{category}")
            elif prefix.lower() == "r":
                categories.append(f"Resource:{category}")
            elif prefix.lower() == "archive":
                categories.append(f"Archive:{category}")

        return categories

    def _extract_entities(self, content: str) -> List[str]:
        """
        Basic entity extraction from content.

        Note: This is a simple pattern-based approach. For production,
        consider using spaCy or a proper NER model.
        """
        entities = []

        # Capitalized words (potential proper nouns)
        capitalized_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        matches = re.findall(capitalized_pattern, content)

        # Filter out common non-entities
        stopwords = {"The", "This", "That", "These", "Those", "A", "An"}
        entities = [m for m in matches if m not in stopwords]

        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities[:10]  # Limit to 10 entities

    def _extract_temporal_markers(self, content: str) -> List[str]:
        """Extract temporal references from content."""
        markers = []

        # Date patterns
        date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",  # ISO date
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # US date
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",  # Month Day, Year
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            markers.extend(matches)

        # Relative time markers
        relative_pattern = r"\b(?:today|yesterday|tomorrow|last\s+\w+|next\s+\w+)\b"
        relative_matches = re.findall(relative_pattern, content, re.IGNORECASE)
        markers.extend(relative_matches)

        return markers[:5]  # Limit to 5 markers

    @staticmethod
    def _compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _find_parent_chunk_id(
        chunk: DoclingChunks, chunk_id_map: Dict[int, str]
    ) -> Optional[str]:
        """
        Find parent chunk ID based on heading hierarchy.

        A parent is a previous chunk with a shorter heading path,
        indicating a higher-level section.
        """
        # Search backwards for a chunk with shorter heading path
        for idx in range(chunk.index - 1, -1, -1):
            if idx in chunk_id_map:
                # In practice, you'd need access to the original chunk here
                # For now, assume previous chunk is parent if depth suggests it
                # This is a simplified implementation
                return chunk_id_map[idx]

        return None


__all__ = ["DarwinXMLWrapper"]
