"""
NeuralCursor ingestion with DarwinXML integration.

Ingests documents through the Docling pipeline with DarwinXML semantic wrapper,
then stores them in the NeuralCursor brain (Neo4j + MongoDB).
"""

import argparse
import asyncio

# Add src to path for imports
import sys
from pathlib import Path

sys.path.insert(0, '/workspace/src')

from dotenv import load_dotenv

from ingestion.docling.chunker import ChunkingConfig, create_chunker
from ingestion.docling.darwinxml_validator import DarwinXMLValidator, ValidationStatus
from ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from ingestion.docling.processor import DoclingProcessor
from ingestion.embedder import create_embedder
from ingestion.models import UploadCollectionRequest
from ingestion.sources.upload_source import UploadCollector
from mdrag_logging.service_logging import get_logger, setup_logging
from neuralcursor.brain.darwinxml.ingestion import DarwinXMLIngestionBridge
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.settings import get_settings as get_neuralcursor_settings
from settings import load_settings

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
        self.processor = DoclingProcessor(settings=settings)
        self.collector = UploadCollector()
        
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
        
        # Collect source + process with Docling
        request = UploadCollectionRequest(
            filename=file_path.name,
            file_path=str(file_path),
        )
        sources = await self.collector.collect(request)
        if not sources:
            logger.warning(
                "neuralcursor_ingest_file_failed",
                extra={"file_path": str(file_path), "reason": "no_source"},
            )
            return {"success": False, "file": str(file_path), "error": "No source"}

        document = await self.processor.convert_source(sources[0])
        document_uid = document.metadata.identity.document_uid

        if not document.content.strip():
            logger.warning(
                "neuralcursor_ingest_file_failed",
                extra={
                    "file_path": str(file_path),
                    "document_uid": document_uid,
                    "reason": "no_content",
                },
            )
            return {"success": False, "file": str(file_path), "error": "No content"}

        # Chunk the document
        chunks = await self.chunker.chunk_document(document=document)
        
        if not chunks:
            logger.warning(
                "neuralcursor_ingest_file_no_chunks",
                extra={
                    "file_path": str(file_path),
                    "document_uid": document_uid,
                },
            )
            return {"success": False, "file": str(file_path), "error": "No chunks"}
        
        # Wrap chunks with DarwinXML
        darwin_docs = self.darwin_wrapper.wrap_chunks_batch(
            chunks=chunks,
            document_uid=document_uid,
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
                            "document_uid": document_uid,
                            "chunk_uuid": darwin_doc.chunk_uuid,
                            "errors": result.errors if result else [],
                        },
                    )
            
            darwin_docs = valid_docs
        
        # Align chunks with validated DarwinXML docs
        chunk_map = {chunk.index: chunk for chunk in chunks}
        aligned_docs = []
        aligned_chunks = []
        for darwin_doc in darwin_docs:
            chunk = chunk_map.get(darwin_doc.chunk_index)
            if not chunk:
                logger.warning(
                    "neuralcursor_chunk_missing",
                    extra={
                        "document_uid": document_uid,
                        "chunk_index": darwin_doc.chunk_index,
                    },
                )
                continue
            aligned_docs.append(darwin_doc)
            aligned_chunks.append(chunk)

        if not aligned_docs:
            logger.warning(
                "neuralcursor_ingest_file_no_valid_chunks",
                extra={
                    "file_path": str(file_path),
                    "document_uid": document_uid,
                },
            )
            return {
                "success": False,
                "file": str(file_path),
                "error": "No valid chunks",
            }

        # Generate embeddings with Docling metadata preserved
        embedded_chunks = await self.embedder.embed_chunks(aligned_chunks)
        embeddings = []
        for chunk in embedded_chunks:
            if chunk.embedding is None:
                raise ValueError("Missing embedding for chunk")
            embeddings.append(chunk.embedding)
        
        # Ingest into NeuralCursor brain
        stats = await self.bridge.ingest_darwin_documents_batch(
            darwin_docs=aligned_docs,
            embeddings=embeddings,
        )
        
        logger.info(
            "neuralcursor_ingest_file_complete",
            extra={
                "file_path": str(file_path),
                "document_uid": document_uid,
                "chunks": len(aligned_docs),
                "para_nodes": stats.para_nodes_created,
                "relationships": stats.relationships_created,
            },
        )
        
        return {
            "success": True,
            "file": str(file_path),
            "document_uid": document_uid,
            "chunks": len(aligned_docs),
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
        uri=nc_settings.mongodb_connection_string,
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
            print("\n✅ Ingestion complete:")
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
