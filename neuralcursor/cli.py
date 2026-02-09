"""
NeuralCursor CLI for interacting with the Second Brain.
"""

import asyncio
import logging

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from neuralcursor.brain.memgpt.agent import MemGPTAgent
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.settings import get_settings

console = Console()
logger = logging.getLogger(__name__)


class NeuralCursorCLI:
    """Interactive CLI for NeuralCursor."""

    def __init__(self):
        """Initialize CLI."""
        self.settings = get_settings()
        self.neo4j: Neo4jClient | None = None
        self.mongodb: MongoDBClient | None = None
        self.memgpt: MemGPTAgent | None = None

    async def initialize(self) -> None:
        """Initialize connections."""
        console.print("[cyan]Initializing NeuralCursor...[/cyan]")

        try:
            # Neo4j
            neo4j_config = Neo4jConfig(
                uri=self.settings.neo4j_uri,
                username=self.settings.neo4j_username,
                password=self.settings.neo4j_password,
                database=self.settings.neo4j_database,
            )
            self.neo4j = Neo4jClient(neo4j_config)
            await self.neo4j.connect()

            # MongoDB
            mongodb_config = MongoDBConfig(
                uri=self.settings.mongodb_connection_string,
                database=self.settings.mongodb_database,
            )
            self.mongodb = MongoDBClient(mongodb_config)
            await self.mongodb.connect()

            # MemGPT
            self.memgpt = MemGPTAgent(self.neo4j, self.mongodb)

            console.print("[green]✓ Connected to NeuralCursor Second Brain[/green]\n")

        except Exception as e:
            console.print(f"[red]Failed to initialize: {e}[/red]")
            raise

    async def show_schema_info(self) -> None:
        """Show schema information."""
        if not self.neo4j:
            return

        info = await self.neo4j.get_schema_info()

        table = Table(title="Graph Schema Info")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Total Nodes", str(info["total_nodes"]))
        table.add_row("Total Relationships", str(info["total_relationships"]))
        table.add_row("Constraints", str(info["constraints"]))
        table.add_row("Indexes", str(info["indexes"]))
        table.add_row("Schema Valid", "✓" if info["schema_valid"] else "✗")

        console.print(table)
        console.print()

        # Node counts
        node_table = Table(title="Nodes by Type")
        node_table.add_column("Type", style="cyan")
        node_table.add_column("Count", justify="right")

        for node_type, count in info["node_counts"].items():
            node_table.add_row(node_type, str(count))

        console.print(node_table)

    async def show_active_context(self) -> None:
        """Show active context from MemGPT."""
        if not self.memgpt:
            return

        context = await self.memgpt.get_active_context()

        console.print(Panel("[bold]Active Context[/bold]"))

        if context.get("active_project"):
            console.print(f"[cyan]Active Project:[/cyan] {context['active_project'].get('name')}")

        console.print(f"[cyan]Working Set Size:[/cyan] {context['working_set_size']}")
        console.print(f"[cyan]Context Usage:[/cyan] {context['context_usage']:.1%}")

        if context.get("recent_nodes"):
            console.print("\n[cyan]Recently Accessed:[/cyan]")
            for node in context["recent_nodes"][:5]:
                console.print(f"  - {node.get('name')} ({node.get('node_type')})")

    async def search_memory(self, query: str) -> None:
        """Search the second brain."""
        if not self.memgpt:
            return

        console.print(f"[cyan]Searching for:[/cyan] {query}\n")

        results = await self.memgpt.retrieve_from_memory(query, memory_type="both", limit=10)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        for i, result in enumerate(results, 1):
            source = result.get("source", "unknown")
            data = result.get("data", {})

            console.print(f"[bold]{i}. [{source}] {data.get('name', 'Unknown')}[/bold]")
            if data.get("description"):
                console.print(f"   {data['description'][:100]}...")
            console.print()

    async def run(self) -> None:
        """Run interactive CLI."""
        console.print(Panel.fit(
            "[bold cyan]NeuralCursor Second Brain[/bold cyan]\n"
            "Your persistent AI memory for Cursor IDE",
            border_style="cyan"
        ))

        await self.initialize()

        console.print("[dim]Commands: info, context, search <query>, exit[/dim]\n")

        while True:
            try:
                command = Prompt.ask("[bold cyan]neuralcursor[/bold cyan]")

                if command in ["exit", "quit", "q"]:
                    break

                elif command == "info":
                    await self.show_schema_info()

                elif command == "context":
                    await self.show_active_context()

                elif command.startswith("search "):
                    query = command.replace("search ", "").strip()
                    await self.search_memory(query)

                elif command == "help":
                    console.print("""
[cyan]Available Commands:[/cyan]
  info          - Show graph schema information
  context       - Show active context and working set
  search <query> - Search the second brain
  help          - Show this help message
  exit          - Exit CLI
""")

                else:
                    console.print("[yellow]Unknown command. Type 'help' for available commands.[/yellow]")

                console.print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        console.print("\n[cyan]Goodbye![/cyan]")

        # Cleanup
        if self.neo4j:
            await self.neo4j.close()
        if self.mongodb:
            await self.mongodb.close()


async def main():
    """Main entry point."""
    cli = NeuralCursorCLI()
    await cli.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
