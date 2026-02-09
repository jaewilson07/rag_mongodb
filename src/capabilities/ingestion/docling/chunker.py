"""
Docling HierarchicalChunker implementation for structure-aware chunking.

This module uses Docling's HierarchicalChunker which:
- Preserves document hierarchy (headings, sections, tables)
- Respects semantic boundaries (paragraphs, lists)
- Is token-aware (fits embedding model limits)
- Provides heading paths for citation context
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from docling.chunking import HierarchicalChunker
from transformers import AutoTokenizer

from mdrag.capabilities.ingestion.models import IngestionDocument, MetadataPassport
from mdrag.integrations.models import Source, SourceFrontmatter
from mdrag.mdrag_logging.service_logging import get_logger, log_async

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for DoclingHierarchicalChunker."""

    chunk_size: int = 1000  # Target characters per chunk (used in fallback)
    chunk_overlap: int = 200  # Character overlap between chunks (used in fallback)
    max_chunk_size: int = 2000  # Maximum chunk size (used in fallback)
    min_chunk_size: int = 100  # Minimum chunk size (used in fallback)
    max_tokens: int = 512  # Maximum tokens for embedding models

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.min_chunk_size <= 0:
            raise ValueError("Minimum chunk size must be positive")


class DoclingChunks(Source):
    """Represents a document chunk with full metadata + optional embedding."""

    index: int
    start_char: int
    end_char: int
    token_count: Optional[int] = None
    embedding: Optional[List[float]] = None  # For embedder compatibility
    passport: MetadataPassport

    def model_post_init(self, __context: Any) -> None:
        """Calculate token count if not provided."""
        if self.token_count is None:
            # Rough estimation: ~4 characters per token
            self.token_count = len(self.content) // 4


class DoclingHierarchicalChunker:
    """
    Docling HierarchicalChunker wrapper for structure-aware document splitting.

    This chunker uses Docling's built-in HierarchicalChunker which:
    - Respects document structure (sections, paragraphs, tables)
    - Is token-aware (fits embedding model limits)
    - Preserves semantic coherence
    - Includes heading context in chunks
    """

    def __init__(self, config: ChunkingConfig) -> None:
        """
        Initialize chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config

        # Initialize tokenizer for token-aware chunking
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        log_async(
            logger,
            "info",
            "docling_tokenizer_init",
            action="docling_tokenizer_init",
            model_id=model_id,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Create HierarchicalChunker
        self.chunker = HierarchicalChunker(
            tokenizer=self.tokenizer,
            max_tokens=config.max_tokens,
            merge_peers=True,
        )

        log_async(
            logger,
            "info",
            "docling_chunker_initialized",
            action="docling_chunker_initialized",
            max_tokens=config.max_tokens,
        )

    async def chunk_document(self, document: IngestionDocument) -> List[DoclingChunks]:
        """Chunk a processed document using Docling's HierarchicalChunker.

        Args:
            document: Docling-processed ingestion document.

        Returns:
            List of document chunks with contextualized content.
        """
        if not document.content.strip():
            return []

        metadata = document.metadata
        base_metadata = {
            **metadata.source_metadata,
            "document_uid": metadata.identity.document_uid,
            "content_hash": metadata.identity.content_hash,
            "source_type": metadata.identity.source_type,
            "source_url": metadata.identity.source_url,
            "source_id": metadata.identity.source_id,
            "source_group": metadata.namespace.source_group,
            "user_id": metadata.namespace.user_id,
            "org_id": metadata.namespace.org_id,
            "document_title": document.title,
            "ingestion_timestamp": metadata.ingested_at,
            "chunk_method": "hierarchical",
        }

        docling_doc = document.docling_document
        if docling_doc is None:
            await logger.warning(
                "docling_chunker_fallback",
                action="docling_chunker_fallback",
                reason="no_docling_document",
            )
            return self._simple_fallback_chunk(document.content, base_metadata)

        try:
            # Use HierarchicalChunker to chunk the DoclingDocument
            chunk_iter = self.chunker.chunk(dl_doc=docling_doc)
            chunks = list(chunk_iter)

            # Convert Docling chunks to DoclingChunks objects
            document_chunks = []
            current_pos = 0

            for i, chunk in enumerate(chunks):
                # Get contextualized text (includes heading hierarchy)
                contextualized_text = self._contextualize(chunk)

                heading_path = self._extract_heading_path(chunk)
                page_number = self._extract_page_number(chunk)
                is_table = self._extract_is_table(chunk, contextualized_text)
                summary_context = self._build_summary_context(
                    title=document.title,
                    heading_path=heading_path,
                )
                embedding_text = None
                if is_table:
                    embedding_text = self._flatten_markdown_table(contextualized_text)

                # Count actual tokens
                token_count = len(self.tokenizer.encode(contextualized_text))

                passport = MetadataPassport(
                    document_uid=base_metadata.get("document_uid", ""),
                    source_type=base_metadata.get("source_type", "upload"),
                    source_url=base_metadata.get("source_url", ""),
                    source_id=base_metadata.get("source_id"),
                    source_group=base_metadata.get("source_group"),
                    user_id=base_metadata.get("user_id"),
                    org_id=base_metadata.get("org_id"),
                    document_title=base_metadata.get("document_title", document.title),
                    page_number=page_number or base_metadata.get("page_number"),
                    heading_path=heading_path or base_metadata.get("heading_path", []),
                    ingestion_timestamp=base_metadata.get(
                        "ingestion_timestamp", datetime.now().isoformat()
                    ),
                    content_hash=base_metadata.get("content_hash", ""),
                )
                frontmatter = metadata.frontmatter.model_copy(deep=True)
                frontmatter.metadata = {
                    **frontmatter.metadata,
                    "heading_path": heading_path,
                    "page_number": page_number,
                }

                # Create chunk metadata
                chunk_metadata = {
                    **base_metadata,
                    "total_chunks": len(chunks),
                    "token_count": token_count,
                    "has_context": True,
                    "heading_path": heading_path,
                    "heading_hierarchy": " > ".join(heading_path) if heading_path else None,
                    "page_number": page_number,
                    "summary_context": summary_context,
                    "is_table": is_table,
                    "raw_text": contextualized_text.strip(),
                    "embedding_text": embedding_text,
                }

                # Estimate character positions
                start_char = current_pos
                end_char = start_char + len(contextualized_text)

                document_chunks.append(
                    DoclingChunks(
                        frontmatter=frontmatter,
                        content=contextualized_text.strip(),
                        index=i,
                        start_char=start_char,
                        end_char=end_char,
                        metadata=chunk_metadata,
                        passport=passport,
                        token_count=token_count,
                    )
                )

                current_pos = end_char

            await logger.info(
                "docling_chunker_complete",
                action="docling_chunker_complete",
                chunk_count=len(document_chunks),
            )
            return document_chunks

        except Exception as exc:
            await logger.error(
                "docling_chunker_failed",
                action="docling_chunker_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return self._simple_fallback_chunk(document.content, base_metadata)

    @staticmethod
    def _build_summary_context(title: str, heading_path: list[str]) -> str:
        if heading_path:
            return f"{title} | {' > '.join(heading_path)}"
        return title

    def _contextualize(self, chunk: Any) -> str:
        """Get contextualized text from a Docling chunk."""
        try:
            return self.chunker.contextualize(chunk=chunk)
        except Exception:
            return getattr(chunk, "text", None) or str(chunk)

    def _extract_heading_path(self, chunk: Any) -> list[str]:
        """Extract heading path from a Docling chunk."""
        candidates = []
        if isinstance(chunk, dict):
            candidates.extend(
                [
                    chunk.get("heading_path"),
                    chunk.get("heading_hierarchy"),
                    chunk.get("path"),
                ]
            )
            metadata = chunk.get("metadata") or {}
            candidates.extend(
                [
                    metadata.get("heading_path"),
                    metadata.get("heading_hierarchy"),
                ]
            )
        else:
            for attr in (
                "heading_path",
                "heading_hierarchy",
                "path",
                "headings",
            ):
                candidates.append(getattr(chunk, attr, None))

            metadata = getattr(chunk, "metadata", None) or {}
            if isinstance(metadata, dict):
                candidates.extend(
                    [
                        metadata.get("heading_path"),
                        metadata.get("heading_hierarchy"),
                    ]
                )

        for candidate in candidates:
            if not candidate:
                continue
            if isinstance(candidate, str):
                return [part.strip() for part in candidate.split(">") if part.strip()]
            if isinstance(candidate, list):
                return [str(part).strip() for part in candidate if str(part).strip()]

        return []

    def _extract_page_number(self, chunk: Any) -> Optional[int]:
        """Extract page number from a Docling chunk if present."""
        if isinstance(chunk, dict):
            return chunk.get("page_number") or None

        for attr in ("page_number", "page_numbers"):
            value = getattr(chunk, attr, None)
            if isinstance(value, list) and value:
                return value[0]
            if isinstance(value, int):
                return value

        metadata = getattr(chunk, "metadata", None) or {}
        if isinstance(metadata, dict):
            page_value = metadata.get("page_number")
            if isinstance(page_value, int):
                return page_value

        return None

    def _extract_is_table(self, chunk: Any, content: str) -> bool:
        """Best-effort table detection for metadata tagging."""
        if isinstance(chunk, dict):
            value = chunk.get("is_table")
            if isinstance(value, bool):
                return value
            block_type = chunk.get("type") or chunk.get("block_type")
            if isinstance(block_type, str) and "table" in block_type.lower():
                return True
            metadata = chunk.get("metadata") or {}
            value = metadata.get("is_table")
            if isinstance(value, bool):
                return value

        for attr in ("is_table", "block_type", "type"):
            value = getattr(chunk, attr, None)
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and "table" in value.lower():
                return True

        metadata = getattr(chunk, "metadata", None) or {}
        if isinstance(metadata, dict):
            value = metadata.get("is_table")
            if isinstance(value, bool):
                return value

        # Markdown table heuristic
        if "|" in content and "---" in content:
            return True

        return False

    @staticmethod
    def _flatten_markdown_table(content: str) -> str:
        """Convert markdown tables into row-wise sentences for embeddings."""
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if len(lines) < 2:
            return content

        header = None
        rows: list[list[str]] = []
        for i, line in enumerate(lines):
            if "|" not in line:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if header is None and i + 1 < len(lines):
                separator = lines[i + 1]
                if "---" in separator:
                    header = cells
                    continue
            if header is not None:
                if line == lines[i - 1]:
                    continue
                rows.append(cells)

        if not header or not rows:
            return content

        sentences = []
        for row in rows:
            pairs = []
            for col, value in zip(header, row):
                if col and value:
                    pairs.append(f"{col}: {value}")
            if pairs:
                sentences.append("; ".join(pairs))

        return "\n".join(sentences) if sentences else content

    def _simple_fallback_chunk(
        self,
        content: str,
        base_metadata: Dict[str, Any],
    ) -> List[DoclingChunks]:
        """
        Simple fallback chunking when HierarchicalChunker can't be used.

        This is used when:
        - No DoclingDocument is provided
        - HierarchicalChunker fails

        Args:
            content: Content to chunk
            base_metadata: Base metadata for chunks

        Returns:
            List of document chunks
        """
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        # Simple sliding window approach
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + chunk_size

            if end >= len(content):
                # Last chunk
                chunk_text = content[start:]
            else:
                # Try to end at sentence boundary
                chunk_end = end
                for i in range(
                    end,
                    max(start + self.config.min_chunk_size, end - 200),
                    -1,
                ):
                    if i < len(content) and content[i] in ".!?\n":
                        chunk_end = i + 1
                        break
                chunk_text = content[start:chunk_end]
                end = chunk_end

            if chunk_text.strip():
                token_count = len(self.tokenizer.encode(chunk_text))
                summary_context = self._build_summary_context(
                    title=base_metadata.get("document_title", ""),
                    heading_path=[],
                )
                is_table = self._extract_is_table({}, chunk_text)
                embedding_text = (
                    self._flatten_markdown_table(chunk_text) if is_table else None
                )

                passport = MetadataPassport(
                    document_uid=base_metadata.get("document_uid", ""),
                    source_type=base_metadata.get("source_type", "upload"),
                    source_url=base_metadata.get("source_url", ""),
                    source_id=base_metadata.get("source_id"),
                    source_group=base_metadata.get("source_group"),
                    user_id=base_metadata.get("user_id"),
                    org_id=base_metadata.get("org_id"),
                    document_title=base_metadata.get("document_title", ""),
                    page_number=base_metadata.get("page_number"),
                    heading_path=base_metadata.get("heading_path", []),
                    ingestion_timestamp=base_metadata.get(
                        "ingestion_timestamp", datetime.now().isoformat()
                    ),
                    content_hash=base_metadata.get("content_hash", ""),
                )
                frontmatter = SourceFrontmatter(
                    source_type=passport.source_type,
                    source_url=passport.source_url,
                    source_title=passport.document_title,
                    metadata={
                        "heading_path": passport.heading_path,
                        "page_number": passport.page_number,
                    },
                )

                chunks.append(
                    DoclingChunks(
                        frontmatter=frontmatter,
                        content=chunk_text.strip(),
                        index=chunk_index,
                        start_char=start,
                        end_char=end,
                        metadata={
                            **base_metadata,
                            "chunk_method": "simple_fallback",
                            "total_chunks": -1,  # Will update after
                            "summary_context": summary_context,
                            "is_table": is_table,
                            "raw_text": chunk_text.strip(),
                            "embedding_text": embedding_text,
                        },
                        passport=passport,
                        token_count=token_count,
                    )
                )

                chunk_index += 1

            # Move forward with overlap
            start = end - overlap

        # Update total chunks
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        log_async(
            logger,
            "info",
            "docling_fallback_chunker_complete",
            action="docling_fallback_chunker_complete",
            chunk_count=len(chunks),
        )
        return chunks


def create_chunker(config: ChunkingConfig) -> DoclingHierarchicalChunker:
    """Create DoclingHierarchicalChunker for structure-aware splitting."""
    return DoclingHierarchicalChunker(config)
