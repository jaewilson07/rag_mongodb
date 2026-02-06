"""
NeuralCursor ingestion with DarwinXML integration.

Ingests documents through the Docling pipeline with DarwinXML semantic wrapper,
then stores them in the NeuralCursor brain (Neo4j + MongoDB).
"""

import asyncio
import argparse
import logging
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
import sys
sys.path.insert(0, '/workspace/src')

from dotenv import load_dotenv

from ingestion.docling.chunker import ChunkingConfig, create_chunker
from ingestion.docling.processor import DocumentProcessor
from ingestion.embedder import create_embedder
from ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from ingestion.docling.darwinxml_validator import DarwinXMLValidator, ValidationStatus
from mdrag_logging.service_logging import get_logger, setup_logging
from settings import load_settings

from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.darwinxml.ingestion import DarwinXMLIngestionBridge
from neuralcursor.settings import get_settings as get_neuralcursor_settings

load_dotenv()

logger = get_logger(__name__)


class NeuralCursorIngestion:
    """
    Ingestion pipeline for NeuralCursor with DarwinXML.
    
    Flow:
    1. Process documents with Docling
    2. Chunk with HierarchicalChunker
    3. Wrap chunks with DarwinXML
    4. Validate DarwinXML documents
    5. Generate embeddings
    6. Store in Neo4j (graph) + MongoDB (content)
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        mongodb_client: MongoDBClient,
        enable_validation: bool = True,
        strict_validation: bool = False,
    ):
        """Initialize ingestion pipeline."""
        self.neo4j_client = neo4j_client
        self.mongodb_client = mongodb_client
        
        # Initialize components
        settings = load_settings()
        self.settings = settings
        
        self.chunker_config = ChunkingConfig(max_tokens=512)
        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()
        self.processor = DocumentProcessor(settings=settings)
        
        # DarwinXML components
        self.darwin_wrapper = DarwinXMLWrapper(
            embedding_model=settings.embedding_model,
            enable_entity_extraction=True,
            enable_category_tagging=True,
        )
        
        self.darwin_validator = DarwinXMLValidator(
            strict_mode=strict_validation,
            require_annotations=True,
            require_provenance=True,
        ) if enable_validation else None
        
        # Ingestion bridge
        self.bridge = DarwinXMLIngestionBridge(
            neo4j_client=neo4j_client,
            mongodb_client=mongodb_client,
        )

    async def ingest_file(self, file_path: Path) -> dict:
        """
        Ingest a single file.
        
        Args:
            file_path: Path to file to ingest
            
        Returns:
            Ingestion statistics
        """
        logger.info(
            "neuralcursor_ingest_file_start",
            extra={"file_path": str(file_path)},
        )
        
        # Process with Docling
        result = await self.processor.process_document(str(file_path))
        
        if not result or not result.markdown_content:
            logger.warning(
                "neuralcursor_ingest_file_failed",
                extra={"file_path": str(file_path), "reason": "no_content"},
            )
            return {"success": False, "file": str(file_path), "error": "No content"}
        
        # Chunk the document
        chunks = await self.chunker.chunk_document(
            content=result.markdown_content,
            title=file_path.stem,
            source=str(file_path),
            docling_doc=result.docling_document,
            metadata={
                "source_type": "upload",
                "document_title": file_path.stem,
            },
        )
        
        if not chunks:
            logger.warning(
                "neuralcursor_ingest_file_no_chunks",
                extra={"file_path": str(file_path)},
            )
            return {"success": False, "file": str(file_path), "error": "No chunks"}
        
        # Wrap chunks with DarwinXML
        darwin_docs = self.darwin_wrapper.wrap_chunks_batch(
            chunks=chunks,
            document_id=str(file_path),
            validation_status=ValidationStatus.UNVALIDATED,
            additional_tags=["neuralcursor", "ingestion"],
        )
        
        # Validate
        if self.darwin_validator:
            validation_results = self.darwin_validator.validate_batch(darwin_docs)
            
            valid_docs = []
            for darwin_doc in darwin_docs:
                result = validation_results.get(darwin_doc.id)
                if result and result.is_valid:
                    darwin_doc.provenance.validation_status = ValidationStatus.VALIDATED
                    valid_docs.append(darwin_doc)
                else:
                    logger.warning(
                        "neuralcursor_validation_failed",
                        extra={
                            "chunk_uuid": darwin_doc.chunk_uuid,
                            "errors": result.errors if result else [],
                        },
                    )
            
            darwin_docs = valid_docs
        
        # Generate embeddings
        texts = [chunk.content for chunk in chunks[:len(darwin_docs)]]
        embeddings = await self.embedder.embed_batch(texts)
        
        # Ingest into NeuralCursor brain
        stats = await self.bridge.ingest_darwin_documents_batch(
            darwin_docs=darwin_docs,
            embeddings=embeddings,
        )
        
        logger.info(
            "neuralcursor_ingest_file_complete",
            extra={
                "file_path": str(file_path),
                "chunks": len(darwin_docs),
                "para_nodes": stats.para_nodes_created,
                "relationships": stats.relationships_created,
            },
        )
        
        return {
            "success": True,
            "file": str(file_path),
            "chunks": len(darwin_docs),
            "para_nodes": stats.para_nodes_created,
            "relationships": stats.relationships_created,
            "errors": stats.errors,
        }

    async def ingest_directory(self, directory: Path) -> dict:
        """
        Ingest all supported files in a directory.
        
        Args:
            directory: Directory path
            
        Returns:
            Overall statistics
        """
        # Find all supported files
        patterns = ["*.md", "*.pdf", "*.docx", "*.txt", "*.html"]
        files = []
        for pattern in patterns:
            files.extend(directory.rglob(pattern))
        
        logger.info(
            "neuralcursor_ingest_directory_start",
            extra={"directory": str(directory), "file_count": len(files)},
        )
        
        total_chunks = 0
        total_para_nodes = 0
        total_relationships = 0
        errors = []
        
        for file_path in files:
            try:
                result = await self.ingest_file(file_path)
                
                if result["success"]:
                    total_chunks += result.get("chunks", 0)
                    total_para_nodes += result.get("para_nodes", 0)
                    total_relationships += result.get("relationships", 0)
                else:
                    errors.append(result.get("error", "Unknown error"))
                    
            except Exception as e:
                logger.exception(
                    "neuralcursor_ingest_file_exception",
                    extra={"file_path": str(file_path), "error": str(e)},
                )
                errors.append(f"{file_path}: {str(e)}")
        
        logger.info(
            "neuralcursor_ingest_directory_complete",
            extra={
                "directory": str(directory),
                "files_processed": len(files),
                "total_chunks": total_chunks,
                "total_para_nodes": total_para_nodes,
                "total_relationships": total_relationships,
                "errors": len(errors),
            },
        )
        
        return {
            "files_processed": len(files),
            "total_chunks": total_chunks,
            "total_para_nodes": total_para_nodes,
            "total_relationships": total_relationships,
            "errors": errors,
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into NeuralCursor with DarwinXML"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        required=True,
        help="Directory containing documents to ingest",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Single file to ingest (overrides directory)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Disable DarwinXML validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    await setup_logging(log_level=log_level)
    
    # Get NeuralCursor settings
    nc_settings = get_neuralcursor_settings()
    
    # Initialize Neo4j client
    neo4j_config = Neo4jConfig(
        uri=nc_settings.neo4j_uri,
        username=nc_settings.neo4j_username,
        password=nc_settings.neo4j_password,
        database=nc_settings.neo4j_database,
    )
    neo4j_client = Neo4jClient(neo4j_config)
    await neo4j_client.connect()
    
    # Initialize MongoDB client
    mongodb_config = MongoDBConfig(
        uri=nc_settings.mongodb_uri,
        database=nc_settings.mongodb_database,
    )
    mongodb_client = MongoDBClient(mongodb_config)
    await mongodb_client.connect()
    
    try:
        # Initialize ingestion pipeline
        ingestion = NeuralCursorIngestion(
            neo4j_client=neo4j_client,
            mongodb_client=mongodb_client,
            enable_validation=not args.no_validate,
            strict_validation=args.strict,
        )
        
        # Ingest
        if args.file:
            result = await ingestion.ingest_file(Path(args.file))
            print(f"\n✅ Ingestion complete: {result}")
        else:
            result = await ingestion.ingest_directory(Path(args.directory))
            print(f"\n✅ Ingestion complete:")
            print(f"   Files processed: {result['files_processed']}")
            print(f"   Total chunks: {result['total_chunks']}")
            print(f"   PARA nodes created: {result['total_para_nodes']}")
            print(f"   Relationships created: {result['total_relationships']}")
            if result['errors']:
                print(f"   Errors: {len(result['errors'])}")
                for error in result['errors'][:5]:
                    print(f"     - {error}")
        
    finally:
        # Cleanup
        await neo4j_client.close()
        await mongodb_client.close()


if __name__ == "__main__":
    asyncio.run(main())
