"""Test that all ingestion sources implement the IngestionSource protocol."""

from mdrag.ingestion.sources.ingestion_source import IngestionSource
from mdrag.ingestion.sources.crawl4ai_source import Crawl4AIIngestionSource
from mdrag.ingestion.sources.google_drive_source import GoogleDriveIngestionSource
from mdrag.ingestion.sources.searxng_source import SearXNGIngestionSource
from mdrag.ingestion.sources.upload_source import UploadIngestionSource

# Add other sources as you implement them
ALL_SOURCES = [
    GoogleDriveIngestionSource,
    Crawl4AIIngestionSource,
    SearXNGIngestionSource,
    UploadIngestionSource,
]


def test_all_sources_implement_protocol():
    for source_cls in ALL_SOURCES:
        assert issubclass(
            source_cls,
            IngestionSource,
        ), f"{source_cls.__name__} does not implement IngestionSource protocol"
