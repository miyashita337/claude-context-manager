from __future__ import annotations

from pathlib import Path
from src.analyzer.jsonl_parser import JsonlParser, SessionStats

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestJsonlParser:
    def test_parse_session_file(self) -> None:
        parser = JsonlParser()
        stats = parser.parse_file(FIXTURES_DIR / "sample_session.jsonl")
        assert isinstance(stats, SessionStats)
        assert stats.input_tokens > 0
        assert stats.output_tokens > 0
        assert stats.cache_creation_tokens > 0
        assert stats.cache_read_tokens > 0

    def test_token_totals(self) -> None:
        parser = JsonlParser()
        stats = parser.parse_file(FIXTURES_DIR / "sample_session.jsonl")
        # From fixture: 100+150+50=300 input, 200+300+80=580 output
        assert stats.input_tokens == 300
        assert stats.output_tokens == 580
        assert stats.cache_creation_tokens == 6000
        assert stats.cache_read_tokens == 115000

    def test_models_used(self) -> None:
        parser = JsonlParser()
        stats = parser.parse_file(FIXTURES_DIR / "sample_session.jsonl")
        assert "claude-opus-4-6" in stats.models_used
        assert "claude-haiku-4-5-20251001" in stats.models_used

    def test_session_count(self) -> None:
        parser = JsonlParser()
        stats = parser.parse_file(FIXTURES_DIR / "sample_session.jsonl")
        assert stats.assistant_message_count == 3
        assert stats.user_message_count == 2

    def test_unknown_type_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "test.jsonl"
        f.write_text(
            '{"type": "future-unknown-type", "data": "whatever"}\n'
            '{"type": "assistant", "message": {"model": "claude-opus-4-6", "usage": {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 20}}}\n'
        )
        parser = JsonlParser()
        stats = parser.parse_file(f)
        assert stats.input_tokens == 10
        assert stats.output_tokens == 20

    def test_malformed_line_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "test.jsonl"
        f.write_text(
            "this is not json\n"
            '{"type": "assistant", "message": {"model": "claude-opus-4-6", "usage": {"input_tokens": 5, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 10}}}\n'
        )
        parser = JsonlParser()
        stats = parser.parse_file(f)
        assert stats.input_tokens == 5

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        parser = JsonlParser()
        stats = parser.parse_file(f)
        assert stats.input_tokens == 0
        assert stats.total_tokens == 0
