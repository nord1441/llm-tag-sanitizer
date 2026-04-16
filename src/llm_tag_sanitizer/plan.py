"""Change plan: diff representation and dry-run display."""

import json
import logging
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table

from llm_tag_sanitizer.tags.models import ProposedChange

logger = logging.getLogger(__name__)


class ChangePlan:
    """Holds and displays proposed tag changes."""

    def __init__(self, changes: list[ProposedChange] | None = None):
        self.changes: list[ProposedChange] = changes or []

    def add(self, change: ProposedChange) -> None:
        self.changes.append(change)

    def extend(self, changes: list[ProposedChange]) -> None:
        self.changes.extend(changes)

    def is_empty(self) -> bool:
        return len(self.changes) == 0

    def display(self, console: Console | None = None) -> None:
        """Display all proposed changes as a rich table."""
        if not self.changes:
            console = console or Console()
            console.print("[dim]No changes proposed.[/dim]")
            return

        console = console or Console()
        table = Table(
            title="Proposed Tag Changes",
            show_lines=True,
            expand=True,
        )
        table.add_column("File", style="cyan", max_width=50)
        table.add_column("Field", style="yellow")
        table.add_column("Old Value", style="red")
        table.add_column("New Value", style="green")
        table.add_column("Reason", style="dim")

        # Group by file for readability
        by_file: dict[Path, list[ProposedChange]] = defaultdict(list)
        for change in self.changes:
            by_file[change.file_path].append(change)

        for file_path, file_changes in sorted(by_file.items()):
            for i, change in enumerate(file_changes):
                file_display = str(file_path.name) if i == 0 else ""
                table.add_row(
                    file_display,
                    change.field_name,
                    change.old_value or "(empty)",
                    change.new_value,
                    change.reason,
                )

        console.print(table)

    def summary(self, console: Console | None = None) -> None:
        """Print summary statistics."""
        console = console or Console()

        if not self.changes:
            console.print("[dim]No changes proposed.[/dim]")
            return

        files = set(c.file_path for c in self.changes)
        by_optimizer: dict[str, int] = defaultdict(int)
        for c in self.changes:
            by_optimizer[c.optimizer_name] += 1

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Files affected: {len(files)}")
        console.print(f"  Total changes: {len(self.changes)}")
        for opt_name, count in sorted(by_optimizer.items()):
            console.print(f"    {opt_name}: {count}")

    def filter(
        self,
        optimizer_name: str | None = None,
        field: str | None = None,
    ) -> "ChangePlan":
        """Return a filtered copy of this plan."""
        filtered = []
        for c in self.changes:
            if optimizer_name and c.optimizer_name != optimizer_name:
                continue
            if field and c.field_name != field:
                continue
            filtered.append(c)
        return ChangePlan(filtered)

    def to_json(self) -> str:
        """Serialize the plan to JSON."""
        return json.dumps(
            [c.model_dump(mode="json") for c in self.changes],
            indent=2,
            ensure_ascii=False,
        )
