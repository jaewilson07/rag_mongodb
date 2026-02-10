"""Docling compatibility redirect package."""

from mdrag.capabilities.ingestion.docling import *

__all__ = [
    "ChunkingConfig",
    "DoclingChunks",
    "DoclingHierarchicalChunker",
    "create_chunker",
]
