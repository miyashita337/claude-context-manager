from __future__ import annotations

from src.analyzer.aggregator import ProjectSummary
from src.analyzer.merger import Merger


class TestMerger:
    def test_merge_with_costs(self) -> None:
        summaries = {
            "alpha": ProjectSummary(
                input_tokens=100, output_tokens=200, session_count=1
            ),
            "beta": ProjectSummary(input_tokens=50, output_tokens=100, session_count=2),
        }
        costs = {"alpha": 10.50, "beta": 5.25}
        merger = Merger()
        merged = merger.merge(summaries, costs)
        assert merged["alpha"].cost_usd == 10.50
        assert merged["beta"].cost_usd == 5.25

    def test_merge_without_costs(self) -> None:
        summaries = {
            "alpha": ProjectSummary(
                input_tokens=100, output_tokens=200, session_count=1
            ),
        }
        merger = Merger()
        merged = merger.merge(summaries, costs=None)
        assert merged["alpha"].cost_usd is None

    def test_merge_partial_costs(self) -> None:
        summaries = {
            "alpha": ProjectSummary(
                input_tokens=100, output_tokens=200, session_count=1
            ),
            "beta": ProjectSummary(input_tokens=50, output_tokens=100, session_count=2),
        }
        costs = {"alpha": 10.50}
        merger = Merger()
        merged = merger.merge(summaries, costs)
        assert merged["alpha"].cost_usd == 10.50
        assert merged["beta"].cost_usd is None
