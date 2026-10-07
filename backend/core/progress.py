"""
Todards Pipeline — Live Terminal Progress Tracker

Renders a terminal progress bar with active stage titles, sub-steps,
and percentages using the `rich` library. Gracefully degrades to standard
console output if `rich` is unavailable.
"""

import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PipelineProgressTracker:
    """
    Live terminal progress bar and banner renderer for the Todards pipeline.
    """

    def __init__(self, issue_number: Optional[int] = None, date_str: Optional[str] = None):
        self.issue_number = issue_number
        self.date_str = date_str
        self.current_percent = 0.0
        self.status_message = "Initializing..."

        if RICH_AVAILABLE:
            self.console = Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="green", finished_style="bold green"),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=False,
            )
            self.task_id = None
        else:
            self.console = None
            self.progress = None
            self.task_id = None

    def start(self):
        """Print initial banner and launch progress display."""
        header_text = "TODARDS NEWS PIPELINE — AUTOMATED LOCAL AGENT"
        sub_text = f"Date: {self.date_str or 'Today'}"
        if self.issue_number:
            sub_text += f" | Issue #{self.issue_number}"

        if RICH_AVAILABLE and self.console:
            self.console.print(
                Panel.fit(
                    f"[bold white]{header_text}[/bold white]\n[dim]{sub_text}[/dim]",
                    border_style="bright_blue",
                )
            )
            self.progress.start()
            self.task_id = self.progress.add_task(
                description="[bold cyan]Starting pipeline...",
                total=100,
                completed=0,
            )
        else:
            print("=" * 60)
            print(f" {header_text}")
            print(f" {sub_text}")
            print("=" * 60)

    def update_stage(self, stage_name: str, percent: float):
        """Update the major stage and overall percentage."""
        self.current_percent = min(100.0, max(0.0, percent))
        self.status_message = stage_name

        if RICH_AVAILABLE and self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=self.current_percent,
                description=f"[bold yellow]{stage_name}",
            )
        else:
            print(f"[{self.current_percent:3.0f}%] {stage_name}")

    def update_status(self, detail: str):
        """Update live micro-status description above or within bar."""
        if RICH_AVAILABLE and self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                description=f"[bold cyan]{detail}",
            )
        else:
            print(f"  → {detail}")

    def finish(self, message: str = "Pipeline completed successfully!"):
        """Complete the progress display with closing summary."""
        if RICH_AVAILABLE and self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=100.0,
                description=f"[bold green]{message}",
            )
            self.progress.stop()
            self.console.print(f"\n[bold green]✓[/bold green] {message}\n")
        else:
            print(f"\n[100%] {message}\n")
