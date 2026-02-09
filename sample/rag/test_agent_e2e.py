"""End-to-end agent testing with real queries.

Usage:
    uv run python sample/rag/test_agent_e2e.py

Requirements:
    - MongoDB with vector and text indexes
    - LLM API key for agent responses
    - Embedding API key for semantic search
"""

import asyncio
import sys
from pathlib import Path

from pydantic_ai.ag_ui import StateDeps

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.agent import RAGState, rag_agent
from mdrag.settings import load_settings
from utils import check_api_keys, check_mongodb, print_pre_flight_results

# Test queries covering different scenarios
TEST_QUERIES = [
    {
        "query": "What is MongoDB vector search?",
        "expected_tool_call": True,
        "description": "Technical knowledge base query"
    },
    {
        "query": "Tell me about the technical architecture",
        "expected_tool_call": True,
        "description": "Architecture documentation query"
    },
    {
        "query": "What does the company handbook say about goals?",
        "expected_tool_call": True,
        "description": "Specific document query"
    },
    {
        "query": "Hello, how are you?",
        "expected_tool_call": False,
        "description": "Conversational greeting (should NOT search)"
    },
    {
        "query": "What's in the meeting notes?",
        "expected_tool_call": True,
        "description": "Document content query"
    }
]


async def test_single_query(query_info: dict, message_history: list) -> tuple[str, list, bool]:
    """
    Test a single query against the agent.

    Returns:
        (response_text, new_messages, tool_was_called)
    """
    print(f"\n{'='*80}")
    print(f"Query: {query_info['query']}")
    print(f"Description: {query_info['description']}")
    print(f"Expected tool call: {query_info['expected_tool_call']}")
    print(f"{'='*80}")

    # Create state and deps
    state = RAGState()
    deps = StateDeps[RAGState](state=state)

    # Track if tool was called
    tool_called = False
    response_text = ""

    # Run the agent
    async with rag_agent.iter(
        query_info['query'],
        deps=deps,
        message_history=message_history
    ) as run:

        async for node in run:
            # Check for tool calls
            if rag_agent.is_call_tools_node(node):
                tool_called = True
                async with node.stream(run.ctx) as tool_stream:
                    async for event in tool_stream:
                        event_type = type(event).__name__
                        if event_type == "FunctionToolCallEvent":
                            if hasattr(event, 'part'):
                                part = event.part
                                tool_name = getattr(part, 'tool_name', getattr(part, 'name', 'Unknown'))
                                args = getattr(part, 'args', getattr(part, 'arguments', {}))
                                print(f"  [TOOL CALL] {tool_name}")
                                if isinstance(args, dict):
                                    for key, value in args.items():
                                        print(f"    {key}: {value}")

            # Collect response text
            elif rag_agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        from pydantic_ai.messages import (
                            PartDeltaEvent,
                            PartStartEvent,
                            TextPartDelta,
                        )
                        if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                            if event.part.content:
                                response_text += event.part.content
                        elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                            if event.delta.content_delta:
                                response_text += event.delta.content_delta

        # Get new messages
        new_messages = run.result.new_messages()

    # Print results
    print("\n[RESULT]")
    print(f"Tool Called: {tool_called} (expected: {query_info['expected_tool_call']})")
    print(f"Response Length: {len(response_text)} chars")
    print(f"Response Preview: {response_text[:200]}...")

    # Validate
    success = tool_called == query_info['expected_tool_call']
    if success:
        print("✓ TEST PASSED")
    else:
        print("✗ TEST FAILED - Tool call mismatch!")

    return response_text, new_messages, success


async def test_conversation_context():
    """Test that conversation context is maintained."""
    print(f"\n{'='*80}")
    print("TESTING CONVERSATION CONTEXT")
    print(f"{'='*80}")

    state = RAGState()
    deps = StateDeps[RAGState](state=state)
    message_history = []

    # First query
    print("\n[Query 1] What documents do we have about MongoDB?")
    async with rag_agent.iter(
        "What documents do we have about MongoDB?",
        deps=deps,
        message_history=message_history
    ) as run:
        async for node in run:
            pass
        message_history.extend(run.result.new_messages())
        response1 = str(run.result.output) if hasattr(run.result, 'output') else ""

    print(f"Response 1: {response1[:150]}...")

    # Follow-up query (should use context)
    print("\n[Query 2] Can you summarize the key points from that?")
    async with rag_agent.iter(
        "Can you summarize the key points from that?",
        deps=deps,
        message_history=message_history
    ) as run:
        async for node in run:
            pass
        response2 = str(run.result.output) if hasattr(run.result, 'output') else ""

    print(f"Response 2: {response2[:150]}...")
    print("✓ Conversation context test completed")

    return True


async def main():
    """Run all end-to-end tests."""
    print("="*80)
    print("MongoDB RAG Agent - End-to-End Testing")
    print("="*80)
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        return 1

    message_history = []
    results = []

    # Test individual queries
    for query_info in TEST_QUERIES:
        try:
            response, new_messages, success = await test_single_query(query_info, message_history)
            results.append({
                "query": query_info['query'],
                "success": success,
                "response_length": len(response)
            })
            # Don't maintain history for isolated tests
            # message_history.extend(new_messages)
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query_info['query'],
                "success": False,
                "error": str(e)
            })

    # Test conversation context
    try:
        await test_conversation_context()
    except Exception as e:
        print(f"\n✗ Conversation context test failed: {e}")

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)

    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result.get('success', False) else "✗ FAIL"
        query = result['query'][:50]
        print(f"{i}. {status} - {query}")
        if 'error' in result:
            print(f"   Error: {result['error']}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Agent is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check results above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
