from __future__ import annotations

from typing import Protocol

from src.analyzer.aggregator import ProjectSummary


class Reporter(Protocol):
    """Protocol for output reporters."""

    def render(
        self,
        data: list[tuple[str, ProjectSummary]],
        costs: dict[str, float] | None = None,
    ) -> None: ...
