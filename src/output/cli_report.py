from __future__ import annotations

import sys
from typing import TextIO

from src.analyzer.aggregator import ProjectSummary


class CliReporter:
    """Render token usage as a CLI table."""

    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output or sys.stdout

    def format_tokens(self, count: int) -> str:
        """Format token count for display."""
        if count >= 100_000_000:
            return f"{count / 100_000_000:.1f}億"
        if count >= 10_000:
            return f"{count / 10_000:.1f}万"
        return str(count)

    def render(
        self,
        data: list[tuple[str, ProjectSummary]],
        costs: dict[str, float] | None = None,
    ) -> None:
        """Render project summaries as a table."""
        if not data:
            self.output.write("データなし\n")
            return

        costs = costs or {}

        header = f"{'#':>2} {'Project':<20} {'Ses':>3} {'Tokens':>8} {'Cost':>8}\n"
        separator = "-" * 45 + "\n"

        self.output.write("Token Usage (Local CLI)\n")
        self.output.write(header)
        self.output.write(separator)

        total_tokens = 0
        total_cost = 0.0

        for i, (name, summary) in enumerate(data, 1):
            cost = costs.get(name)
            cost_str = f"${cost:.0f}" if cost is not None else "-"
            tokens_str = self.format_tokens(summary.total_tokens)
            total_tokens += summary.total_tokens
            if cost is not None:
                total_cost += cost
            # Truncate long project names
            display_name = name[:20] if len(name) > 20 else name
            self.output.write(
                f"{i:>2} {display_name:<20} {summary.session_count:>3} {tokens_str:>8} {cost_str:>8}\n"
            )

        self.output.write(separator)
        total_tokens_str = self.format_tokens(total_tokens)
        total_cost_str = f"${total_cost:.0f}" if costs else "-"
        self.output.write(
            f"   {'Total':<20} {'':>3} {total_tokens_str:>8} {total_cost_str:>8}\n"
        )
