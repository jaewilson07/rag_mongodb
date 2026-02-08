"""Sample script to chat with the knowledge base within wiki context.

Demonstrates the streaming chat pipeline:
1. Accepts a question and wiki context
2. Searches relevant chunks via hybrid search
3. Streams the LLM response to stdout

Usage:
    uv run python sample/wiki/chat_wiki.py --question "How does authentication work?"
    uv run python sample/wiki/chat_wiki.py --question "Explain the data model" --context "API Docs"
"""

from __future__ import annotations

import argparse
import asyncio

from mdrag.server.services.wiki import WikiService

DEFAULT_QUESTION = "What topics are covered in the knowledge base?"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chat with the knowledge base using wiki context.",
    )
    parser.add_argument(
        "--question",
        default=DEFAULT_QUESTION,
        help="Question to ask",
    )
    parser.add_argument(
        "--context",
        default="Knowledge Base",
        help="Wiki context to scope the query",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    service = WikiService()

    print(f"Question: {args.question}")
    print(f"Context: {args.context}")
    print("=" * 60)
    print()

    messages = [{"role": "user", "content": args.question}]

    async for chunk in service.stream_chat_response(
        messages=messages,
        wiki_context=args.context,
    ):
        print(chunk, end="", flush=True)

    print()
    print()
    print("=" * 60)
    print("Chat complete.")


if __name__ == "__main__":
    asyncio.run(_run())
