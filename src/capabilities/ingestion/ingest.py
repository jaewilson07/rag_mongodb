"""
Ingestion workflow and CLI for MongoDB RAG Agent.

This module coordinates the collection, Docling processing, chunking,
embedding, and storage steps using standardized interfaces.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import glob
import os
from datetime import datetime
from typing import Callable, Optional, TypeVar

from dotenv import load_dotenv

from mdrag.capabilities.ingestion.docling.chunker import (
    ChunkingConfig,
    DoclingChunks,
    DoclingHierarchicalChunker,
)
from mdrag.capabilities.ingestion.docling.darwinxml_models import DarwinXMLDocument
from mdrag.capabilities.ingestion.docling.darwinxml_validator import (
    DarwinXMLValidator,
    ValidationStatus,
)
from mdrag.capabilities.ingestion.docling.darwinxml_wrapper import DarwinXMLWrapper
from mdrag.capabilities.ingestion.docling.processor import DoclingProcessor
from mdrag.capabilities.ingestion.embedder import EmbeddingGenerator, create_embedder
from pydantic import BaseModel

from mdrag.capabilities.ingestion.models import (
    CollectedSource,
    GoogleDriveCollectionRequest,
    GraphTriple,
    IngestionConfig,
    IngestionResult,
    Namespace,
    StorageRepresentations,
    UploadCollectionRequest,
    WebCollectionRequest,
)
from mdrag.capabilities.ingestion.protocols import SourceCollector, StorageAdapter
from mdrag.capabilities.ingestion.sources import Crawl4AICollector, GoogleDriveCollector, UploadCollector
from mdrag.integrations.mongodb.adapters.storage import MongoStorageAdapter
from mdrag.integrations.google_drive import parse_csv_values
from mdrag.mdrag_logging.service_logging import get_logger, log_async, setup_logging
from mdrag.settings import Settings, load_settings
from mdrag.validation import ValidationError
from mdrag.capabilities.ingestion.validation import validate_ingestion

load_dotenv()

logger = get_logger(__name__)

RequestT = TypeVar("RequestT", bound=BaseModel)


class IngestionWorkflow:
    """Coordinate collection, processing, and storage for ingestion."""

    def __init__(
        self,
        config: IngestionConfig,
        *,
        settings: Optional[Settings] = None,
        processor: Optional[DoclingProcessor] = None,
        chunker: Optional[DoclingHierarchicalChunker] = None,
        embedder: Optional[EmbeddingGenerator] = None,
        storage: Optional[StorageAdapter] = None,
    ) -> None:
        """Initialize the ingestion workflow.

        Args:
            config: Ingestion configuration.
            settings: Optional application settings.
            processor: Optional Docling processor override.
            chunker: Optional chunker override.
            embedder: Optional embedder override.
            storage: Optional storage adapter override.
        """
        self.settings = settings or load_settings()
        self.config = config
        self.processor = processor or DoclingProcessor(self.settings)
        self.chunker = chunker or DoclingHierarchicalChunker(
            ChunkingConfig(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                max_chunk_size=config.max_chunk_size,
                max_tokens=config.max_tokens,
            )
        )
        self.embedder = embedder or create_embedder()
        self.storage = storage or MongoStorageAdapter(
            settings=self.settings,
            config=config,
        )
        self.darwin_wrapper = (
            DarwinXMLWrapper(
                embedding_model=self.settings.embedding_model,
                enable_entity_extraction=True,
                enable_category_tagging=True,
            )
            if config.enable_darwinxml
            else None
        )
        self.darwin_validator = (
            DarwinXMLValidator(
                strict_mode=config.darwinxml_strict,
                require_annotations=True,
                require_provenance=True,
            )
            if config.enable_darwinxml
            else None
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize storage dependencies."""
        if self._initialized:
            return
        await logger.info(
            "ingestion_workflow_initialize_start",
            action="ingestion_workflow_initialize_start",
        )
        await self.storage.initialize()
        self._initialized = True
        await logger.info(
            "ingestion_workflow_initialized",
            action="ingestion_workflow_initialized",
        )

    async def close(self) -> None:
        """Close workflow dependencies."""
        await self.storage.close()
        await self.embedder.close()
        self._initialized = False

    async def ingest_collector(
        self,
        collector: SourceCollector[RequestT],
        request: RequestT,
    ) -> list[IngestionResult]:
        """Ingest sources from a collector request."""
        collector_name = getattr(collector, "name", collector.__class__.__name__)
        await validate_ingestion(
            self.settings,
            collectors=[collector_name],
            strict_mongodb=False,
            require_redis=False,
        )
        await logger.info(
            "ingestion_collect_start",
            action="ingestion_collect_start",
            collector=collector_name,
        )
        sources = await collector.collect(request)
        await logger.info(
            "ingestion_collect_complete",
            action="ingestion_collect_complete",
            collector=collector_name,
            collected_count=len(sources),
        )
        return await self.ingest_sources(sources)

    async def ingest_sources(
        self,
        sources: list[CollectedSource],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[IngestionResult]:
        """Ingest a list of collected sources."""
        if not sources:
            return []
        if not self._initialized:
            await self.initialize()

        results: list[IngestionResult] = []
        for index, source in enumerate(sources, start=1):
            result = await self._ingest_single_source(source)
            results.append(result)
            if progress_callback:
                progress_callback(index, len(sources))
        return results

    async def ingest_documents_folder(
        self,
        documents_folder: str,
        *,
        namespace: Optional[Namespace] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[IngestionResult]:
        """Ingest documents from a local folder using the upload collector."""
        files = self._find_document_files(documents_folder)
        if not files:
            return []
        collector = UploadCollector()
        sources: list[CollectedSource] = []
        for file_path in files:
            request = UploadCollectionRequest(
                filename=os.path.basename(file_path),
                file_path=file_path,
                namespace=namespace or Namespace(),
            )
            sources.extend(await collector.collect(request))
        return await self.ingest_sources(sources, progress_callback=progress_callback)

    async def _ingest_single_source(self, source: CollectedSource) -> IngestionResult:
        """Process, chunk, embed, and store a single source."""
        start_time = datetime.now()
        try:
            document = await self.processor.convert_source(source)
            await logger.info(
                "ingestion_document_processed",
                action="ingestion_document_processed",
                document_uid=document.metadata.identity.document_uid,
                title=document.title,
            )

            chunks = await self.chunker.chunk_document(document)
            if not chunks:
                await logger.warning(
                    "ingestion_no_chunks",
                    action="ingestion_no_chunks",
                    document_uid=document.metadata.identity.document_uid,
                    title=document.title,
                )
                return IngestionResult(
                    document_uid=document.metadata.identity.document_uid,
                    title=document.title,
                    chunks_created=0,
                    processing_time_ms=self._elapsed_ms(start_time),
                    errors=["No chunks created"],
                )

            embedded_chunks = await self.embedder.embed_chunks(chunks)
            await logger.info(
                "ingestion_embeddings_complete",
                action="ingestion_embeddings_complete",
                document_uid=document.metadata.identity.document_uid,
                chunk_count=len(embedded_chunks),
            )

            darwin_documents, graph_triples = await self._build_darwin_bundle(
                embedded_chunks,
                document.metadata.identity.document_uid,
            )

            representations = StorageRepresentations(
                markdown=document.content,
                docling_json=document.docling_json,
                graph_triples=graph_triples,
            )

            storage_result = await self.storage.store(
                document=document,
                chunks=embedded_chunks,
                representations=representations,
                darwin_documents=darwin_documents,
            )

            return IngestionResult(
                document_uid=document.metadata.identity.document_uid,
                title=document.title,
                chunks_created=len(embedded_chunks),
                processing_time_ms=self._elapsed_ms(start_time),
                storage_results=[storage_result],
                errors=[],
            )
        except Exception as exc:
            await logger.error(
                "ingestion_source_failed",
                action="ingestion_source_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return IngestionResult(
                document_uid="",
                title=source.frontmatter.source_title or source.frontmatter.source_url,
                chunks_created=0,
                processing_time_ms=self._elapsed_ms(start_time),
                errors=[str(exc)],
            )

    async def _build_darwin_bundle(
        self,
        chunks: list[DoclingChunks],
        document_uid: str,
    ) -> tuple[list[DarwinXMLDocument], list[GraphTriple]]:
        """Build DarwinXML documents and graph triples if enabled."""
        if not self.config.enable_darwinxml or not self.darwin_wrapper:
            return [], []

        darwin_docs = self.darwin_wrapper.wrap_chunks_batch(
            chunks=chunks,
            document_uid=document_uid,
            validation_status=ValidationStatus.UNVALIDATED,
        )

        if self.config.darwinxml_validate and self.darwin_validator:
            validation_results = self.darwin_validator.validate_batch(darwin_docs)
            valid_docs = []
            invalid_count = 0
            for darwin_doc in darwin_docs:
                result = validation_results.get(darwin_doc.id)
                if result and result.is_valid:
                    darwin_doc.provenance.validation_status = (
                        ValidationStatus.VALIDATED
                    )
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
            if invalid_count:
                await logger.warning(
                    "darwin_validation_summary",
                    action="darwin_validation_summary",
                    total_chunks=len(darwin_docs),
                    invalid_count=invalid_count,
                )
            darwin_docs = valid_docs

        graph_triples: list[GraphTriple] = []
        for darwin_doc in darwin_docs:
            graph_triples.extend(darwin_doc.extract_graph_triples())

        return darwin_docs, graph_triples

    @staticmethod
    def _elapsed_ms(start_time: datetime) -> float:
        return (datetime.now() - start_time).total_seconds() * 1000

    @staticmethod
    def _find_document_files(documents_folder: str) -> list[str]:
        """Find all supported document files in the documents folder."""
        if not os.path.exists(documents_folder):
            log_async(
                logger,
                "error",
                "documents_folder_not_found",
                action="documents_folder_not_found",
                documents_folder=documents_folder,
            )
            return []

        patterns = [
            "*.md",
            "*.markdown",
            "*.txt",
            "*.pdf",
            "*.docx",
            "*.doc",
            "*.pptx",
            "*.ppt",
            "*.xlsx",
            "*.xls",
            "*.html",
            "*.htm",
            "*.mp3",
            "*.wav",
            "*.m4a",
            "*.flac",
        ]
        files: list[str] = []
        for pattern in patterns:
            files.extend(
                glob.glob(os.path.join(documents_folder, "**", pattern), recursive=True)
            )
        return sorted(files)


async def main() -> None:
    """Main entrypoint for CLI ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into MongoDB vector database"
    )
    parser.add_argument(
        "--documents",
        "-d",
        default="documents",
        help="Documents folder path",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning existing data before ingestion",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Chunk size for splitting documents",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Chunk overlap size",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens per chunk for embeddings",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--crawl-url",
        action="append",
        dest="crawl_urls",
        help="URL to crawl with Crawl4AI (repeatable)",
    )
    parser.add_argument(
        "--crawl-deep",
        action="store_true",
        help="Enable deep crawling for Crawl4AI URLs",
    )
    parser.add_argument(
        "--crawl-max-depth",
        type=int,
        default=None,
        help="Maximum depth for deep Crawl4AI crawl",
    )
    parser.add_argument(
        "--drive-folder-ids",
        type=str,
        default=None,
        help="Comma-separated Google Drive folder IDs",
    )
    parser.add_argument(
        "--drive-file-ids",
        type=str,
        default=None,
        help="Comma-separated Google Drive file IDs",
    )
    parser.add_argument(
        "--drive-doc-ids",
        type=str,
        default=None,
        help="Comma-separated Google Docs IDs",
    )
    parser.add_argument(
        "--enable-darwinxml",
        action="store_true",
        help="Enable DarwinXML semantic wrapper for chunks",
    )
    parser.add_argument(
        "--darwinxml-validate",
        action="store_true",
        default=True,
        help="Validate DarwinXML documents (default: True)",
    )
    parser.add_argument(
        "--darwinxml-strict",
        action="store_true",
        help="Enable strict validation mode (warnings become errors)",
    )

    args = parser.parse_args()
    log_level = "DEBUG" if args.verbose else None
    await setup_logging(log_level=log_level or "INFO")

    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        max_tokens=args.max_tokens,
        enable_darwinxml=args.enable_darwinxml,
        darwinxml_validate=args.darwinxml_validate,
        darwinxml_strict=args.darwinxml_strict,
    )

    workflow = IngestionWorkflow(config=config)

    crawl_urls = args.crawl_urls or []
    drive_folder_ids = parse_csv_values(args.drive_folder_ids) or []
    drive_file_ids = parse_csv_values(args.drive_file_ids) or []
    drive_doc_ids = parse_csv_values(args.drive_doc_ids) or []

    # Pre-flight: validate core + collectors for requested sources
    collectors: list[str] = ["upload"]
    if crawl_urls:
        collectors.append("crawl4ai")
    if drive_folder_ids or drive_file_ids or drive_doc_ids:
        collectors.append("gdrive")
    collectors = list(dict.fromkeys(collectors))

    try:
        await validate_ingestion(
            workflow.settings,
            collectors=collectors,
            strict_mongodb=False,
            require_redis=False,
        )
    except ValidationError as e:
        await logger.error("ingestion_validation_failed", error=str(e))
        print(str(e), file=sys.stderr)
        sys.exit(1)

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
        if not args.no_clean:
            await workflow.storage.clean()

        results: list[IngestionResult] = []
        if crawl_urls:
            collector = Crawl4AICollector()
            for url in crawl_urls:
                results.extend(
                    await workflow.ingest_collector(
                        collector,
                        WebCollectionRequest(
                            url=url,
                            deep=args.crawl_deep,
                            max_depth=args.crawl_max_depth,
                        ),
                    )
                )

        if drive_folder_ids or drive_file_ids or drive_doc_ids:
            collector = GoogleDriveCollector()
            results.extend(
                await workflow.ingest_collector(
                    collector,
                    GoogleDriveCollectionRequest(
                        file_ids=drive_file_ids,
                        folder_ids=drive_folder_ids,
                        doc_ids=drive_doc_ids,
                    ),
                )
            )

        results.extend(
            await workflow.ingest_documents_folder(
                args.documents,
                progress_callback=progress_callback,
            )
        )

        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)
        await logger.info(
            "ingestion_complete",
            action="ingestion_complete",
            document_count=len(results),
            chunk_count=total_chunks,
            error_count=total_errors,
        )
    except KeyboardInterrupt:
        await logger.warning(
            "ingestion_interrupted",
            action="ingestion_interrupted",
        )
    finally:
        await workflow.close()


if __name__ == "__main__":
    asyncio.run(main())
