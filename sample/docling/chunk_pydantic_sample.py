"""Sample: convert pydantic.txt into DoclingChunks with intelligent subsetting.

Usage:
    uv run python sample/docling/chunk_pydantic_sample.py

Requirements:
    - Docling + transformers for processing
    - pydantic.txt file in sample/docling/ directory
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from mdrag.capabilities.ingestion.docling.chunker import ChunkingConfig, create_chunker
from mdrag.capabilities.ingestion.docling.processor import DoclingProcessor
from mdrag.capabilities.ingestion.models import IngestionDocument, Namespace, UploadCollectionRequest
from mdrag.capabilities.ingestion.sources.upload_source import UploadCollector
from mdrag.config.settings import load_settings


def subset_markdown_by_headings(
    markdown: str,
    max_chars: int = 20000,
    max_sections: int = 8,
) -> str:
    """Keep title + first N heading sections until max_chars is reached."""
    if not markdown.strip():
        return markdown

    lines = markdown.splitlines()
    sections: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        is_heading = line.startswith("#")
        if is_heading and current:
            sections.append(current)
            current = [line]
        else:
            if not current and line.strip():
                current = [line]
            elif current:
                current.append(line)

    if current:
        sections.append(current)

    # Always include the first section (typically title/introduction)
    output_lines: list[str] = []
    total_chars = 0
    added_sections = 0

    for section in sections:
        section_text = "\n".join(section).strip()
        if not section_text:
            continue
        projected = total_chars + len(section_text) + 2
        if output_lines and (projected > max_chars or added_sections >= max_sections):
            break
        output_lines.append(section_text)
        total_chars = projected
        added_sections += 1

    return "\n\n".join(output_lines).strip()


async def build_subset_document(file_path: Path) -> IngestionDocument:
    """Create an ingestion document from a subset of the markdown content."""
    markdown = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
    subset_markdown = subset_markdown_by_headings(
        markdown,
        max_chars=20000,
        max_sections=8,
    )

    collector = UploadCollector()
    request = UploadCollectionRequest(
        filename=file_path.name,
        content=subset_markdown,
        mime_type="text/markdown",
        namespace=Namespace(),
    )
    sources = await collector.collect(request)
    if not sources:
        raise ValueError("Upload collector returned no sources")

    processor = DoclingProcessor(settings=load_settings())
    return await processor.convert_source(sources[0])


async def main() -> None:
    file_path = Path("sample/docling/pydantic.txt").resolve()

    # Check if file exists
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print("\n   This sample requires the pydantic.txt file to exist.")
        return

    document = await build_subset_document(file_path)

    chunker = create_chunker(
        ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            max_chunk_size=2000,
            max_tokens=512,
        )
    )

    results = await chunker.chunk_document(document)
    print(f"Subset chars: {len(document.content)}")
    print(f"Document UID: {document.metadata.identity.document_uid}")
    print(f"Chunks created: {len(results)}")
    if results:
        first = results[0]
        print("First chunk summary_context:", first.metadata.get("summary_context"))
        print("First chunk token_count:", first.token_count)


if __name__ == "__main__":
    asyncio.run(main())
