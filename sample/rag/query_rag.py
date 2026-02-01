"""Sample script to query MongoDB RAG and print the response."""

from __future__ import annotations

import asyncio

from mdrag.query.service import QueryService

DEFAULT_QUERY = "what is AI in domo"


async def _run() -> None:
    service = QueryService()
    try:
        result = await service.answer_query(DEFAULT_QUERY)
        print("Query:")
        print(DEFAULT_QUERY)
        print("\nAnswer:")
        print(result.get("answer", ""))
        print("\nCitations:")
        citations = result.get("citations", {})
        for index, citation in citations.items():
            print(f"[{index}] {citation}")
        grounding = result.get("grounding", {})
        print("\nGrounding:")
        print(grounding)
        print("\nTrace ID:")
        print(result.get("trace_id"))
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(_run())
