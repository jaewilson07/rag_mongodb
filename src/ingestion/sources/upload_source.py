"""Upload ingestion source implementing the IngestionSource protocol."""

from typing import Any

from .ingestion_source import IngestionSource
from ..docling.processor import DocumentProcessor, ProcessedDocument
from ...settings import load_settings


class UploadIngestionSource(IngestionSource):
    def __init__(self, file_path: str, namespace: dict[str, Any] | None = None) -> None:
        self.file_path = file_path
        self.namespace = namespace or {}
        self.settings = load_settings()
        self.processor = DocumentProcessor(self.settings)

    def fetch_and_convert(self, **kwargs) -> ProcessedDocument:
        """
        Convert a local file path into a ProcessedDocument for ingestion.
        """
        return self.processor.process_local_file(self.file_path, namespace=self.namespace)
