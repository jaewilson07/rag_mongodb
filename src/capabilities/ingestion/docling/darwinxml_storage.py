"""
Storage helpers for DarwinXML metadata in MongoDB.

Provides utilities for:
- Storing DarwinXML metadata alongside chunks
- Extracting graph triples for Neo4j
- Querying by semantic tags and attributes
- Managing DarwinXML document lifecycle
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from mdrag.capabilities.ingestion.docling.darwinxml_models import DarwinXMLDocument
from mdrag.capabilities.ingestion.models import GraphTriple
from mdrag.mdrag_logging.service_logging import get_logger

logger = get_logger(__name__)


class DarwinXMLStorage:
    """
    Storage manager for DarwinXML documents in MongoDB.

    This class handles:
    - Storing DarwinXML metadata with chunks
    - Upserting based on content_hash
    - Extracting graph data for Neo4j
    - Querying by tags, categories, and relationships
    """

    def __init__(
        self,
        chunks_collection: AsyncIOMotorCollection,
        darwin_metadata_collection: Optional[AsyncIOMotorCollection] = None,
    ):
        """
        Initialize storage manager.

        Args:
            chunks_collection: MongoDB collection for chunks
            darwin_metadata_collection: Optional separate collection for DarwinXML metadata
        """
        self.chunks_collection = chunks_collection
        self.darwin_metadata_collection = darwin_metadata_collection

    async def store_darwin_document(
        self,
        darwin_doc: DarwinXMLDocument,
        embedding: Optional[List[float]] = None,
        upsert: bool = True,
        document_id: Optional[Any] = None,
    ) -> str:
        """
        Store DarwinXML document with chunk data.

        Args:
            darwin_doc: DarwinXML document to store
            embedding: Optional embedding vector
            upsert: If True, update existing document with same content_hash
            document_id: Optional Mongo document ObjectId for lookup joins

        Returns:
            Inserted/updated document ID
        """
        # Build chunk document
        chunk_doc = self._darwin_to_chunk_document(
            darwin_doc,
            embedding,
            document_id,
        )

        # Upsert based on content_hash
        if upsert:
            content_hash = darwin_doc.provenance.content_hash
            filter_query = {"darwin_metadata.provenance.content_hash": content_hash}

            result = await self.chunks_collection.update_one(
                filter_query,
                {"$set": chunk_doc},
                upsert=True,
            )

            if result.upserted_id:
                await logger.info(
                    "darwin_document_inserted",
                    action="darwin_document_inserted",
                    document_id=str(result.upserted_id),
                    chunk_uuid=darwin_doc.chunk_uuid,
                )
                return str(result.upserted_id)
            else:
                await logger.info(
                    "darwin_document_updated",
                    action="darwin_document_updated",
                    chunk_uuid=darwin_doc.chunk_uuid,
                )
                return darwin_doc.chunk_uuid
        else:
            result = await self.chunks_collection.insert_one(chunk_doc)
            await logger.info(
                "darwin_document_inserted",
                action="darwin_document_inserted",
                document_id=str(result.inserted_id),
                chunk_uuid=darwin_doc.chunk_uuid,
            )
            return str(result.inserted_id)

    async def store_darwin_documents_batch(
        self,
        darwin_docs: List[DarwinXMLDocument],
        embeddings: Optional[List[List[float]]] = None,
        upsert: bool = True,
        document_id: Optional[Any] = None,
    ) -> List[str]:
        """
        Store a batch of DarwinXML documents.

        Args:
            darwin_docs: List of DarwinXML documents
            embeddings: Optional list of embedding vectors (same order as documents)
            upsert: If True, update existing documents
            document_id: Optional Mongo document ObjectId for lookup joins

        Returns:
            List of inserted/updated document IDs
        """
        doc_ids = []

        for i, darwin_doc in enumerate(darwin_docs):
            embedding = embeddings[i] if embeddings and i < len(embeddings) else None

            try:
                doc_id = await self.store_darwin_document(
                    darwin_doc=darwin_doc,
                    embedding=embedding,
                    upsert=upsert,
                    document_id=document_id,
                )
                doc_ids.append(doc_id)
            except Exception as e:
                await logger.error(
                    "darwin_storage_failed",
                    action="darwin_storage_failed",
                    chunk_uuid=darwin_doc.chunk_uuid,
                    error=str(e),
                )
                # Continue with other documents
                doc_ids.append("")

        await logger.info(
            "darwin_batch_stored",
            action="darwin_batch_stored",
            total_documents=len(darwin_docs),
            successful=len([d for d in doc_ids if d]),
        )

        return doc_ids

    async def get_graph_triples(
        self, darwin_doc: DarwinXMLDocument
    ) -> List[GraphTriple]:
        """
        Extract graph triples for Neo4j ingestion.

        Returns triples in format suitable for Neo4j Cypher queries:
        {
            "subject": "node_id",
            "predicate": "RELATIONSHIP_TYPE",
            "object": "target_node_id",
            "properties": {...}
        }

        Args:
            darwin_doc: DarwinXML document

        Returns:
            List of graph triples
        """
        return darwin_doc.extract_graph_triples()

    async def query_by_tags(
        self,
        tags: List[str],
        match_all: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query DarwinXML documents by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, require all tags; if False, match any tag
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        if match_all:
            # All tags must be present
            query = {"darwin_metadata.provenance.tags": {"$all": tags}}
        else:
            # Any tag matches
            query = {"darwin_metadata.provenance.tags": {"$in": tags}}

        cursor = self.chunks_collection.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        await logger.info(
            "darwin_query_by_tags",
            action="darwin_query_by_tags",
            tags=tags,
            match_all=match_all,
            result_count=len(results),
        )

        return results

    async def query_by_category(
        self,
        category: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query DarwinXML documents by PARA category.

        Args:
            category: Category to search (e.g., "para:project", "Project:MyProject")
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        # Search in attributes for category matches
        query = {
            "darwin_metadata.annotations.attributes": {
                "$elemMatch": {
                    "type": "category",
                    "value": {"$regex": category, "$options": "i"},
                }
            }
        }

        cursor = self.chunks_collection.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        await logger.info(
            "darwin_query_by_category",
            action="darwin_query_by_category",
            category=category,
            result_count=len(results),
        )

        return results

    async def query_by_entity(
        self,
        entity: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query DarwinXML documents mentioning an entity.

        Args:
            entity: Entity name to search
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        query = {
            "darwin_metadata.annotations.attributes": {
                "$elemMatch": {
                    "type": "entity",
                    "value": entity,
                }
            }
        }

        cursor = self.chunks_collection.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        await logger.info(
            "darwin_query_by_entity",
            action="darwin_query_by_entity",
            entity=entity,
            result_count=len(results),
        )

        return results

    async def query_by_validation_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query DarwinXML documents by validation status.

        Args:
            status: Validation status (validated, verified, unvalidated, rejected)
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        query = {"darwin_metadata.provenance.validation_status": status}

        cursor = self.chunks_collection.find(query).limit(limit)
        results = await cursor.to_list(length=limit)

        await logger.info(
            "darwin_query_by_status",
            action="darwin_query_by_status",
            status=status,
            result_count=len(results),
        )

        return results

    async def update_validation_status(
        self,
        chunk_uuid: str,
        new_status: str,
    ) -> bool:
        """
        Update validation status for a DarwinXML document.

        Args:
            chunk_uuid: UUID of chunk to update
            new_status: New validation status

        Returns:
            True if updated successfully
        """
        result = await self.chunks_collection.update_one(
            {"darwin_metadata.chunk_uuid": chunk_uuid},
            {
                "$set": {
                    "darwin_metadata.provenance.validation_status": new_status,
                    "darwin_metadata.provenance.updated_at": datetime.now().isoformat(),
                }
            },
        )

        if result.modified_count > 0:
            await logger.info(
                "darwin_status_updated",
                action="darwin_status_updated",
                chunk_uuid=chunk_uuid,
                new_status=new_status,
            )
            return True

        return False

    def _darwin_to_chunk_document(
        self,
        darwin_doc: DarwinXMLDocument,
        embedding: Optional[List[float]] = None,
        document_id: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Convert DarwinXML document to MongoDB chunk document.

        The DarwinXML metadata is stored in a 'darwin_metadata' field,
        while the standard chunk fields remain accessible for compatibility.
        """
        chunk_doc = {
            "chunk_uuid": darwin_doc.chunk_uuid,
            "content": darwin_doc.content,
            "document_title": darwin_doc.document_title,
            "chunk_index": darwin_doc.chunk_index,
            "embedding": embedding,
            "darwin_metadata": darwin_doc.to_dict(),
            "created_at": datetime.now().isoformat(),
        }

        if document_id is not None:
            chunk_doc["document_id"] = document_id

        # Add searchable fields from DarwinXML
        chunk_doc["tags"] = darwin_doc.provenance.tags
        chunk_doc["source_url"] = darwin_doc.provenance.source_url
        chunk_doc["source_type"] = darwin_doc.provenance.source_type
        chunk_doc["source_mask"] = self._source_type_to_mask(
            darwin_doc.provenance.source_type
        )
        chunk_doc["validation_status"] = darwin_doc.provenance.validation_status.value
        chunk_doc["content_hash"] = darwin_doc.provenance.content_hash
        chunk_doc["document_uid"] = darwin_doc.provenance.document_uid
        chunk_doc["source_id"] = darwin_doc.provenance.source_id
        chunk_doc["source_group"] = darwin_doc.provenance.source_group
        chunk_doc["user_id"] = darwin_doc.provenance.user_id
        chunk_doc["org_id"] = darwin_doc.provenance.org_id

        # Extract attributes for easy querying
        all_attributes = []
        for ann in darwin_doc.annotations:
            for attr in ann.attributes:
                all_attributes.append(
                    {
                        "type": attr.type.value,
                        "name": attr.name,
                        "value": attr.value,
                    }
                )
        chunk_doc["attributes"] = all_attributes

        # Extract heading path for hierarchical queries
        if darwin_doc.annotations:
            main_ann = darwin_doc.annotations[0]
            chunk_doc["heading_path"] = main_ann.metadata.get("heading_path", [])
            chunk_doc["page_number"] = main_ann.metadata.get("page_number")

        return chunk_doc

    @staticmethod
    def _source_type_to_mask(source_type: str) -> int:
        mapping = {"web": 1, "gdrive": 2, "upload": 4}
        return mapping.get(source_type, 0)


__all__ = ["DarwinXMLStorage"]
