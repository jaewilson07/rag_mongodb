"""
Document embedding generation for vector search.
"""

from typing import List, Optional
from datetime import datetime

from mdrag.capabilities.ingestion.docling.chunker import DoclingChunks
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.config.settings import Settings, load_settings
from mdrag.capabilities.retrieval.embeddings import EmbeddingClient

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for document chunks."""

    def __init__(
        self,
        model: Optional[str] = None,
        batch_size: int = 100,
        settings: Optional[Settings] = None,
        client: Optional[EmbeddingClient] = None,
    ):
        """
        Initialize embedding generator.

        Args:
            model: Embedding model to use
            batch_size: Number of texts to process in parallel
        """
        self.settings = settings or load_settings()
        self.model = model or self.settings.embedding_model
        self.batch_size = batch_size
        self.client = client or EmbeddingClient(settings=self.settings, model=self.model)

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        return await self.client.embed_text(text)

    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return await self.client.embed_texts(texts)

    async def embed_chunks(
        self,
        chunks: List[DoclingChunks],
        progress_callback: Optional[callable] = None
    ) -> List[DoclingChunks]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of document chunks
            progress_callback: Optional callback for progress updates

        Returns:
            Chunks with embeddings added
        """
        if not chunks:
            return chunks

        await logger.info(
            "embedding_generation_start",
            action="embedding_generation_start",
            chunk_count=len(chunks),
            batch_size=self.batch_size,
            model=self.model,
        )

        # Process chunks in batches
        embedded_chunks = []
        total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(chunks), self.batch_size):
            batch_chunks = chunks[i:i + self.batch_size]
            batch_texts = [
                (chunk.metadata.get("embedding_text") or chunk.content)
                if chunk.metadata
                else chunk.content
                for chunk in batch_chunks
            ]

            # Generate embeddings for this batch
            embeddings = await self.generate_embeddings_batch(batch_texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(batch_chunks, embeddings):
                embedded_chunk = DoclingChunks(
                    frontmatter=chunk.frontmatter,
                    content=chunk.content,
                    index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata={
                        **chunk.metadata,
                        "embedding_model": self.model,
                        "embedding_generated_at": datetime.now().isoformat()
                    },
                    passport=chunk.passport,
                    token_count=chunk.token_count
                )
                embedded_chunk.embedding = embedding
                embedded_chunks.append(embedded_chunk)

            # Progress update
            current_batch = (i // self.batch_size) + 1
            if progress_callback:
                progress_callback(current_batch, total_batches)

            await logger.debug(
                "embedding_batch_complete",
                action="embedding_batch_complete",
                batch=current_batch,
                total_batches=total_batches,
            )

        await logger.info(
            "embedding_generation_complete",
            action="embedding_generation_complete",
            chunk_count=len(embedded_chunks),
            model=self.model,
        )
        return embedded_chunks

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query

        Returns:
            Query embedding
        """
        return await self.generate_embedding(query)

    async def close(self) -> None:
        """Close the embedding client."""
        await self.client.close()

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        return self.client.embedding_dimension()


def create_embedder(model: Optional[str] = None, **kwargs) -> EmbeddingGenerator:
    """
    Create embedding generator.

    Args:
        model: Embedding model to use
        **kwargs: Additional arguments for EmbeddingGenerator

    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model=model, **kwargs)
