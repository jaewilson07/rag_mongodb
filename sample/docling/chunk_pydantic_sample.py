# pyright: reportMissingImports=false
"""Sample: convert pydantic.txt into DoclingChunks with intelligent subsetting."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from docling.document_converter import DocumentConverter

from mdrag.ingestion.docling.chunker import ChunkingConfig, create_chunker  # type: ignore[reportMissingImports]
from mdrag.ingestion.docling.processor import DocumentProcessor  # type: ignore[reportMissingImports]
from mdrag.settings import load_settings  # type: ignore[reportMissingImports]


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


def convert_subset_to_docling(markdown: str) -> tuple[str, object]:
    """Convert subset markdown into a DoclingDocument using a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".md", delete=True) as tmp:
        tmp.write(markdown.encode("utf-8"))
        tmp.flush()
        doc = DocumentConverter().convert(tmp.name).document
        return markdown, doc


def main() -> None:
    settings = load_settings()
    processor = DocumentProcessor(settings=settings)

    file_path = Path("sample/docling/pydantic.txt").resolve()
    processed = processor.process_local_file(str(file_path))

    subset_markdown = subset_markdown_by_headings(
        processed.content,
        max_chars=20000,
        max_sections=8,
    )

    subset_markdown, subset_doc = convert_subset_to_docling(subset_markdown)
    content_hash = hashlib.sha256(subset_markdown.encode("utf-8")).hexdigest()

    chunker = create_chunker(
        ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            max_chunk_size=2000,
            max_tokens=512,
        )
    )

    chunks = chunker.chunk_document(
        content=subset_markdown,
        title=processed.title,
        source=processed.source_url,
        metadata={
            **processed.metadata,
            "content_hash": content_hash,
        },
        docling_doc=subset_doc,
    )

    # chunk_document is async; run it synchronously for this sample
    import asyncio

    results = asyncio.run(chunks)
    print(f"Subset chars: {len(subset_markdown)}")
    print(f"Chunks created: {len(results)}")
    if results:
        first = results[0]
        print("First chunk summary_context:", first.metadata.get("summary_context"))
        print("First chunk token_count:", first.token_count)


if __name__ == "__main__":
    main()
