"""Protocol for all ingestion sources to standardize Docling handoff."""

from typing import Protocol

from mdrag.ingestion.docling.processor import ProcessedDocument

class IngestionSource(Protocol):
    def fetch_and_convert(self, **kwargs) -> ProcessedDocument:
        """
        Fetches content from the source and returns a ProcessedDocument for ingestion.
        All ingestion sources must implement this method.
        """
        ...
