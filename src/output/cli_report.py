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

        header = f"{'#':>3}  {'Project':<35}  {'Sessions':>8}  {'Total Tokens':>14}  {'Cost (USD)':>12}\n"
        separator = "-" * len(header.rstrip()) + "\n"

        self.output.write("\nToken Usage Report (Local CLI)\n")
        self.output.write("* Cost is approximate (via ccusage)\n\n")
        self.output.write(header)
        self.output.write(separator)

        total_tokens = 0
        total_cost = 0.0

        for i, (name, summary) in enumerate(data, 1):
            cost = costs.get(name)
            cost_str = f"~${cost:.2f}" if cost is not None else "N/A"
            tokens_str = self.format_tokens(summary.total_tokens)
            total_tokens += summary.total_tokens
            if cost is not None:
                total_cost += cost
            self.output.write(
                f"{i:>3}  {name:<35}  {summary.session_count:>8}  {tokens_str:>14}  {cost_str:>12}\n"
            )

        self.output.write(separator)
        total_tokens_str = self.format_tokens(total_tokens)
        total_cost_str = f"~${total_cost:.2f}" if costs else "N/A"
        self.output.write(
            f"{'':>3}  {'Total':<35}  {'':>8}  {total_tokens_str:>14}  {total_cost_str:>12}\n"
        )
        self.output.write("\n")
