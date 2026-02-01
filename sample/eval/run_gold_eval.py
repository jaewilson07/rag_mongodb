"""Run evaluation against the gold dataset."""

import json
from pathlib import Path

from src.agent import rag_agent, RAGState
from pydantic_ai.ag_ui import StateDeps


DATASET_PATH = Path(__file__).with_name("gold_dataset.json")


def load_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


async def run_eval():
    data = load_dataset()

    state = RAGState()
    deps = StateDeps[RAGState](state=state)

    results = []
    for item in data:
        question = item["question"]
        expected = item["expected"]

        response_text = ""
        tool_called = False

        async with rag_agent.iter(question, deps=deps, message_history=[]) as run:
            async for node in run:
                if rag_agent.is_call_tools_node(node):
                    tool_called = True
                elif rag_agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            from pydantic_ai.messages import PartStartEvent, PartDeltaEvent, TextPartDelta
                            if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                if event.part.content:
                                    response_text += event.part.content
                            elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                if event.delta.content_delta:
                                    response_text += event.delta.content_delta

        # Simple scoring
        matched = sum(1 for token in expected if token.lower() in response_text.lower())
        results.append({
            "question": question,
            "matched": matched,
            "expected_count": len(expected),
            "tool_called": tool_called,
        })

    # Summary
    total = len(results)
    average_match = sum(r["matched"] for r in results) / total if total else 0
    print(f"Evaluated {total} questions. Avg match: {average_match:.2f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_eval())
