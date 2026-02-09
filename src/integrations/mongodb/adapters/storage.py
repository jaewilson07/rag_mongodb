"""MongoDB storage adapter for ingestion (documents and chunks)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from mdrag.capabilities.ingestion.docling.chunker import DoclingChunks
from mdrag.capabilities.ingestion.docling.darwinxml_models import DarwinXMLDocument
from mdrag.capabilities.ingestion.docling.darwinxml_storage import DarwinXMLStorage
from mdrag.capabilities.ingestion.models import (
    IngestionConfig,
    IngestionDocument,
    StorageRepresentations,
    StorageResult,
)
from mdrag.capabilities.ingestion.protocols import StorageAdapter
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import Settings
from pymongo import AsyncMongoClient
from pymongo.errors import (
    ConnectionFailure,
    DocumentTooLarge,
    ServerSelectionTimeoutError,
)

logger = get_logger(__name__)


class MongoStorageAdapter(StorageAdapter):
    """MongoDB storage adapter for documents and chunks."""

    name = "mongodb"

    def __init__(
        self,
        *,
        settings: Settings,
        config: IngestionConfig,
        mongo_client: Optional[AsyncMongoClient] = None,
    ) -> None:
        """Initialize MongoDB storage adapter.

        Args:
            settings: Application settings.
            config: Ingestion configuration.
            mongo_client: Optional pre-configured Mongo client.
        """
        self.settings = settings
        self.config = config
        self.mongo_client = mongo_client
        self.db: Optional[Any] = None
        self._initialized = False
        self.darwin_storage: Optional[DarwinXMLStorage] = None

    async def initialize(self) -> None:
        """Initialize MongoDB connection and DarwinXML storage."""
        if self._initialized:
            return
        await logger.info(
            "mongodb_storage_initialize_start",
            action="mongodb_storage_initialize_start",
            database=self.settings.mongodb_database,
        )
        try:
            if not self.mongo_client:
                self.mongo_client = AsyncMongoClient(
                    self.settings.mongodb_connection_string,
                    serverSelectionTimeoutMS=5000,
                )
            self.db = self.mongo_client[self.settings.mongodb_database]
            await self.mongo_client.admin.command("ping")

            if self.config.enable_darwinxml and self.db:
                chunks_collection = self.db[self.settings.mongodb_collection_chunks]
                self.darwin_storage = DarwinXMLStorage(
                    chunks_collection=chunks_collection,
                )
            self._initialized = True
            await logger.info(
                "mongodb_storage_initialized",
                action="mongodb_storage_initialized",
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            await logger.error(
                "mongodb_storage_initialize_failed",
                action="mongodb_storage_initialize_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    async def close(self) -> None:
        """Close MongoDB connections."""
        if self._initialized and self.mongo_client:
            await self.mongo_client.close()
        self._initialized = False
        self.mongo_client = None
        self.db = None

    async def clean(self) -> None:
        """Delete all documents and chunks from MongoDB."""
        if not self._initialized:
            await self.initialize()
        if not self.db:
            return
        await logger.warning(
            "mongodb_cleanup_start",
            action="mongodb_cleanup_start",
        )
        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]
        chunks_result = await chunks_collection.delete_many({})
        await logger.info(
            "mongodb_chunks_deleted",
            action="mongodb_chunks_deleted",
            deleted_count=chunks_result.deleted_count,
        )
        docs_result = await documents_collection.delete_many({})
        await logger.info(
            "mongodb_documents_deleted",
            action="mongodb_documents_deleted",
            deleted_count=docs_result.deleted_count,
        )

    async def store(
        self,
        document: IngestionDocument,
        chunks: list[DoclingChunks],
        representations: StorageRepresentations,
        darwin_documents: list[DarwinXMLDocument],
    ) -> StorageResult:
        """Persist document and chunks into MongoDB."""
        if not self._initialized:
            await self.initialize()
        if not self.db:
            raise RuntimeError("MongoDB storage is not initialized")

        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        identity = document.metadata.identity
        namespace = document.metadata.namespace.model_dump(exclude_none=True)
        source_mask = self._source_type_to_mask(identity.source_type)

        document_payload = {
            "document_uid": identity.document_uid,
            "content_hash": identity.content_hash,
            "title": document.title,
            "source_url": identity.source_url,
            "source_type": identity.source_type,
            "source_id": identity.source_id,
            "source_mime_type": identity.source_mime_type,
            "content": document.content,
            "frontmatter": document.metadata.frontmatter.model_dump(exclude_none=True),
            "namespace": namespace,
            "ingestion_metadata": {
                "identity": identity.model_dump(),
                "namespace": namespace,
                "collected_at": document.metadata.collected_at,
                "ingested_at": document.metadata.ingested_at,
                "source_metadata": document.metadata.source_metadata,
            },
            "docling_json": representations.docling_json or {},
            "page_texts": document.page_texts or {},
            "updated_at": datetime.now(),
            "created_at": datetime.now(),
        }
        document_payload = self._sanitize_for_mongo(document_payload)

        existing = await documents_collection.find_one(
            {"document_uid": identity.document_uid}
        )
        try:
            if existing:
                document_id = existing["_id"]
                await documents_collection.update_one(
                    {"_id": document_id},
                    {"$set": {**document_payload, "updated_at": datetime.now()}},
                )
                await chunks_collection.delete_many(
                    {"document_uid": identity.document_uid}
                )
                await logger.info(
                    "mongodb_document_updated",
                    action="mongodb_document_updated",
                    document_uid=identity.document_uid,
                    document_id=str(document_id),
                )
            else:
                document_result = await documents_collection.insert_one(
                    document_payload
                )
                document_id = document_result.inserted_id
                await logger.info(
                    "mongodb_document_inserted",
                    action="mongodb_document_inserted",
                    document_uid=identity.document_uid,
                    document_id=str(document_id),
                )
        except DocumentTooLarge:
            await logger.warning(
                "mongodb_document_too_large",
                action="mongodb_document_too_large",
                title=document.title,
                document_uid=identity.document_uid,
            )
            document_payload["docling_json"] = {}
            document_payload["page_texts"] = {}
            document_payload = self._sanitize_for_mongo(document_payload)
            if existing:
                document_id = existing["_id"]
                await documents_collection.update_one(
                    {"_id": document_id},
                    {"$set": {**document_payload, "updated_at": datetime.now()}},
                )
                await chunks_collection.delete_many(
                    {"document_uid": identity.document_uid}
                )
            else:
                document_result = await documents_collection.insert_one(
                    document_payload
                )
                document_id = document_result.inserted_id

        if self.config.enable_darwinxml and darwin_documents:
            await self._store_darwin_documents(darwin_documents, chunks, document_id)
        else:
            chunk_docs = []
            for chunk in chunks:
                chunk_metadata = {
                    **chunk.metadata,
                    "source_mask": source_mask,
                }
                chunk_doc = {
                    "document_id": document_id,
                    "document_uid": identity.document_uid,
                    "content": chunk.content,
                    "embedding": chunk.embedding,
                    "chunk_index": chunk.index,
                    "metadata": chunk_metadata,
                    "passport": chunk.passport.model_dump(exclude_none=True),
                    "frontmatter": chunk.frontmatter.model_dump(exclude_none=True),
                    "token_count": chunk.token_count,
                    "summary_context": chunk_metadata.get("summary_context"),
                    "source_url": chunk.passport.source_url,
                    "source_type": chunk.passport.source_type,
                    "source_id": chunk.passport.source_id,
                    "source_group": chunk.passport.source_group,
                    "user_id": chunk.passport.user_id,
                    "org_id": chunk.passport.org_id,
                    "page_number": chunk.passport.page_number,
                    "heading_path": chunk.passport.heading_path,
                    "source_mask": source_mask,
                    "content_hash": identity.content_hash,
                    "created_at": datetime.now(),
                }
                chunk_docs.append(self._sanitize_for_mongo(chunk_doc))

            if chunk_docs:
                await chunks_collection.insert_many(chunk_docs, ordered=False)
            await logger.info(
                "mongodb_chunks_inserted",
                action="mongodb_chunks_inserted",
                chunk_count=len(chunk_docs),
            )

        return StorageResult(
            adapter=self.name,
            document_uid=identity.document_uid,
            document_id=str(document_id),
            chunk_count=len(chunks),
            metadata={
                "source_mask": source_mask,
                "graph_triple_count": len(representations.graph_triples),
            },
        )

    async def _store_darwin_documents(
        self,
        darwin_documents: list[DarwinXMLDocument],
        chunks: list[DoclingChunks],
        document_id: Any,
    ) -> None:
        """Persist DarwinXML documents into MongoDB."""
        if not self.darwin_storage:
            await logger.warning(
                "darwin_storage_missing",
                action="darwin_storage_missing",
            )
            return

        embedding_map = {chunk.index: chunk.embedding for chunk in chunks}
        embeddings = [embedding_map.get(doc.chunk_index) for doc in darwin_documents]
        embeddings_payload = (
            None if any(embedding is None for embedding in embeddings) else embeddings
        )
        await self.darwin_storage.store_darwin_documents_batch(
            darwin_docs=darwin_documents,
            embeddings=embeddings_payload,
            upsert=True,
            document_id=document_id,
        )
        await logger.info(
            "darwin_chunks_stored",
            action="darwin_chunks_stored",
            total_chunks=len(darwin_documents),
        )

    @staticmethod
    def _source_type_to_mask(source_type: str) -> int:
        mapping = {"web": 1, "gdrive": 2, "upload": 4}
        return mapping.get(source_type, 0)

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
            return {
                key: MongoStorageAdapter._sanitize_for_mongo(val)
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [MongoStorageAdapter._sanitize_for_mongo(val) for val in value]
        return value


__all__ = ["MongoStorageAdapter"]
