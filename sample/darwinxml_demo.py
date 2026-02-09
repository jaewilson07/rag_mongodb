"""
DarwinXML Demo Script

Demonstrates the DarwinXML semantic wrapper for Docling chunks.
Shows how to:
1. Wrap DoclingChunks in DarwinXML format
2. Validate DarwinXML documents
3. Extract graph triples for Neo4j
4. Query by semantic tags and categories
"""

import asyncio
from typing import List

from mdrag.ingestion.docling.chunker import DoclingChunks
from mdrag.ingestion.docling.darwinxml_models import (
    ValidationStatus,
)
from mdrag.ingestion.docling.darwinxml_validator import (
    DarwinXMLValidator,
    validate_darwin_document,
)
from mdrag.ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from mdrag.ingestion.models import MetadataPassport
from mdrag.integrations.models import SourceFrontmatter
from mdrag.mdrag_logging.service_logging import get_logger, setup_logging

logger = get_logger(__name__)


async def create_sample_chunk(
    content: str,
    title: str,
    index: int = 0,
    heading_path: List[str] = None,
) -> DoclingChunks:
    """Create a sample DoclingChunk for demonstration."""
    passport = MetadataPassport(
        source_type="upload",
        source_url=f"file:///demo/{title}.md",
        document_title=title,
        page_number=1,
        heading_path=heading_path or [],
        ingestion_timestamp="2026-02-06T00:00:00",
        content_hash="demo_hash_123",
    )

    frontmatter = SourceFrontmatter(
        source_type="upload",
        source_url=f"file:///demo/{title}.md",
        source_title=title,
        metadata={"demo": True},
    )

    return DoclingChunks(
        frontmatter=frontmatter,
        content=content,
        index=index,
        start_char=0,
        end_char=len(content),
        passport=passport,
        token_count=len(content.split()),
        metadata={
            "chunk_method": "hierarchical",
            "is_table": False,
        },
    )


async def demo_basic_wrapping():
    """Demonstrate basic DarwinXML wrapping."""
    await logger.info("demo_basic_wrapping", action="demo_basic_wrapping")

    # Create sample chunk
    chunk = await create_sample_chunk(
        content="""# Sellaronda Bike Trip Planning

## Overview
The Sellaronda is a circular ski and bike route in the Dolomites, Italy.
This document contains planning notes for our #p/Sellaronda trip.

## Budget #status/verified
- Accommodation: €500
- Bike rental: €200
- Food: €300
- Total: €1000

This is marked as a verified estimate from local vendors.
""",
        title="Sellaronda Planning",
        heading_path=["Overview"],
    )

    # Create wrapper
    wrapper = DarwinXMLWrapper(
        embedding_model="text-embedding-3-small",
        enable_entity_extraction=True,
        enable_category_tagging=True,
    )

    # Wrap chunk
    darwin_doc = wrapper.wrap_chunk(
        chunk=chunk,
        document_id="doc_123",
        validation_status=ValidationStatus.UNVALIDATED,
        additional_tags=["trip", "planning"],
    )

    # Display results
    await logger.info(
        "darwin_document_created",
        action="darwin_document_created",
        chunk_uuid=darwin_doc.chunk_uuid,
        annotation_count=len(darwin_doc.annotations),
        tag_count=len(darwin_doc.provenance.tags),
    )

    # Show annotations
    for ann in darwin_doc.annotations:
        await logger.info(
            "darwin_annotation",
            action="darwin_annotation",
            type=ann.type.value,
            attribute_count=len(ann.attributes),
            relationship_count=len(ann.relationships),
        )

    # Show tags
    await logger.info(
        "darwin_tags",
        action="darwin_tags",
        tags=darwin_doc.provenance.tags,
    )

    # Show attributes
    for ann in darwin_doc.annotations:
        for attr in ann.attributes:
            await logger.info(
                "darwin_attribute",
                action="darwin_attribute",
                type=attr.type.value,
                name=attr.name,
                value=attr.value,
            )

    return darwin_doc


async def demo_validation():
    """Demonstrate DarwinXML validation."""
    await logger.info("demo_validation", action="demo_validation")

    # Create sample chunk
    chunk = await create_sample_chunk(
        content="This is a test chunk with minimal content.",
        title="Test Document",
    )

    # Create wrapper and wrap
    wrapper = DarwinXMLWrapper()
    darwin_doc = wrapper.wrap_chunk(chunk=chunk, document_id="test_doc")

    # Validate (basic mode)
    result = validate_darwin_document(darwin_doc, strict=False)

    await logger.info(
        "validation_result",
        action="validation_result",
        is_valid=result.is_valid,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
    )

    if result.errors:
        for error in result.errors:
            await logger.warning(
                "validation_error",
                action="validation_error",
                error=error,
            )

    if result.warnings:
        for warning in result.warnings:
            await logger.info(
                "validation_warning",
                action="validation_warning",
                warning=warning,
            )

    # Validate with strict mode
    validator = DarwinXMLValidator(strict_mode=True)
    strict_result = validator.validate(darwin_doc)

    await logger.info(
        "strict_validation_result",
        action="strict_validation_result",
        is_valid=strict_result.is_valid,
    )

    return result


async def demo_graph_triples():
    """Demonstrate graph triple extraction."""
    await logger.info("demo_graph_triples", action="demo_graph_triples")

    # Create multiple related chunks
    chunks = [
        await create_sample_chunk(
            content="# Introduction\nThis is the main document.",
            title="Main Document",
            index=0,
            heading_path=["Introduction"],
        ),
        await create_sample_chunk(
            content="## Section 1\nThis references the Subaru Forester maintenance schedule.",
            title="Main Document",
            index=1,
            heading_path=["Introduction", "Section 1"],
        ),
        await create_sample_chunk(
            content="### Maintenance Interval\nOil change every 6 months.",
            title="Main Document",
            index=2,
            heading_path=["Introduction", "Section 1", "Maintenance Interval"],
        ),
    ]

    # Create wrapper and wrap batch
    wrapper = DarwinXMLWrapper(enable_entity_extraction=True)
    darwin_docs = wrapper.wrap_chunks_batch(
        chunks=chunks,
        document_id="main_doc",
        additional_tags=["automotive", "maintenance"],
    )

    # Extract graph triples from first document
    darwin_doc = darwin_docs[0]
    triples = darwin_doc.extract_graph_triples()

    await logger.info(
        "graph_triples_extracted",
        action="graph_triples_extracted",
        triple_count=len(triples),
    )

    # Display triples
    for triple in triples:
        await logger.info(
            "graph_triple",
            action="graph_triple",
            subject=triple["subject"],
            predicate=triple["predicate"],
            object=triple["object"],
            properties=triple.get("properties", {}),
        )

    return triples


async def demo_xml_export():
    """Demonstrate XML export."""
    await logger.info("demo_xml_export", action="demo_xml_export")

    # Create sample chunk
    chunk = await create_sample_chunk(
        content="This is a sample document for XML export demonstration.",
        title="XML Export Demo",
        heading_path=["Main Section"],
    )

    # Wrap and export to XML
    wrapper = DarwinXMLWrapper()
    darwin_doc = wrapper.wrap_chunk(chunk=chunk, document_id="xml_demo")

    # Export to XML string
    xml_string = darwin_doc.to_xml()

    await logger.info(
        "xml_exported",
        action="xml_exported",
        xml_length=len(xml_string),
    )

    # Print first 500 characters
    print("\n=== DarwinXML Export ===")
    print(xml_string[:500])
    print("...\n")

    return xml_string


async def demo_batch_validation():
    """Demonstrate batch validation."""
    await logger.info("demo_batch_validation", action="demo_batch_validation")

    # Create multiple chunks
    chunks = [
        await create_sample_chunk(
            content=f"Chunk {i} with content",
            title=f"Document {i}",
            index=i,
        )
        for i in range(5)
    ]

    # Wrap all chunks
    wrapper = DarwinXMLWrapper()
    darwin_docs = wrapper.wrap_chunks_batch(
        chunks=chunks,
        document_id="batch_demo",
    )

    # Validate batch
    validator = DarwinXMLValidator()
    results = validator.validate_batch(darwin_docs)

    # Summary
    valid_count = sum(1 for r in results.values() if r.is_valid)
    invalid_count = len(results) - valid_count

    await logger.info(
        "batch_validation_summary",
        action="batch_validation_summary",
        total_documents=len(results),
        valid_count=valid_count,
        invalid_count=invalid_count,
    )

    # Show individual results
    for doc_id, result in results.items():
        await logger.info(
            "batch_validation_result",
            action="batch_validation_result",
            document_id=doc_id,
            is_valid=result.is_valid,
            error_count=len(result.errors),
        )

    return results


async def main():
    """Run all demonstrations."""
    await setup_logging(log_level="INFO")

    await logger.info(
        "darwinxml_demo_start",
        action="darwinxml_demo_start",
        message="Starting DarwinXML demonstration",
    )

    # Run demonstrations
    print("\n" + "=" * 60)
    print("DarwinXML Demonstration")
    print("=" * 60 + "\n")

    print("1. Basic Wrapping")
    print("-" * 60)
    _ = await demo_basic_wrapping()
    print()

    print("2. Validation")
    print("-" * 60)
    _ = await demo_validation()
    print()

    print("3. Graph Triple Extraction")
    print("-" * 60)
    _ = await demo_graph_triples()
    print()

    print("4. XML Export")
    print("-" * 60)
    _ = await demo_xml_export()
    print()

    print("5. Batch Validation")
    print("-" * 60)
    _ = await demo_batch_validation()
    print()

    await logger.info(
        "darwinxml_demo_complete",
        action="darwinxml_demo_complete",
        message="All demonstrations completed successfully",
    )

    print("=" * 60)
    print("Demonstration Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
