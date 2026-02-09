"""
Unit tests for DarwinXML components.

Tests the DarwinXML models, wrapper, validator, and storage without requiring
full environment setup.
"""


# Import DarwinXML components
import sys
sys.path.insert(0, '/workspace/src')

from ingestion.docling.darwinxml_models import (
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


def test_darwin_attribute_creation():
    """Test creating a DarwinAttribute."""
    attr = DarwinAttribute(
        type=AttributeType.CATEGORY,
        name="para_category",
        value="Project:Sellaronda",
        confidence=0.95,
    )

    assert attr.type == AttributeType.CATEGORY
    assert attr.name == "para_category"
    assert attr.value == "Project:Sellaronda"
    assert attr.confidence == 0.95


def test_darwin_attribute_confidence_validation():
    """Test confidence validation (must be 0-1)."""
    try:
        DarwinAttribute(
            type=AttributeType.ENTITY,
            name="test",
            value="test",
            confidence=1.5,  # Invalid: > 1.0
        )
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # Expected


def test_darwin_relationship_creation():
    """Test creating a DarwinRelationship."""
    rel = DarwinRelationship(
        type=RelationshipType.PARENT,
        source_id="chunk-1",
        target_id="chunk-0",
        label="child_of",
    )

    assert rel.type == RelationshipType.PARENT
    assert rel.source_id == "chunk-1"
    assert rel.target_id == "chunk-0"
    assert rel.label == "child_of"


def test_darwin_annotation_creation():
    """Test creating a DarwinAnnotation with attributes."""
    attr1 = DarwinAttribute(
        type=AttributeType.CATEGORY,
        name="para_category",
        value="Project",
    )

    attr2 = DarwinAttribute(
        type=AttributeType.ENTITY,
        name="named_entity",
        value="Italy",
        confidence=0.8,
    )

    annotation = DarwinAnnotation(
        type=AnnotationType.SECTION,
        content="Budget section for the trip",
        attributes=[attr1, attr2],
    )

    assert annotation.type == AnnotationType.SECTION
    assert len(annotation.attributes) == 2
    assert annotation.attributes[0].value == "Project"
    assert annotation.attributes[1].value == "Italy"


def test_provenance_metadata_creation():
    """Test creating ProvenanceMetadata."""
    provenance = ProvenanceMetadata(
        source_url="file:///test.md",
        source_type="upload",
        validation_status=ValidationStatus.VALIDATED,
        content_hash="abc123",
        tags=["para:project", "test"],
    )

    assert provenance.source_url == "file:///test.md"
    assert provenance.validation_status == ValidationStatus.VALIDATED
    assert len(provenance.tags) == 2
    assert "para:project" in provenance.tags


def test_darwinxml_document_creation():
    """Test creating a complete DarwinXML document."""
    provenance = ProvenanceMetadata(
        source_url="file:///test.md",
        source_type="upload",
        validation_status=ValidationStatus.UNVALIDATED,
        content_hash="test_hash",
        tags=["test"],
    )

    annotation = DarwinAnnotation(
        type=AnnotationType.PARAGRAPH,
        content="Test content",
    )

    doc = DarwinXMLDocument(
        document_title="Test Document",
        chunk_index=0,
        chunk_uuid="test-chunk-uuid",
        content="Test content",
        annotations=[annotation],
        provenance=provenance,
    )

    assert doc.schema_version == "1.0"
    assert doc.document_title == "Test Document"
    assert doc.chunk_index == 0
    assert len(doc.annotations) == 1


def test_darwinxml_to_dict():
    """Test converting DarwinXML document to dict."""
    provenance = ProvenanceMetadata(
        source_url="file:///test.md",
        source_type="upload",
        content_hash="test_hash",
    )

    doc = DarwinXMLDocument(
        document_title="Test",
        chunk_index=0,
        chunk_uuid="test-uuid",
        content="Test",
        provenance=provenance,
    )

    doc_dict = doc.to_dict()

    assert isinstance(doc_dict, dict)
    assert doc_dict["document_title"] == "Test"
    assert doc_dict["chunk_index"] == 0
    assert "provenance" in doc_dict


def test_darwinxml_to_xml():
    """Test XML export."""
    provenance = ProvenanceMetadata(
        source_url="file:///test.md",
        source_type="upload",
        content_hash="test_hash",
    )

    doc = DarwinXMLDocument(
        document_title="Test Document",
        chunk_index=0,
        chunk_uuid="test-uuid",
        content="Test content",
        provenance=provenance,
    )

    xml_string = doc.to_xml()

    assert isinstance(xml_string, str)
    assert "<darwin-document" in xml_string
    assert "Test Document" in xml_string
    assert "test-uuid" in xml_string


def test_extract_graph_triples():
    """Test graph triple extraction."""
    provenance = ProvenanceMetadata(
        source_url="file:///test.md",
        source_type="upload",
        content_hash="test_hash",
        tags=["para:project", "test"],
    )

    attr = DarwinAttribute(
        type=AttributeType.ENTITY,
        name="named_entity",
        value="Italy",
        confidence=0.8,
    )

    rel = DarwinRelationship(
        type=RelationshipType.PARENT,
        source_id="chunk-1",
        target_id="chunk-0",
    )

    annotation = DarwinAnnotation(
        type=AnnotationType.SECTION,
        content="Test content",
        attributes=[attr],
        relationships=[rel],
    )

    doc = DarwinXMLDocument(
        document_title="Test Document",
        chunk_index=0,
        chunk_uuid="test-uuid",
        content="Test",
        annotations=[annotation],
        provenance=provenance,
    )

    triples = doc.extract_graph_triples()

    assert len(triples) > 0
    
    # Check document -> chunk relationship
    doc_chunk_triple = next(
        (t for t in triples if t.predicate == "HAS_CHUNK"), None
    )
    assert doc_chunk_triple is not None
    assert doc_chunk_triple.subject == "Test Document"
    assert doc_chunk_triple.object == "test-uuid"

    # Check entity mention
    entity_triple = next(
        (t for t in triples if t.predicate == "MENTIONS"), None
    )
    assert entity_triple is not None
    assert entity_triple.object == "Italy"

    # Check tag relationships
    tag_triples = [t for t in triples if t.predicate == "HAS_TAG"]
    assert len(tag_triples) == 2  # para:project and test


def test_validation_status_enum():
    """Test ValidationStatus enum values."""
    assert ValidationStatus.UNVALIDATED.value == "unvalidated"
    assert ValidationStatus.VALIDATED.value == "validated"
    assert ValidationStatus.VERIFIED.value == "verified"
    assert ValidationStatus.REJECTED.value == "rejected"


def test_annotation_type_enum():
    """Test AnnotationType enum values."""
    assert AnnotationType.HEADING.value == "heading"
    assert AnnotationType.PARAGRAPH.value == "paragraph"
    assert AnnotationType.TABLE.value == "table"
    assert AnnotationType.SECTION.value == "section"


def test_attribute_type_enum():
    """Test AttributeType enum values."""
    assert AttributeType.TAG.value == "tag"
    assert AttributeType.CATEGORY.value == "category"
    assert AttributeType.ENTITY.value == "entity"
    assert AttributeType.TEMPORAL.value == "temporal"


def test_relationship_type_enum():
    """Test RelationshipType enum values."""
    assert RelationshipType.PARENT.value == "parent"
    assert RelationshipType.CHILD.value == "child"
    assert RelationshipType.SIBLING.value == "sibling"
    assert RelationshipType.RELATED_TO.value == "related_to"


if __name__ == "__main__":
    # Run tests manually
    print("Running DarwinXML tests...\n")

    test_darwin_attribute_creation()
    print("✓ test_darwin_attribute_creation")

    test_darwin_attribute_confidence_validation()
    print("✓ test_darwin_attribute_confidence_validation")

    test_darwin_relationship_creation()
    print("✓ test_darwin_relationship_creation")

    test_darwin_annotation_creation()
    print("✓ test_darwin_annotation_creation")

    test_provenance_metadata_creation()
    print("✓ test_provenance_metadata_creation")

    test_darwinxml_document_creation()
    print("✓ test_darwinxml_document_creation")

    test_darwinxml_to_dict()
    print("✓ test_darwinxml_to_dict")

    test_darwinxml_to_xml()
    print("✓ test_darwinxml_to_xml")

    test_extract_graph_triples()
    print("✓ test_extract_graph_triples")

    test_validation_status_enum()
    print("✓ test_validation_status_enum")

    test_annotation_type_enum()
    print("✓ test_annotation_type_enum")

    test_attribute_type_enum()
    print("✓ test_attribute_type_enum")

    test_relationship_type_enum()
    print("✓ test_relationship_type_enum")

    print("\n✅ All tests passed!")
