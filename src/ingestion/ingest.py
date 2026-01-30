"""
Main ingestion script for processing documents into MongoDB vector database.

This adapts the examples/ingestion/ingest.py pipeline to use MongoDB instead of PostgreSQL,
changing only the database layer while preserving all document processing logic.
"""

import os
import asyncio
import logging
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

from src.ingestion.chunker import ChunkingConfig, create_chunker, DocumentChunk
from src.ingestion.google_drive import parse_csv_values
from src.ingestion.processor import DocumentProcessor
from src.ingestion.embedder import create_embedder
from src.logging_config import configure_logging
from src.settings import load_settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 2000
    max_tokens: int = 512


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

        logger.info("Initializing ingestion pipeline...")

        try:
            # Initialize MongoDB client
            self.mongo_client = AsyncMongoClient(
                self.settings.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.mongo_client[self.settings.mongodb_database]

            # Verify connection
            await self.mongo_client.admin.command("ping")
            logger.info(
                f"Connected to MongoDB database: {self.settings.mongodb_database}"
            )

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.exception("mongodb_connection_failed", error=str(e))
            raise

        self._initialized = True
        logger.info("Ingestion pipeline initialized")

    async def close(self) -> None:
        """Close MongoDB connections."""
        if self._initialized and self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            self._initialized = False
            logger.info("MongoDB connection closed")

    def _find_document_files(self) -> List[str]:
        """
        Find all supported document files in the documents folder.

        Returns:
            List of file paths
        """
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
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
        chunks: List[DocumentChunk],
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

        existing = await documents_collection.find_one({"content_hash": content_hash})
        if existing:
            document_id = existing["_id"]
            await documents_collection.update_one(
                {"_id": document_id},
                {"$set": {**document_dict, "updated_at": datetime.now()}},
            )
            await chunks_collection.delete_many({"document_id": document_id})
            logger.info("Updated document with ID: %s", document_id)
        else:
            document_result = await documents_collection.insert_one(document_dict)
            document_id = document_result.inserted_id
            logger.info("Inserted document with ID: %s", document_id)

        # Insert chunks with embeddings as Python lists
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
            chunk_dicts.append(chunk_dict)

        # Batch insert with ordered=False for partial success
        if chunk_dicts:
            await chunks_collection.insert_many(chunk_dicts, ordered=False)
            logger.info(f"Inserted {len(chunk_dicts)} chunks")

        return str(document_id)

    async def _clean_databases(self) -> None:
        """Clean existing data from MongoDB collections."""
        logger.warning("Cleaning existing data from MongoDB...")

        # Get collection references
        documents_collection = self.db[
            self.settings.mongodb_collection_documents
        ]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Delete all chunks first (to respect FK relationships)
        chunks_result = await chunks_collection.delete_many({})
        logger.info(f"Deleted {chunks_result.deleted_count} chunks")

        # Delete all documents
        docs_result = await documents_collection.delete_many({})
        logger.info(f"Deleted {docs_result.deleted_count} documents")

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

        logger.info(f"Processing document: {title}")

        chunks = await self.chunker.chunk_document(
            content=content,
            title=title,
            source=source_url,
            metadata=metadata,
            docling_doc=docling_doc,
        )

        if not chunks:
            logger.warning(f"No chunks created for {title}")
            return IngestionResult(
                document_id="",
                title=title,
                chunks_created=0,
                processing_time_ms=(
                    datetime.now() - start_time
                ).total_seconds() * 1000,
                errors=["No chunks created"],
            )

        logger.info(f"Created {len(chunks)} chunks")

        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

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

        logger.info(f"Saved document to MongoDB with ID: {document_id}")

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
                logger.exception(f"Failed to crawl {url}: {exc}")
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
            logger.warning("Google service account file not configured")
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
                logger.exception(f"Failed to list folder {folder_id}: {exc}")

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
                logger.exception(f"Failed to ingest Google file {file_id}: {exc}")
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
            logger.warning(
                f"No supported document files found in {self.documents_folder}"
            )
            return []

        if document_files:
            logger.info(f"Found {len(document_files)} document files to process")

            for i, file_path in enumerate(document_files):
                try:
                    logger.info(
                        f"Processing file {i+1}/{len(document_files)}: {file_path}"
                    )

                    result = await self._ingest_single_document(file_path)
                    results.append(result)

                    if progress_callback:
                        progress_callback(i + 1, len(document_files))

                except Exception as e:
                    logger.exception(f"Failed to process {file_path}: {e}")
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

        logger.info(
            f"Ingestion complete: {len(results)} documents, "
            f"{total_chunks} chunks, {total_errors} errors"
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

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else None
    configure_logging(log_level)

    # Create ingestion configuration
    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        max_tokens=args.max_tokens
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
        print(f"Progress: {current}/{total} documents processed")

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

        # Print summary
        print("\n" + "="*50)
        print("INGESTION SUMMARY")
        print("="*50)
        print(f"Documents processed: {len(results)}")
        print(f"Total chunks created: {sum(r.chunks_created for r in results)}")
        print(f"Total errors: {sum(len(r.errors) for r in results)}")
        print(f"Total processing time: {total_time:.2f} seconds")
        print()

        # Print individual results
        for result in results:
            status = "[OK]" if not result.errors else "[FAILED]"
            print(f"{status} {result.title}: {result.chunks_created} chunks")

            if result.errors:
                for error in result.errors:
                    print(f"  Error: {error}")

        # Print next steps
        print("\n" + "="*50)
        print("NEXT STEPS")
        print("="*50)
        print("1. Create vector search index in Atlas UI:")
        print("   - Index name: vector_index")
        print("   - Collection: chunks")
        print("   - Field: embedding")
        print("   - Dimensions: 1536 (for text-embedding-3-small)")
        print()
        print("2. Create text search index in Atlas UI:")
        print("   - Index name: text_index")
        print("   - Collection: chunks")
        print("   - Field: content")
        print()
        print("See .claude/reference/mongodb-patterns.md for detailed instructions")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user")
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
