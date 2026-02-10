"""Test that ingestion capabilities implement protocol contracts."""

from mdrag.ingestion.docling.processor import DoclingProcessor
from mdrag.ingestion.protocols import IngestionProcessor, SourceCollector, StorageAdapter
from mdrag.ingestion.sources import Crawl4AICollector, GoogleDriveCollector, UploadCollector
from mdrag.integrations.mongodb.adapters.storage import MongoStorageAdapter


def test_collectors_implement_protocol() -> None:
    collectors = [
        Crawl4AICollector,
        GoogleDriveCollector,
        UploadCollector,
    ]
    for collector_cls in collectors:
        assert issubclass(
            collector_cls,
            SourceCollector,
        ), f"{collector_cls.__name__} does not implement SourceCollector protocol"


def test_processor_implements_protocol() -> None:
    assert issubclass(
        DoclingProcessor,
        IngestionProcessor,
    ), "DoclingProcessor does not implement IngestionProcessor protocol"


def test_storage_implements_protocol() -> None:
    assert issubclass(
        MongoStorageAdapter,
        StorageAdapter,
    ), "MongoStorageAdapter does not implement StorageAdapter protocol"
