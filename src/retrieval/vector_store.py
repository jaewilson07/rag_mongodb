"""Vector store utilities for parent-child hydration and cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from bson import ObjectId
from pymongo import AsyncMongoClient

from mdrag.settings import Settings


@dataclass
class VectorStore:
    """MongoDB-backed vector storage helpers."""

    settings: Settings
    mongo_client: Optional[AsyncMongoClient] = None

    async def initialize(self) -> None:
        if not self.mongo_client:
            self.mongo_client = AsyncMongoClient(
                self.settings.mongodb_uri,
                serverSelectionTimeoutMS=5000,
            )

    async def close(self) -> None:
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None

    async def purge_source(self, source_id: str) -> Dict[str, int]:
        """Delete all vectors/documents for a source ID or URL."""
        await self.initialize()
        db = self.mongo_client[self.settings.mongodb_database]
        documents = db[self.settings.mongodb_collection_documents]
        chunks = db[self.settings.mongodb_collection_chunks]

        doc_filter = {
            "$or": [
                {"source_url": source_id},
                {"metadata.source_url": source_id},
                {"metadata.gdrive_file_id": source_id},
                {"metadata.crawl_url": source_id},
                {"metadata.source_group": source_id},
            ]
        }

        doc_ids = [doc["_id"] async for doc in documents.find(doc_filter, {"_id": 1})]
        chunk_filter = {
            "$or": [
                {"document_id": {"$in": doc_ids}} if doc_ids else {"_id": None},
                {"source_url": source_id},
                {"metadata.source_url": source_id},
                {"metadata.gdrive_file_id": source_id},
                {"metadata.crawl_url": source_id},
                {"metadata.source_group": source_id},
            ]
        }

        chunk_result = await chunks.delete_many(chunk_filter)
        doc_result = await documents.delete_many(doc_filter)

        return {
            "documents_deleted": doc_result.deleted_count,
            "chunks_deleted": chunk_result.deleted_count,
        }

    async def get_parent_page_text(self, chunk_id: str) -> Optional[str]:
        """Return page text for a chunk ID using stored page_texts."""
        await self.initialize()
        db = self.mongo_client[self.settings.mongodb_database]
        documents = db[self.settings.mongodb_collection_documents]
        chunks = db[self.settings.mongodb_collection_chunks]

        chunk = await chunks.find_one({"_id": ObjectId(chunk_id)})
        if not chunk:
            return None

        page_number = (
            chunk.get("page_number")
            or (chunk.get("metadata") or {}).get("page_number")
        )
        document = await documents.find_one({"_id": chunk.get("document_id")})
        if not document:
            return None

        page_texts = document.get("page_texts", {})
        if page_number is not None:
            return page_texts.get(str(page_number))

        return document.get("content")