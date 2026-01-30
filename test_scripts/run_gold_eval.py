"""Run gold dataset evaluation for regression checks."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.query import QueryService

DATASET_PATH = Path(__file__).parent / "gold_dataset.json"


async def main() -> None:
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    service = QueryService()
    try:
        grounded = 0
        total = 0
        for item in data:
            total += 1
            response = await service.answer_query(
                query=item["query"],
                match_count=5,
                filters={"source_group": item.get("source_group")},
            )
            if response.get("grounding", {}).get("grounded"):
                grounded += 1

        score = grounded / max(total, 1)
        print(f"Groundedness score: {score:.2f}")
        if score < 0.90:
            raise SystemExit(1)
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
