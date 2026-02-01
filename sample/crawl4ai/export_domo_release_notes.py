"""Export Domo release notes HTML and selector-scoped markdown via Crawl4AI."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from mdrag.integrations.crawl4ai import Crawl4AIClient  # type: ignore[import-not-found]
from mdrag.integrations.models import Source  # type: ignore[import-not-found]

DEFAULT_URL = "https://domo-support.domo.com/s/article/Current-Release-Notes?language=en_US"
DEFAULT_SELECTOR = (
    ".slds-rich-text-editor__output.uiOutputRichText.forceOutputRichText"
    ".selfServiceOutputRichTextWithSmartLinks"
)
DEFAULT_OUTPUT_DIRNAME = "domo-release-notes"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export full HTML and selector markdown from a web page.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL to export")
    parser.add_argument(
        "--selector",
        default=DEFAULT_SELECTOR,
        help="CSS selector to wait for and extract",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (defaults to sample/crawl4ai/EXPORTS/domo-release-notes)",
    )
    parser.add_argument(
        "--wait-for-timeout",
        type=int,
        default=60000,
        help="Timeout (ms) for selector wait",
    )
    parser.add_argument(
        "--page-timeout",
        type=int,
        default=120000,
        help="Timeout (ms) for page navigation",
    )
    return parser.parse_args()


async def _run_export(
    url: str,
    selector: str,
    output_dir: Path,
    wait_for_timeout: int,
    page_timeout: int,
) -> None:
    client = Crawl4AIClient()

    try:
        result = await client.crawl_single_page(
            url=url,
            wait_for_selector=selector,
            wait_until="networkidle",
            wait_for_timeout=wait_for_timeout,
            page_timeout=page_timeout,
            allow_fallback=True,
        )
    except Exception as exc:  # pragma: no cover - sample script resilience
        raise RuntimeError(
            "Crawl4AI failed. If this is a Playwright error, run 'playwright install' "
            "and ensure Chromium can launch in your environment."
        ) from exc

    if not result:
        raise RuntimeError("Crawl failed or selector wait timed out.")

    html = (result.html or "").strip()
    if not html:
        raise RuntimeError("Crawl succeeded but returned empty HTML.")

    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(selector)
    if not nodes:
        raise RuntimeError("Selector did not match any elements.")

    selector_html = "\n".join(str(node) for node in nodes)
    markdown = md(selector_html).strip()
    if not markdown:
        raise RuntimeError("Selector markdown is empty after conversion.")

    selector_frontmatter = result.frontmatter.model_copy(deep=True)
    selector_frontmatter.metadata = {
        **(selector_frontmatter.metadata or {}),
        "selector": selector,
    }

    selector_source = Source(
        frontmatter=selector_frontmatter,
        content=markdown,
        metadata={"selector": selector},
        links=result.links,
        html=selector_html,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    (output_dir / "selector.md").write_text(
        selector_source.to_markdown(),
        encoding="utf-8",
    )


def main() -> None:
    args = _parse_args()
    sample_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else sample_dir / "EXPORTS" / DEFAULT_OUTPUT_DIRNAME
    )
    asyncio.run(
        _run_export(
            url=args.url,
            selector=args.selector,
            output_dir=output_dir,
            wait_for_timeout=args.wait_for_timeout,
            page_timeout=args.page_timeout,
        )
    )


if __name__ == "__main__":
    main()
