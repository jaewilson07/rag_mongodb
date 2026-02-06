"""
Real-time dashboard for monitoring NeuralCursor health.
"""

import asyncio
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from neuralcursor.monitoring.gpu_monitor import get_monitor


class HealthDashboard:
    """
    Rich-based terminal dashboard for monitoring system health.
    
    Displays:
    - GPU VRAM usage for dual 3090s
    - System CPU/RAM usage
    - Neo4j/MongoDB connection status
    - LLM endpoint health
    """

    def __init__(self):
        """Initialize dashboard."""
        self.console = Console()
        self.monitor = get_monitor()
        self._running = False

    def _create_layout(self) -> Layout:
        """
        Create the dashboard layout.
        
        Returns:
            Rich Layout
        """
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        return layout

    def _render_header(self) -> Panel:
        """Render dashboard header."""
        header_text = Text()
        header_text.append("🧠 NeuralCursor Health Dashboard", style="bold cyan")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

        return Panel(header_text, style="bold")

    def _render_gpu_status(self) -> Table:
        """Render GPU status table."""
        table = Table(title="GPU Status (Dual 3090s)", show_header=True)

        table.add_column("GPU", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("VRAM Used", justify="right")
        table.add_column("VRAM Free", justify="right")
        table.add_column("Util %", justify="right")
        table.add_column("Temp °C", justify="right")
        table.add_column("Power W", justify="right")

        system_status = self.monitor.get_system_status()

        for gpu in system_status.gpus:
            # Color code VRAM utilization
            vram_color = "green"
            if gpu.memory_utilization_percent > 80:
                vram_color = "red"
            elif gpu.memory_utilization_percent > 60:
                vram_color = "yellow"

            table.add_row(
                f"GPU {gpu.device_id}",
                gpu.name,
                f"[{vram_color}]{gpu.used_memory_gb:.2f} GB[/{vram_color}]",
                f"{gpu.free_memory_gb:.2f} GB",
                f"[{vram_color}]{gpu.memory_utilization_percent:.1f}%[/{vram_color}]",
                f"{gpu.temperature_celsius:.0f}" if gpu.temperature_celsius else "N/A",
                f"{gpu.power_draw_watts:.0f}" if gpu.power_draw_watts else "N/A",
            )

        if not system_status.gpus:
            table.add_row("N/A", "NVML not available", "-", "-", "-", "-", "-")

        return table

    def _render_system_status(self) -> Table:
        """Render system resource table."""
        table = Table(title="System Resources", show_header=True)

        table.add_column("Resource", style="cyan")
        table.add_column("Usage", justify="right")
        table.add_column("Available", justify="right")

        system_status = self.monitor.get_system_status()

        # CPU
        cpu_color = "green" if system_status.cpu_percent < 70 else "yellow"
        table.add_row(
            "CPU",
            f"[{cpu_color}]{system_status.cpu_percent:.1f}%[/{cpu_color}]",
            "-",
        )

        # RAM
        ram_color = "green" if system_status.ram_percent < 70 else "yellow"
        table.add_row(
            "RAM",
            f"[{ram_color}]{system_status.ram_used_gb:.2f} GB ({system_status.ram_percent:.1f}%)[/{ram_color}]",
            f"{system_status.ram_total_gb:.2f} GB",
        )

        # Process memory
        table.add_row(
            "Process",
            f"{system_status.process_memory_gb:.2f} GB",
            "-",
        )

        return table

    def _render_connections(self) -> Table:
        """Render database connection status."""
        table = Table(title="Connections", show_header=True)

        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")

        # TODO: Get actual connection status from gateway
        # For now, show placeholder
        table.add_row("Neo4j", "[yellow]Unknown[/yellow]")
        table.add_row("MongoDB", "[yellow]Unknown[/yellow]")
        table.add_row("Reasoning LLM", "[yellow]Unknown[/yellow]")
        table.add_row("Embedding LLM", "[yellow]Unknown[/yellow]")

        return table

    def _render_footer(self) -> Panel:
        """Render dashboard footer."""
        footer_text = Text()
        footer_text.append("Press Ctrl+C to exit", style="dim italic")

        return Panel(footer_text, style="dim")

    def render(self) -> Layout:
        """
        Render the full dashboard.
        
        Returns:
            Complete dashboard layout
        """
        layout = self._create_layout()

        layout["header"].update(self._render_header())
        layout["left"].update(Panel(self._render_gpu_status()))
        layout["right"].split_column(
            Layout(Panel(self._render_system_status())),
            Layout(Panel(self._render_connections())),
        )
        layout["footer"].update(self._render_footer())

        return layout

    async def run(self, refresh_interval: float = 2.0) -> None:
        """
        Run the live dashboard.
        
        Args:
            refresh_interval: Refresh interval in seconds
        """
        self._running = True

        try:
            with Live(self.render(), console=self.console, refresh_per_second=1/refresh_interval) as live:
                while self._running:
                    live.update(self.render())
                    await asyncio.sleep(refresh_interval)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped[/yellow]")

    def stop(self) -> None:
        """Stop the dashboard."""
        self._running = False


async def main():
    """Run the dashboard as standalone application."""
    dashboard = HealthDashboard()
    await dashboard.run()


if __name__ == "__main__":
    asyncio.run(main())
