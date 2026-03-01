"""Tests for analytics engine question scatter detection (#99)."""
import json
import pytest
import sys
import pathlib

# Add project root to path so we can import .claude.analytics.engine
_WORKTREE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_WORKTREE))

# The module is at .claude/analytics/engine.py — import via importlib
import importlib
_spec = importlib.util.spec_from_file_location(
    "claude_analytics_engine",
    _WORKTREE / ".claude" / "analytics" / "engine.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
analyze_bottlenecks = _mod.analyze_bottlenecks


def _make_user_event(content, msg_index=0):
    """Create a minimal user event."""
    return {
        "type": "user",
        "message": {"role": "user", "content": content},
        "msg_index": msg_index,
    }


def _make_assistant_event(tokens=1000, msg_index=1):
    """Create a minimal assistant event."""
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": "response"},
        "usage": {
            "input_tokens": tokens,
            "output_tokens": 100,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
        "msg_index": msg_index,
    }


class TestQuestionScatterAnalytics:
    """#99: Question pattern analysis in analyze_bottlenecks."""

    def test_high_density_detected(self):
        """Average 3.0 questions/msg should trigger question_scatter."""
        events = []
        for i in range(10):
            events.append(_make_user_event("質問？質問？質問？", msg_index=i * 2))
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        types = [iss["type"] for iss in result["issues"]]
        assert "question_scatter" in types

    def test_low_density_not_detected(self):
        """Normal session with few questions should not trigger."""
        events = []
        for i in range(10):
            events.append(_make_user_event("コードを修正してください", msg_index=i * 2))
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        types = [iss["type"] for iss in result["issues"]]
        assert "question_scatter" not in types

    def test_fullwidth_question_marks(self):
        """Full-width ？ should be counted."""
        events = []
        for i in range(10):
            events.append(_make_user_event("何？何？何？", msg_index=i * 2))
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        types = [iss["type"] for iss in result["issues"]]
        assert "question_scatter" in types

    def test_list_content_format(self):
        """content as list (with tool_result) should only count text blocks."""
        content = [
            {"type": "text", "text": "質問？質問？質問？"},
            {"type": "tool_result", "content": "????"},  # should be ignored
        ]
        events = []
        for i in range(10):
            events.append(_make_user_event(content, msg_index=i * 2))
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        types = [iss["type"] for iss in result["issues"]]
        assert "question_scatter" in types

    def test_score_contribution(self):
        """High density should add to bottleneck score."""
        events = []
        for i in range(10):
            events.append(_make_user_event("？？？？？？？？？？", msg_index=i * 2))  # 10 per msg
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        assert result["bottleneck_score"] >= 10

    def test_large_tool_result_still_detected(self):
        """Regression: large_tool_result detection should still work."""
        content = [
            {"type": "tool_result", "content": "x" * 6000},
        ]
        events = [
            _make_user_event(content, msg_index=0),
            _make_assistant_event(msg_index=1),
        ]
        result = analyze_bottlenecks(events)
        types = [iss["type"] for iss in result["issues"]]
        assert "large_tool_result" in types

    def test_issue_counts_includes_scatter(self):
        """question_scatter should appear in issue_counts."""
        events = []
        for i in range(10):
            events.append(_make_user_event("？？？", msg_index=i * 2))
            events.append(_make_assistant_event(msg_index=i * 2 + 1))
        result = analyze_bottlenecks(events)
        assert "question_scatter" in result.get("issue_counts", {})
