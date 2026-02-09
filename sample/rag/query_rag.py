"""Sample script to query MongoDB RAG and print the response.

Usage:
    uv run python sample/rag/query_rag.py

Requirements:
    - MongoDB with vector and text indexes
    - LLM API key for answer generation
    - Embedding API key for semantic search
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.query.service import QueryService
from mdrag.settings import load_settings
from utils import check_api_keys, check_mongodb, print_pre_flight_results

DEFAULT_QUERY = "what is AI in domo"


async def _run() -> None:
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        return
    
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
