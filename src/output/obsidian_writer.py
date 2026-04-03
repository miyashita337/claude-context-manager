from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.analyzer.aggregator import ProjectSummary


class ObsidianWriter:
    """Write token usage reports as Obsidian-compatible Markdown."""

    def __init__(self, vault_dir: Path) -> None:
        self.vault_dir = vault_dir

    def render(
        self,
        data: list[tuple[str, ProjectSummary]],
        costs: dict[str, float] | None = None,
        report_type: str = "daily",
    ) -> Path:
        """Write a report file and return its path."""
        costs = costs or {}
        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d')}-token-{report_type}.md"
        output_dir = self.vault_dir / "claude-analytics"
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename

        lines: list[str] = []
        lines.append("---")
        lines.append(f"date: {now.strftime('%Y-%m-%d')}")
        lines.append(f"type: token-{report_type}")
        lines.append(f"total_projects: {len(data)}")
        total_tokens = sum(s.total_tokens for _, s in data)
        lines.append(f"total_tokens: {total_tokens}")
        total_cost = sum(costs.get(n, 0) for n, _ in data)
        if costs:
            lines.append(f"total_cost_usd: {total_cost:.2f}")
        lines.append("tags: [claude, token-usage, analytics]")
        lines.append("---")
        lines.append("")
        lines.append(
            f"# Token Usage — {report_type.capitalize()} ({now.strftime('%Y-%m-%d')})"
        )
        lines.append("")
        lines.append("| # | Project | Sessions | Total Tokens | Cost (USD) |")
        lines.append("|---|---------|----------|-------------|-----------|")

        for i, (name, summary) in enumerate(data, 1):
            cost = costs.get(name)
            cost_str = f"~${cost:.2f}" if cost is not None else "N/A"
            tokens_str = self._format_tokens(summary.total_tokens)
            lines.append(
                f"| {i} | {name} | {summary.session_count} | {tokens_str} | {cost_str} |"
            )

        lines.append("")
        lines.append(f"**Total**: {self._format_tokens(total_tokens)} tokens")
        if costs:
            lines.append(f" / ~${total_cost:.2f}")
        lines.append("")

        filepath.write_text("\n".join(lines))
        return filepath

    def _format_tokens(self, count: int) -> str:
        if count >= 100_000_000:
            return f"{count / 100_000_000:.1f}億"
        if count >= 10_000:
            return f"{count / 10_000:.1f}万"
        return str(count)
