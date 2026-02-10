#!/usr/bin/env python3
"""Conversational CLI with real-time streaming and tool call visibility."""

import asyncio
from typing import List

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from mdrag.agent import RAGState, rag_agent
from mdrag.dependencies import AgentDependencies
from mdrag.logging_config import configure_logging
from mdrag.settings import load_settings

load_dotenv(override=True)

console = Console()


async def ensure_services_ready() -> None:
    """Fail fast if required services are unavailable."""
    deps = AgentDependencies()
    try:
        await deps.initialize()
    finally:
        await deps.cleanup()


async def stream_agent_interaction(
    user_input: str, message_history: List, deps: RAGState
) -> tuple[str, List]:
    """
    Stream agent interaction with real-time tool call display.

    Args:
        user_input: The user's input text
        message_history: List of ModelRequest/ModelResponse objects for conversation context
        deps: StateDeps with RAG state

    Returns:
        Tuple of (streamed_text, updated_message_history)
    """
    try:
        return await _stream_agent(user_input, deps, message_history)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        return ("", [])


async def _stream_agent(
    user_input: str, deps: RAGState, message_history: List
) -> tuple[str, List]:
    """Stream the agent execution and return response."""

    response_text = ""

    async with rag_agent.iter(
        user_input, deps=deps, message_history=message_history
    ) as run:
        async for node in run:
            if Agent.is_user_prompt_node(node):
                pass
            elif Agent.is_model_request_node(node):
                console.print("[bold blue]Assistant:[/bold blue] ", end="")
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if (
                            isinstance(event, PartStartEvent)
                            and event.part.part_kind == "text"
                        ):
                            initial_text = event.part.content
                            if initial_text:
                                console.print(initial_text, end="")
                                response_text += initial_text
                        elif isinstance(event, PartDeltaEvent) and isinstance(
                            event.delta, TextPartDelta
                        ):
                            delta_text = event.delta.content_delta
                            if delta_text:
                                console.print(delta_text, end="")
                                response_text += delta_text
                console.print()
            elif Agent.is_call_tools_node(node):
                async with node.stream(run.ctx) as tool_stream:
                    async for event in tool_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            tool_name = event.part.tool_name
                            args = event.part.args
                            console.print(
                                f"  [cyan]Calling tool:[/cyan] [bold]{tool_name}[/bold]"
                            )
                            if args and isinstance(args, dict):
                                if "query" in args:
                                    console.print(
                                        f"    [dim]Query:[/dim] {args['query']}"
                                    )
                                if "search_type" in args:
                                    console.print(
                                        f"    [dim]Type:[/dim] {args['search_type']}"
                                    )
                                if "match_count" in args:
                                    console.print(
                                        f"    [dim]Results:[/dim] {args['match_count']}"
                                    )
                            elif args:
                                args_str = str(args)
                                if len(args_str) > 100:
                                    args_str = args_str[:97] + "..."
                                console.print(f"    [dim]Args: {args_str}[/dim]")
                        elif isinstance(event, FunctionToolResultEvent):
                            console.print(
                                "  [green]Tool completed successfully[/green]"
                            )
            elif Agent.is_end_node(node):
                pass

    if run.result is None:
        return (response_text.strip(), [])

    new_messages = run.result.new_messages()
    final_output = (
        run.result.output if hasattr(run.result, "output") else str(run.result)
    )
    response_text = response_text.strip() or final_output
    return (response_text, new_messages)


def display_welcome():
    """Display welcome message with configuration info."""
    settings = load_settings()
    welcome = Panel(
        "[bold blue]MongoDB RAG Agent[/bold blue]\n\n"
        "[green]Intelligent knowledge base search with MongoDB Atlas Vector Search[/green]\n"
        f"[dim]LLM: {settings.llm_model}[/dim]\n\n"
        "[dim]Type 'exit' to quit, 'info' for system info, 'clear' to clear screen[/dim]",
        style="blue",
        padding=(1, 2),
    )
    console.print(welcome)
    console.print()


async def main():
    """Main conversation loop."""
    configure_logging()

    try:
        await ensure_services_ready()
    except Exception as e:
        console.print(
            "[red]Service health check failed. "
            "Verify MONGODB_URI and ensure MongoDB is reachable.[/red]"
        )
        console.print(f"[dim]{e}[/dim]")
        raise SystemExit(1)

    display_welcome()
    state = RAGState()
    deps = state
    console.print("[bold green]✓[/bold green] Search system initialized\n")
    message_history = []

    try:
        while True:
            try:
                user_input = Prompt.ask("[bold green]You").strip()

                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("\n[yellow]👋 Goodbye![/yellow]")
                    break
                elif user_input.lower() == "info":
                    settings = load_settings()
                    console.print(
                        Panel(
                            f"[cyan]LLM Provider:[/cyan] {settings.llm_provider}\n"
                            f"[cyan]LLM Model:[/cyan] {settings.llm_model}\n"
                            f"[cyan]Embedding Model:[/cyan] {settings.embedding_model}\n"
                            f"[cyan]Default Match Count:[/cyan] {settings.default_match_count}\n"
                            f"[cyan]Default Text Weight:[/cyan] {settings.default_text_weight}",
                            title="System Configuration",
                            border_style="magenta",
                        )
                    )
                    continue
                elif user_input.lower() == "clear":
                    console.clear()
                    display_welcome()
                    continue
                if not user_input:
                    continue

                response_text, new_messages = await stream_agent_interaction(
                    user_input, message_history, deps
                )
                message_history.extend(new_messages)
                console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                import traceback

                traceback.print_exc()
                continue

    finally:
        console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    asyncio.run(main())
