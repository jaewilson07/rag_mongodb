"""
Main ingestion script for processing documents into MongoDB vector database.

This adapts the examples/ingestion/ingest.py pipeline to use MongoDB instead of PostgreSQL,
changing only the database layer while preserving all document processing logic.
"""

import os
import asyncio
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DocumentTooLarge
from dotenv import load_dotenv

from mdrag.ingestion.docling.chunker import (
    ChunkingConfig,
    DoclingChunks,
    create_chunker,
)
from mdrag.integrations.google_drive import parse_csv_values
from mdrag.ingestion.docling.processor import DocumentProcessor, ProcessedDocument
from mdrag.ingestion.embedder import create_embedder
from mdrag.ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from mdrag.ingestion.docling.darwinxml_storage import DarwinXMLStorage
from mdrag.ingestion.docling.darwinxml_validator import DarwinXMLValidator, ValidationStatus
from mdrag.mdrag_logging.service_logging import get_logger, log_async, setup_logging
from mdrag.settings import load_settings

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 2000
    max_tokens: int = 512
    enable_darwinxml: bool = False  # Enable DarwinXML semantic wrapper
    darwinxml_validate: bool = True  # Validate DarwinXML documents
    darwinxml_strict: bool = False  # Strict validation mode


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    errors: List[str]


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into MongoDB vector database."""

    @staticmethod
    def _sanitize_for_mongo(value: Any) -> Any:
        """Ensure values are compatible with MongoDB BSON encoding."""
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, int):
            min_int64 = -(2**63)
            max_int64 = 2**63 - 1
            if value < min_int64 or value > max_int64:
                return str(value)
            return value
        if isinstance(value, dict):
            return {k: DocumentIngestionPipeline._sanitize_for_mongo(v) for k, v in value.items()}
        if isinstance(value, list):
            return [DocumentIngestionPipeline._sanitize_for_mongo(v) for v in value]
        return value

    def __init__(
        self,
        config: IngestionConfig,
        documents_folder: str = "documents",
        clean_before_ingest: bool = False
    ):
        """
        Initialize ingestion pipeline.

        Args:
            config: Ingestion configuration
            documents_folder: Folder containing documents
            clean_before_ingest: Whether to clean existing data before ingestion
        """
        self.config = config
        self.documents_folder = documents_folder
        self.clean_before_ingest = clean_before_ingest

        # DarwinXML components (initialized if enabled)
        self.darwin_wrapper: Optional[DarwinXMLWrapper] = None
        self.darwin_storage: Optional[DarwinXMLStorage] = None
        self.darwin_validator: Optional[DarwinXMLValidator] = None

        # Load settings
        self.settings = load_settings()

        # Initialize MongoDB client and database references
        self.mongo_client: Optional[AsyncMongoClient] = None
        self.db: Optional[Any] = None

        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
            max_tokens=config.max_tokens
        )

        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()
        self.processor = DocumentProcessor(settings=self.settings)

        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize MongoDB connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        if self._initialized:
            return

        await logger.info("ingestion_pipeline_initialize_start", action="ingestion_pipeline_initialize_start")

        try:
            # Initialize MongoDB client
            self.mongo_client = AsyncMongoClient(
                self.settings.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.mongo_client[self.settings.mongodb_database]

            # Verify connection
            await self.mongo_client.admin.command("ping")

            # Initialize DarwinXML components if enabled
            if self.config.enable_darwinxml:
                await logger.info(
                    "darwin_initialization_start",
                    action="darwin_initialization_start",
                )
                
                chunks_collection = self.db[self.settings.mongodb_collection_chunks]
                
                self.darwin_wrapper = DarwinXMLWrapper(
                    embedding_model=self.settings.embedding_model,
                    enable_entity_extraction=True,
                    enable_category_tagging=True,
                )
                
                self.darwin_storage = DarwinXMLStorage(
                    chunks_collection=chunks_collection,
                )
                
                self.darwin_validator = DarwinXMLValidator(
                    strict_mode=self.config.darwinxml_strict,
                    require_annotations=True,
                    require_provenance=True,
                )
                
                await logger.info(
                    "darwin_initialization_complete",
                    action="darwin_initialization_complete",
                )
            await logger.info(
                "mongodb_connection_ready",
                action="mongodb_connection_ready",
                database=self.settings.mongodb_database,
            )

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            await logger.error(
                "mongodb_connection_failed",
                action="mongodb_connection_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        self._initialized = True
        await logger.info("ingestion_pipeline_initialized", action="ingestion_pipeline_initialized")

    async def close(self) -> None:
        """Close MongoDB connections."""
        if self._initialized and self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            self._initialized = False
            await logger.info("mongodb_connection_closed", action="mongodb_connection_closed")

    def _find_document_files(self) -> List[str]:
        """
        Find all supported document files in the documents folder.

        Returns:
            List of file paths
        """
        if not os.path.exists(self.documents_folder):
            log_async(
                logger,
                "error",
                "documents_folder_not_found",
                action="documents_folder_not_found",
                documents_folder=self.documents_folder,
            )
            return []

        # Supported file patterns - Docling + text formats + audio
        patterns = [
            "*.md", "*.markdown", "*.txt",  # Text formats
            "*.pdf",  # PDF
            "*.docx", "*.doc",  # Word
            "*.pptx", "*.ppt",  # PowerPoint
            "*.xlsx", "*.xls",  # Excel
            "*.html", "*.htm",  # HTML
            "*.mp3", "*.wav", "*.m4a", "*.flac",  # Audio formats
        ]
        files = []

        for pattern in patterns:
            files.extend(
                glob.glob(
                    os.path.join(self.documents_folder, "**", pattern),
                    recursive=True
                )
            )

        return sorted(files)

    async def _save_to_mongodb(
        self,
        title: str,
        source_url: str,
        content: str,
        chunks: List[DoclingChunks],
        metadata: Dict[str, Any],
        content_hash: str,
        docling_json: Optional[Dict[str, Any]] = None,
        page_texts: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Save document and chunks to MongoDB.

        Args:
            title: Document title
            source_url: Document source URL
            content: Document content
            chunks: List of document chunks with embeddings
            metadata: Document metadata
            content_hash: Hash used for idempotent updates
            docling_json: Serialized Docling document
            page_texts: Page number to text mapping

        Returns:
            Document ID (ObjectId as string)

        Raises:
            Exception: If MongoDB operations fail
        """
        # Get collection references
        documents_collection = self.db[
            self.settings.mongodb_collection_documents
        ]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        namespace = {
            key: metadata.get(key)
            for key in ("user_id", "org_id", "source_group")
            if metadata.get(key)
        }

        document_dict = {
            "title": title,
            "source_url": source_url,
            "source_type": metadata.get("source_type"),
            "content": content,
            "metadata": metadata,
            "content_hash": content_hash,
            "docling_json": docling_json or {},
            "page_texts": page_texts or {},
            "namespace": namespace,
            "updated_at": datetime.now(),
            "created_at": datetime.now(),
        }
        document_dict = self._sanitize_for_mongo(document_dict)

        existing = await documents_collection.find_one({"content_hash": content_hash})
        try:
            if existing:
                document_id = existing["_id"]
                await documents_collection.update_one(
                    {"_id": document_id},
                    {"$set": {**document_dict, "updated_at": datetime.now()}},
                )
                await chunks_collection.delete_many({"document_id": document_id})
                await logger.info(
                    "mongodb_document_updated",
                    action="mongodb_document_updated",
                    document_id=str(document_id),
                )
            else:
                document_result = await documents_collection.insert_one(document_dict)
                document_id = document_result.inserted_id
                await logger.info(
                    "mongodb_document_inserted",
                    action="mongodb_document_inserted",
                    document_id=str(document_id),
                )
        except DocumentTooLarge:
            await logger.warning(
                "mongodb_document_too_large",
                action="mongodb_document_too_large",
                title=title,
            )
            document_dict["docling_json"] = {}
            document_dict["page_texts"] = {}
            document_dict = self._sanitize_for_mongo(document_dict)
            if existing:
                document_id = existing["_id"]
                await documents_collection.update_one(
                    {"_id": document_id},
                    {"$set": {**document_dict, "updated_at": datetime.now()}},
                )
                await chunks_collection.delete_many({"document_id": document_id})
                await logger.info(
                    "mongodb_document_updated",
                    action="mongodb_document_updated",
                    document_id=str(document_id),
                )
            else:
                document_result = await documents_collection.insert_one(document_dict)
                document_id = document_result.inserted_id
                await logger.info(
                    "mongodb_document_inserted",
                    action="mongodb_document_inserted",
                    document_id=str(document_id),
                )

        # Insert chunks with embeddings as Python lists
        # If DarwinXML is enabled, use DarwinXML storage instead
        if self.config.enable_darwinxml and self.darwin_wrapper and self.darwin_storage:
            await self._save_chunks_with_darwinxml(
                chunks=chunks,
                document_id=str(document_id),
                content_hash=content_hash,
            )
        else:
            # Standard chunk storage
            chunk_dicts = []
            for chunk in chunks:
                chunk_metadata = self._build_chunk_metadata(metadata, chunk.metadata)
                chunk_dict = {
                    "document_id": document_id,
                    "content": chunk.content,
                    "embedding": chunk.embedding,  # Python list, NOT string!
                    "chunk_index": chunk.index,
                    "metadata": chunk_metadata,
                    "knowledge_base_id": str(document_id),
                    "token_count": chunk.token_count,
                    "summary_context": chunk_metadata.get("summary_context"),
                    "source_url": chunk_metadata.get("source_url"),
                    "source_type": chunk_metadata.get("source_type"),
                    "source_group": chunk_metadata.get("source_group"),
                    "source_mask": chunk_metadata.get("source_mask"),
                    "user_id": chunk_metadata.get("user_id"),
                    "org_id": chunk_metadata.get("org_id"),
                    "page_number": chunk_metadata.get("page_number"),
                    "heading_path": chunk_metadata.get("heading_path"),
                    "is_table": chunk_metadata.get("is_table"),
                    "content_hash": content_hash,
                    "created_at": datetime.now()
                }
                chunk_dicts.append(self._sanitize_for_mongo(chunk_dict))

            # Batch insert with ordered=False for partial success
            if chunk_dicts:
                await chunks_collection.insert_many(chunk_dicts, ordered=False)
            await logger.info(
                "mongodb_chunks_inserted",
                action="mongodb_chunks_inserted",
                chunk_count=len(chunk_dicts),
            )

        return str(document_id)

    async def _save_chunks_with_darwinxml(
        self,
        chunks: List[DoclingChunks],
        document_id: str,
        content_hash: str,
    ) -> None:
        """
        Save chunks with DarwinXML semantic wrapper.

        Args:
            chunks: List of DoclingChunks to wrap and store
            document_id: Document identifier
            content_hash: Content hash for deduplication
        """
        if not self.darwin_wrapper or not self.darwin_storage or not self.darwin_validator:
            await logger.error(
                "darwin_components_not_initialized",
                action="darwin_components_not_initialized",
            )
            return

        # Wrap chunks in DarwinXML format
        darwin_docs = self.darwin_wrapper.wrap_chunks_batch(
            chunks=chunks,
            document_id=document_id,
            validation_status=ValidationStatus.UNVALIDATED,
        )

        # Validate if enabled
        if self.config.darwinxml_validate:
            validation_results = self.darwin_validator.validate_batch(darwin_docs)
            
            valid_docs = []
            invalid_count = 0
            
            for darwin_doc in darwin_docs:
                result = validation_results.get(darwin_doc.id)
                if result and result.is_valid:
                    darwin_doc.provenance.validation_status = ValidationStatus.VALIDATED
                    valid_docs.append(darwin_doc)
                else:
                    invalid_count += 1
                    if result:
                        await logger.warning(
                            "darwin_validation_failed",
                            action="darwin_validation_failed",
                            chunk_uuid=darwin_doc.chunk_uuid,
                            errors=result.errors,
                            warnings=result.warnings,
                        )

            if invalid_count > 0:
                await logger.warning(
                    "darwin_validation_summary",
                    action="darwin_validation_summary",
                    total_chunks=len(darwin_docs),
                    invalid_count=invalid_count,
                )

            darwin_docs = valid_docs

        # Extract embeddings from chunks
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding]

        # Store DarwinXML documents
        doc_ids = await self.darwin_storage.store_darwin_documents_batch(
            darwin_docs=darwin_docs,
            embeddings=embeddings if embeddings else None,
            upsert=True,
        )

        await logger.info(
            "darwin_chunks_stored",
            action="darwin_chunks_stored",
            total_chunks=len(darwin_docs),
            document_id=document_id,
        )

        # Optionally log graph triples for Neo4j integration
        if darwin_docs:
            sample_doc = darwin_docs[0]
            triples = await self.darwin_storage.get_graph_triples(sample_doc)
            await logger.info(
                "darwin_graph_triples_sample",
                action="darwin_graph_triples_sample",
                chunk_uuid=sample_doc.chunk_uuid,
                triple_count=len(triples),
            )

    async def _clean_databases(self) -> None:
        """Clean existing data from MongoDB collections."""
        await logger.warning(
            "mongodb_cleanup_start",
            action="mongodb_cleanup_start",
        )

        # Get collection references
        documents_collection = self.db[
            self.settings.mongodb_collection_documents
        ]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Delete all chunks first (to respect FK relationships)
        chunks_result = await chunks_collection.delete_many({})
        await logger.info(
            "mongodb_chunks_deleted",
            action="mongodb_chunks_deleted",
            deleted_count=chunks_result.deleted_count,
        )

        # Delete all documents
        docs_result = await documents_collection.delete_many({})
        await logger.info(
            "mongodb_documents_deleted",
            action="mongodb_documents_deleted",
            deleted_count=docs_result.deleted_count,
        )

    @staticmethod
    def _build_chunk_metadata(
        document_metadata: Dict[str, Any],
        chunk_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge document + chunk metadata while enforcing required fields."""
        merged = {**document_metadata, **chunk_metadata}

        heading_path = chunk_metadata.get("heading_path") or document_metadata.get(
            "heading_path", []
        )
        if not isinstance(heading_path, list):
            heading_path = []

        merged["heading_path"] = heading_path
        merged["page_number"] = chunk_metadata.get("page_number") or document_metadata.get(
            "page_number"
        )
        merged["source_url"] = document_metadata.get("source_url")
        merged["source_type"] = document_metadata.get("source_type")
        merged["source_mask"] = document_metadata.get("source_mask")
        merged["user_id"] = document_metadata.get("user_id")
        merged["org_id"] = document_metadata.get("org_id")
        merged["source_group"] = document_metadata.get("source_group")
        merged["content_hash"] = document_metadata.get("content_hash")

        summary_context = chunk_metadata.get("summary_context")
        if not summary_context:
            title = (
                document_metadata.get("document_title")
                or document_metadata.get("title")
                or ""
            )
            summary_context = (
                f"{title} | {' > '.join(heading_path)}" if heading_path else title
            )
        merged["summary_context"] = summary_context
        merged["is_table"] = bool(chunk_metadata.get("is_table"))

        return merged

    async def _ingest_document_content(
        self,
        content: str,
        title: str,
        source_url: str,
        metadata: Dict[str, Any],
        docling_doc: Optional[Any] = None,
        docling_json: Optional[Dict[str, Any]] = None,
        page_texts: Optional[Dict[str, str]] = None,
        content_hash: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest document content into MongoDB.

        Args:
            content: Document content
            title: Document title
            source_url: Document source URL
            metadata: Document metadata
            docling_doc: Optional DoclingDocument for HierarchicalChunker
            docling_json: Optional serialized Docling document
            page_texts: Optional page-to-text mapping
            content_hash: Optional content hash for idempotent upsert

        Returns:
            Ingestion result
        """
        start_time = datetime.now()

        await logger.info(
            "document_processing_start",
            action="document_processing_start",
            title=title,
            source_url=source_url,
        )

        chunks = await self.chunker.chunk_document(
            content=content,
            title=title,
            source=source_url,
            metadata=metadata,
            docling_doc=docling_doc,
        )

        if not chunks:
            await logger.warning(
                "document_no_chunks",
                action="document_no_chunks",
                title=title,
                source_url=source_url,
            )
            return IngestionResult(
                document_id="",
                title=title,
                chunks_created=0,
                processing_time_ms=(
                    datetime.now() - start_time
                ).total_seconds() * 1000,
                errors=["No chunks created"],
            )

        await logger.info(
            "document_chunks_created",
            action="document_chunks_created",
            title=title,
            chunk_count=len(chunks),
        )

        embedded_chunks = await self.embedder.embed_chunks(chunks)
        await logger.info(
            "document_embeddings_generated",
            action="document_embeddings_generated",
            title=title,
            chunk_count=len(embedded_chunks),
        )

        document_id = await self._save_to_mongodb(
            title,
            source_url,
            content,
            embedded_chunks,
            metadata,
            content_hash or metadata.get("content_hash", ""),
            docling_json=docling_json,
            page_texts=page_texts,
        )

        await logger.info(
            "document_saved",
            action="document_saved",
            document_id=document_id,
            title=title,
        )

        processing_time = (
            datetime.now() - start_time
        ).total_seconds() * 1000

        return IngestionResult(
            document_id=document_id,
            title=title,
            chunks_created=len(embedded_chunks),
            processing_time_ms=processing_time,
            errors=[],
        )

    async def _ingest_single_document(
        self,
        file_path: str,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """
        Ingest a single document.

        Args:
            file_path: Path to the document file

        Returns:
            Ingestion result
        """
        processed = self.processor.process_local_file(
            file_path,
            namespace=namespace,
        )

        return await self._ingest_document_content(
            content=processed.content,
            title=processed.title,
            source_url=processed.source_url,
            metadata=processed.metadata,
            docling_doc=processed.docling_document,
            docling_json=processed.docling_json,
            page_texts=processed.page_texts,
            content_hash=processed.content_hash,
        )

    async def _ingest_processed_document(
        self,
        processed: ProcessedDocument,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """
        Ingest a pre-processed Docling document payload.

        Args:
            processed: ProcessedDocument from an IngestionSource
            namespace: Optional namespace overrides

        Returns:
            Ingestion result
        """
        metadata = dict(processed.metadata)
        if namespace:
            metadata.update(namespace)

        return await self._ingest_document_content(
            content=processed.content,
            title=processed.title,
            source_url=processed.source_url,
            metadata=metadata,
            docling_doc=processed.docling_document,
            docling_json=processed.docling_json,
            page_texts=processed.page_texts,
            content_hash=processed.content_hash,
        )

    async def _ingest_crawl4ai(
        self,
        urls: List[str],
        deep: bool = False,
        max_depth: Optional[int] = None,
        namespace: Optional[Dict[str, Any]] = None,
    ) -> List[IngestionResult]:
        """Ingest documents from Crawl4AI."""
        if not urls:
            return []

        results: List[IngestionResult] = []

        for url in urls:
            try:
                processed_docs = await self.processor.process_web_url(
                    url=url,
                    deep=deep,
                    max_depth=max_depth,
                    namespace=namespace,
                )
                for processed in processed_docs:
                    results.append(
                        await self._ingest_document_content(
                            content=processed.content,
                            title=processed.title,
                            source_url=processed.source_url,
                            metadata=processed.metadata,
                            docling_doc=processed.docling_document,
                            docling_json=processed.docling_json,
                            page_texts=processed.page_texts,
                            content_hash=processed.content_hash,
                        )
                    )

            except Exception as exc:
                await logger.error(
                    "crawl4ai_ingest_failed",
                    action="crawl4ai_ingest_failed",
                    url=url,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                results.append(
                    IngestionResult(
                        document_id="",
                        title=url,
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(exc)],
                    )
                )

        return results

    async def _ingest_google_drive(
        self,
        folder_ids: List[str],
        file_ids: List[str],
        doc_ids: List[str],
        namespace: Optional[Dict[str, Any]] = None,
    ) -> List[IngestionResult]:
        """Ingest documents from Google Drive/Docs."""
        if not (folder_ids or file_ids or doc_ids):
            return []

        if not self.settings.google_service_account_file:
            await logger.warning(
                "gdrive_service_account_missing",
                action="gdrive_service_account_missing",
            )
            return []

        results: List[IngestionResult] = []
        gathered_file_ids = list(file_ids)

        for folder_id in folder_ids:
            try:
                files = await self.processor.list_google_drive_files_in_folder(
                    folder_id
                )
                gathered_file_ids.extend([file["id"] for file in files])
            except Exception as exc:
                await logger.error(
                    "gdrive_folder_list_failed",
                    action="gdrive_folder_list_failed",
                    folder_id=folder_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        gathered_file_ids.extend(doc_ids)
        seen: set[str] = set()

        for file_id in gathered_file_ids:
            if file_id in seen:
                continue
            seen.add(file_id)
            try:
                processed = await self.processor.process_google_file(
                    file_id,
                    namespace=namespace,
                )
                results.append(
                    await self._ingest_document_content(
                        content=processed.content,
                        title=processed.title,
                        source_url=processed.source_url,
                        metadata=processed.metadata,
                        docling_doc=processed.docling_document,
                        docling_json=processed.docling_json,
                        page_texts=processed.page_texts,
                        content_hash=processed.content_hash,
                    )
                )

            except Exception as exc:
                await logger.error(
                    "gdrive_file_ingest_failed",
                    action="gdrive_file_ingest_failed",
                    file_id=file_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                results.append(
                    IngestionResult(
                        document_id="",
                        title=file_id,
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(exc)],
                    )
                )

        return results

    async def ingest_documents(
        self,
        progress_callback: Optional[callable] = None,
        crawl_urls: Optional[List[str]] = None,
        crawl_deep: bool = False,
        crawl_max_depth: Optional[int] = None,
        google_drive_folder_ids: Optional[List[str]] = None,
        google_drive_file_ids: Optional[List[str]] = None,
        google_docs_ids: Optional[List[str]] = None,
    ) -> List[IngestionResult]:
        """
        Ingest all documents from the documents folder.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            List of ingestion results
        """
        if not self._initialized:
            await self.initialize()

        # Clean existing data if requested
        if self.clean_before_ingest:
            await self._clean_databases()

        results: List[IngestionResult] = []

        # Crawl4AI ingestion
        crawl_urls = crawl_urls or []
        if crawl_urls:
            results.extend(
                await self._ingest_crawl4ai(
                    urls=crawl_urls,
                    deep=crawl_deep,
                    max_depth=crawl_max_depth,
                )
            )

        # Google Drive / Docs ingestion
        google_drive_folder_ids = google_drive_folder_ids or []
        google_drive_file_ids = google_drive_file_ids or []
        google_docs_ids = google_docs_ids or []
        if google_drive_folder_ids or google_drive_file_ids or google_docs_ids:
            results.extend(
                await self._ingest_google_drive(
                    folder_ids=google_drive_folder_ids,
                    file_ids=google_drive_file_ids,
                    doc_ids=google_docs_ids,
                )
            )

        # Find all supported document files
        document_files = self._find_document_files()

        if not document_files and not results:
            await logger.warning(
                "documents_folder_empty",
                action="documents_folder_empty",
                documents_folder=self.documents_folder,
            )
            return []

        if document_files:
            await logger.info(
                "documents_discovered",
                action="documents_discovered",
                document_count=len(document_files),
            )

            for i, file_path in enumerate(document_files):
                try:
                    await logger.info(
                        "document_file_processing_start",
                        action="document_file_processing_start",
                        index=i + 1,
                        total=len(document_files),
                        file_path=file_path,
                    )

                    result = await self._ingest_single_document(file_path)
                    results.append(result)

                    if progress_callback:
                        progress_callback(i + 1, len(document_files))

                except Exception as e:
                    await logger.error(
                        "document_file_processing_failed",
                        action="document_file_processing_failed",
                        file_path=file_path,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    results.append(IngestionResult(
                        document_id="",
                        title=os.path.basename(file_path),
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(e)]
                    ))

        # Log summary
        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)

        await logger.info(
            "ingestion_complete",
            action="ingestion_complete",
            document_count=len(results),
            chunk_count=total_chunks,
            error_count=total_errors,
        )

        return results


async def main() -> None:
    """Main function for running ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into MongoDB vector database"
    )
    parser.add_argument(
        "--documents", "-d",
        default="documents",
        help="Documents folder path"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning existing data before ingestion"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size for splitting documents"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Chunk overlap size"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens per chunk for embeddings"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--crawl-url",
        action="append",
        dest="crawl_urls",
        help="URL to crawl with Crawl4AI (repeatable)"
    )
    parser.add_argument(
        "--crawl-deep",
        action="store_true",
        help="Enable deep crawling for Crawl4AI URLs"
    )
    parser.add_argument(
        "--crawl-max-depth",
        type=int,
        default=None,
        help="Maximum depth for deep Crawl4AI crawl"
    )
    parser.add_argument(
        "--drive-folder-ids",
        type=str,
        default=None,
        help="Comma-separated Google Drive folder IDs"
    )
    parser.add_argument(
        "--drive-file-ids",
        type=str,
        default=None,
        help="Comma-separated Google Drive file IDs"
    )
    parser.add_argument(
        "--drive-doc-ids",
        type=str,
        default=None,
        help="Comma-separated Google Docs IDs"
    )
    parser.add_argument(
        "--enable-darwinxml",
        action="store_true",
        help="Enable DarwinXML semantic wrapper for chunks"
    )
    parser.add_argument(
        "--darwinxml-validate",
        action="store_true",
        default=True,
        help="Validate DarwinXML documents (default: True)"
    )
    parser.add_argument(
        "--darwinxml-strict",
        action="store_true",
        help="Enable strict validation mode (warnings become errors)"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else None
    await setup_logging(log_level=log_level or "INFO")

    # Create ingestion configuration
    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        max_tokens=args.max_tokens,
        enable_darwinxml=args.enable_darwinxml,
        darwinxml_validate=args.darwinxml_validate,
        darwinxml_strict=args.darwinxml_strict,
    )

    # Create and run pipeline - clean by default unless --no-clean is specified
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=not args.no_clean  # Clean by default
    )

    crawl_urls = args.crawl_urls or []
    drive_folder_ids = (
        parse_csv_values(args.drive_folder_ids)
        or parse_csv_values(pipeline.settings.google_drive_folder_ids)
    )
    drive_file_ids = (
        parse_csv_values(args.drive_file_ids)
        or parse_csv_values(pipeline.settings.google_drive_file_ids)
    )
    drive_doc_ids = (
        parse_csv_values(args.drive_doc_ids)
        or parse_csv_values(pipeline.settings.google_docs_ids)
    )

    def progress_callback(current: int, total: int) -> None:
        log_async(
            logger,
            "info",
            "ingestion_progress",
            action="ingestion_progress",
            current=current,
            total=total,
        )

    try:
        start_time = datetime.now()

        results = await pipeline.ingest_documents(
            progress_callback=progress_callback,
            crawl_urls=crawl_urls,
            crawl_deep=args.crawl_deep,
            crawl_max_depth=args.crawl_max_depth,
            google_drive_folder_ids=drive_folder_ids,
            google_drive_file_ids=drive_file_ids,
            google_docs_ids=drive_doc_ids,
        )

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)

        await logger.info(
            "ingestion_summary",
            action="ingestion_summary",
            documents_processed=len(results),
            total_chunks=total_chunks,
            total_errors=total_errors,
            total_processing_time_seconds=round(total_time, 2),
        )

        for result in results:
            await logger.info(
                "ingestion_result",
                action="ingestion_result",
                title=result.title,
                chunks_created=result.chunks_created,
                errors=result.errors,
                success=not result.errors,
            )

        await logger.info(
            "ingestion_next_steps",
            action="ingestion_next_steps",
            vector_index_name="vector_index",
            text_index_name="text_index",
            vector_index_collection="chunks",
            text_index_collection="chunks",
            vector_index_field="embedding",
            vector_index_dimensions=1536,
            text_index_field="content",
            reference_doc=".claude/reference/mongodb-patterns.md",
        )

    except KeyboardInterrupt:
        await logger.warning(
            "ingestion_interrupted",
            action="ingestion_interrupted",
        )
    except Exception as e:
        await logger.error(
            "ingestion_failed",
            action="ingestion_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
