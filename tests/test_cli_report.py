from __future__ import annotations

from io import StringIO

from src.analyzer.aggregator import ProjectSummary
from src.output.cli_report import CliReporter


class TestCliReporter:
    def test_format_tokens_millions(self) -> None:
        reporter = CliReporter()
        assert reporter.format_tokens(150_000_000) == "1.5億"

    def test_format_tokens_ten_thousands(self) -> None:
        reporter = CliReporter()
        assert reporter.format_tokens(50_000) == "5.0万"

    def test_format_tokens_small(self) -> None:
        reporter = CliReporter()
        assert reporter.format_tokens(999) == "999"

    def test_render_table(self) -> None:
        data: list[tuple[str, ProjectSummary]] = [
            (
                "alpha",
                ProjectSummary(
                    input_tokens=100,
                    output_tokens=200,
                    cache_creation_tokens=5000,
                    cache_read_tokens=50000,
                    session_count=3,
                    models_used={"claude-opus-4-6"},
                ),
            ),
            (
                "beta",
                ProjectSummary(
                    input_tokens=50,
                    output_tokens=100,
                    cache_creation_tokens=1000,
                    cache_read_tokens=10000,
                    session_count=1,
                    models_used={"claude-sonnet-4-6"},
                ),
            ),
        ]
        output = StringIO()
        reporter = CliReporter(output=output)
        reporter.render(data)
        result = output.getvalue()
        assert "alpha" in result
        assert "beta" in result
        assert "3" in result

    def test_render_with_cost(self) -> None:
        data: list[tuple[str, ProjectSummary]] = [
            (
                "alpha",
                ProjectSummary(
                    input_tokens=100,
                    output_tokens=200,
                    cache_creation_tokens=5000,
                    cache_read_tokens=50000,
                    session_count=1,
                ),
            ),
        ]
        costs = {"alpha": 12.34}
        output = StringIO()
        reporter = CliReporter(output=output)
        reporter.render(data, costs=costs)
        result = output.getvalue()
        assert "$12.34" in result

    def test_render_empty(self) -> None:
        output = StringIO()
        reporter = CliReporter(output=output)
        reporter.render([])
        result = output.getvalue()
        assert "データなし" in result
