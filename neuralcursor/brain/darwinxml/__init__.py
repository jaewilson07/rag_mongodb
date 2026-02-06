"""
DarwinXML integration with NeuralCursor brain.

Bridges the Docling ingestion pipeline with NeuralCursor's knowledge graph
and episodic memory systems.
"""

from .converter import DarwinXMLConverter
from .ingestion import DarwinXMLIngestionBridge

__all__ = ["DarwinXMLConverter", "DarwinXMLIngestionBridge"]
