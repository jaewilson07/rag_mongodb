#!/usr/bin/env python3
"""Conversational CLI using LangGraph with streaming and tool call visibility."""

import asyncio
from typing import Any, Iterable

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from mdrag.dependencies import AgentDependencies
from mdrag.langgraph_agent import LANGGRAPH_SYSTEM_PROMPT, build_langgraph_agent
from mdrag.logging_config import configure_logging
from mdrag.settings import load_settings

load_dotenv(override=True)

console = Console()


def _iter_messages(value: Any) -> Iterable[BaseMessage]:
    if isinstance(value, BaseMessage):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, BaseMessage)]
    return []


def _extract_text(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
        return "".join(parts)
    return ""


async def ensure_services_ready() -> None:
    """Fail fast if required services are unavailable."""
    deps = AgentDependencies()
    try:
        await deps.initialize()
    finally:
        await deps.cleanup()


async def stream_agent_interaction(
    user_input: str,
    graph,
    thread_id: str,
    include_system_prompt: bool,
) -> str:
    """Stream the LangGraph agent execution and return response text."""
    response_text = ""
    assistant_started = False

    messages = []
    if include_system_prompt:
        messages.append(SystemMessage(content=LANGGRAPH_SYSTEM_PROMPT))
    messages.append(HumanMessage(content=user_input))

    stream = graph.astream(
        {"messages": messages},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="messages",
    )

    def handle_event(event: Any) -> None:
        nonlocal assistant_started, response_text
        data = event[1] if isinstance(event, tuple) else event
        if not isinstance(data, dict):
            return

        for message in _iter_messages(data.get("messages")):
            if isinstance(message, ToolMessage):
                console.print("  [green]Tool completed successfully[/green]")
                continue

            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                for call in tool_calls:
                    tool_name = call.get("name") or call.get("tool_name") or "tool"
                    args = call.get("args") or {}
                    console.print(
                        f"  [cyan]Calling tool:[/cyan] [bold]{tool_name}[/bold]"
                    )
                    if isinstance(args, dict):
                        if "query" in args:
                            console.print(f"    [dim]Query:[/dim] {args['query']}")
                        if "search_type" in args:
                            console.print(f"    [dim]Type:[/dim] {args['search_type']}")
                        if "match_count" in args:
                            console.print(f"    [dim]Results:[/dim] {args['match_count']}")

            if isinstance(message, (AIMessageChunk, AIMessage)):
                content = _extract_text(message)
                if content:
                    if not assistant_started:
                        console.print("[bold blue]Assistant:[/bold blue] ", end="")
                        assistant_started = True
                    console.print(content, end="")
                    response_text += content

    async for event in stream:
        handle_event(event)

    if assistant_started:
        console.print()

    return response_text.strip()


def display_welcome() -> None:
    """Display welcome message with configuration info."""
    settings = load_settings()
    welcome = Panel(
        "[bold blue]MongoDB RAG Agent (LangGraph)[/bold blue]\n\n"
        "[green]Intelligent knowledge base search with MongoDB Atlas Vector Search[/green]\n"
        f"[dim]LLM: {settings.llm_model}[/dim]\n\n"
        "[dim]Type 'exit' to quit, 'info' for system info, 'clear' to clear screen[/dim]",
        style="blue",
        padding=(1, 2),
    )
    console.print(welcome)
    console.print()


async def main() -> None:
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
    graph = build_langgraph_agent()
    thread_id = "cli-session"
    include_system_prompt = True

    console.print("[bold green]✓[/bold green] Search system initialized\n")

    try:
        while True:
            try:
                user_input = Prompt.ask("[bold green]You").strip()

                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("\n[yellow]👋 Goodbye![/yellow]")
                    break

                if user_input.lower() == "info":
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

                if user_input.lower() == "clear":
                    console.clear()
                    display_welcome()
                    include_system_prompt = True
                    continue

                if not user_input:
                    continue

                await stream_agent_interaction(
                    user_input,
                    graph,
                    thread_id,
                    include_system_prompt,
                )
                include_system_prompt = False
                console.print()

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                import traceback

                traceback.print_exc()
                continue

    except asyncio.CancelledError:
        console.print("\n[dim]Session cancelled.[/dim]")
    finally:
        console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
