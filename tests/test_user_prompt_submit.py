#!/usr/bin/env python3
"""TDD tests for user-prompt-submit.py - P2 LLM judgment.

Test strategy:
  - Unit tests for _query_llm_p2(): all failure patterns
  - Integration tests for _run_detection(): pipeline trigger conditions
"""

import importlib.util
import json
import os
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── module loader (filename has hyphen, can't use plain import) ──────────────
HOOKS_DIR = Path(__file__).parent.parent / "src" / "hooks"
sys.path.insert(0, str(HOOKS_DIR / "shared"))


def _load_ups():
    spec = importlib.util.spec_from_file_location(
        "user_prompt_submit",
        HOOKS_DIR / "user-prompt-submit.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ups = _load_ups()

# ── convenience aliases for new functions (#96/#97) ───────────────────────────
detect_question_scatter = getattr(ups, "detect_question_scatter", None)
compute_question_density = getattr(ups, "compute_question_density", None)


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_urlopen(body: dict) -> MagicMock:
    """Return a mock context-manager for urllib.request.urlopen (200 success)."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _http_error(status: int) -> urllib.error.HTTPError:
    """Return an HTTPError for the given status code."""
    return urllib.error.HTTPError(
        url=None, code=status, msg="Error", hdrs=None, fp=None
    )


def _api_ok(ok: bool, reason: str = "") -> dict:
    """Build the JSON body that Haiku returns."""
    text = json.dumps({"ok": ok, "reason": reason} if not ok else {"ok": ok})
    return {"content": [{"type": "text", "text": text}]}


# ── baseline transcript fixture ───────────────────────────────────────────────

@pytest.fixture()
def transcript(tmp_path) -> str:
    """JSONL transcript with two technical baseline messages."""
    f = tmp_path / "transcript.jsonl"
    lines = [
        {"type": "user", "message": {"content": "fix the authentication bug in auth.py"}},
        {"type": "user", "message": {"content": "add unit tests for the login function"}},
    ]
    f.write_text("\n".join(json.dumps(l) for l in lines))
    return str(f)


# =============================================================================
# Unit tests: _query_llm_p2()
# =============================================================================

class TestQueryLlmP2:
    """All failure + success paths for the raw API call."""

    # ── availability guards ──────────────────────────────────────────────────

    def test_no_api_key_returns_warn(self):
        """No ANTHROPIC_API_KEY → immediate warn, no HTTP call."""
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_unavailable" in result["reason"]

    # ── happy paths ──────────────────────────────────────────────────────────

    def test_on_topic_returns_pass(self):
        """ok:true → decision=pass."""
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_ok(True))):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("refactor this function", ["fix bug"])

        assert result["decision"] == "pass"

    def test_off_topic_returns_warn_with_reason(self):
        """ok:false → decision=warn, reason propagated."""
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_ok(False, "weather unrelated to work"))):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("what's the weather today?", ["fix bug"])

        assert result["decision"] == "warn"
        assert "weather" in result["reason"]

    # ── API error codes ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
    def test_api_non_200_returns_warn(self, status):
        """Any non-200 HTTP error → warn with api_error tag."""
        with patch("urllib.request.urlopen", side_effect=_http_error(status)):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_api_error" in result["reason"]
        assert str(status) in result["reason"]

    # ── network / connection errors ──────────────────────────────────────────

    def test_timeout_returns_warn(self):
        """socket.timeout → warn, never raises."""
        import socket

        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_error" in result["reason"]

    def test_oserror_returns_warn(self):
        """URLError (connection refused) → warn."""
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_error" in result["reason"]

    # ── malformed response ───────────────────────────────────────────────────

    def test_malformed_json_in_text_returns_warn(self):
        """LLM returns non-JSON text → warn, never raises."""
        body = {"content": [{"type": "text", "text": "I cannot determine..."}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"

    def test_empty_content_array_returns_warn(self):
        """Empty content list → warn."""
        with patch("urllib.request.urlopen", return_value=_mock_urlopen({"content": []})):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_empty_response" in result["reason"]

    def test_missing_ok_field_defaults_to_pass(self):
        """'ok' field absent → default on-topic (conservative: avoid false positives)."""
        body = {"content": [{"type": "text", "text": '{"reason": "unclear"}'}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "pass"

    def test_entire_response_body_is_not_json(self):
        """API body is plain text (e.g. WAF HTML) → warn."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html>Gateway Error</html>"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"

    def test_empty_baseline_messages(self):
        """Empty baseline is handled without error."""
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_ok(True))):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "pass"

    def test_empty_response_body_returns_warn(self):
        """200 status but empty body (e.g. network truncation) → warn, not crash."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert result["reason"] == "p2_empty_body"

    def test_empty_text_field_in_content_returns_warn(self):
        """LLM returns content with empty text (model output empty) → warn, not crash."""
        body = {"content": [{"type": "text", "text": "   "}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert result["reason"] == "p2_empty_text"

    def test_haiku_returns_prose_not_json(self):
        """Haiku returns prose ('I cannot determine...') instead of JSON → warn, not crash."""
        body = {"content": [{"type": "text", "text": "I cannot determine if this is off-topic."}]}
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert result["reason"] == "p2_non_json_text"

    def test_waf_html_response_body_returns_warn(self):
        """CDN/WAF returns HTML with 200 status → non-JSON body guard catches it."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html>Gateway Error</html>"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert result["reason"] == "p2_non_json_body"


# =============================================================================
# Integration tests: _run_detection() pipeline trigger conditions
# =============================================================================

class TestRunDetectionPipeline:
    """Verify WHEN P2 fires (and when it must NOT fire)."""

    # ── P2 must NOT fire ─────────────────────────────────────────────────────

    def test_p2_not_called_when_p1_passes(self, transcript):
        """P1 says PASS → P2 skipped."""
        p1 = {"available": True, "is_deviation": False, "similarity": 0.9, "reason": "ok"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2") as mock_p2:
                result = ups._run_detection("any prompt", "s1", transcript)

        mock_p2.assert_not_called()
        assert not result["is_deviation"]

    def test_p2_not_called_when_p0_tech_veto(self, transcript):
        """P1 WARN + P0 sees tech keyword → P2 skipped."""
        p1 = {"available": True, "is_deviation": True, "similarity": 0.3, "reason": "low"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2") as mock_p2:
                # "python" is a tech keyword → P0 veto
                result = ups._run_detection(
                    "pythonのバグを修正してください", "s1", transcript
                )

        mock_p2.assert_not_called()
        assert not result["is_deviation"]

    def test_p2_not_called_when_p1_server_unavailable(self, transcript):
        """P1 server down → P0 fallback path, P2 skipped."""
        p1 = {"available": False, "reason": "server_not_running"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2") as mock_p2:
                ups._run_detection("今日の天気は？", "s1", transcript)

        mock_p2.assert_not_called()

    def test_p2_not_called_when_p1_no_baseline(self, transcript):
        """P1 available but no baseline yet → P0 fallback, P2 skipped."""
        p1 = {"available": True, "is_deviation": False, "reason": "no_baseline"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2") as mock_p2:
                ups._run_detection("今日の天気は？", "s1", transcript)

        mock_p2.assert_not_called()

    # ── P2 MUST fire ─────────────────────────────────────────────────────────

    def test_p2_called_when_p1_warn_no_p0_veto(self, transcript):
        """P1 WARN + no tech keyword + no P0 veto → P2 invoked."""
        p1 = {"available": True, "is_deviation": True, "similarity": 0.25, "reason": "low"}
        p2_ret = {"decision": "pass", "reason": "p2_on_topic"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2", return_value=p2_ret) as mock_p2:
                ups._run_detection("今日の天気は？", "s1", transcript)

        mock_p2.assert_called_once()

    # ── P2 outcome effects ───────────────────────────────────────────────────

    def test_p2_pass_overrides_p1_warn(self, transcript):
        """P2 says pass → final result is_deviation=False."""
        p1 = {"available": True, "is_deviation": True, "similarity": 0.3, "reason": "low"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2", return_value={"decision": "pass", "reason": "p2_on_topic"}):
                result = ups._run_detection("今日の天気は？", "s1", transcript)

        assert not result["is_deviation"]
        assert "p2_pass" in result["reason"]

    def test_p2_warn_keeps_deviation_true(self, transcript):
        """P2 says warn → is_deviation stays True, reason updated."""
        p1 = {"available": True, "is_deviation": True, "similarity": 0.2, "reason": "low"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2", return_value={"decision": "warn", "reason": "p2_llm: 天気は無関係"}):
                result = ups._run_detection("今日の天気は？", "s1", transcript)

        assert result["is_deviation"]
        assert "p2_llm" in result["reason"]

    def test_p2_error_preserves_p1_warn(self, transcript):
        """P2 internal error (conservative) → still warns."""
        p1 = {"available": True, "is_deviation": True, "similarity": 0.2, "reason": "low"}
        with patch.object(ups, "_query_topic_server", return_value=p1):
            with patch.object(ups, "_query_llm_p2", return_value={"decision": "warn", "reason": "p2_error: timeout"}):
                result = ups._run_detection("今日の天気は？", "s1", transcript)

        assert result["is_deviation"]


# =============================================================================
# Unit tests: _query_topic_server()
# =============================================================================

class TestQueryTopicServer:
    """Verify P1 embedding server error handling."""

    def test_empty_body_from_server_returns_unavailable(self, transcript):
        """Embedding server returns empty body → JSONDecodeError must NOT propagate."""
        import http.client

        mock_resp = MagicMock()
        mock_resp.read.return_value = b""  # empty body → json.loads("") raises JSONDecodeError

        with patch.object(http.client, "HTTPConnection") as mock_conn_cls:
            mock_conn_cls.return_value.getresponse.return_value = mock_resp
            result = ups._query_topic_server("test prompt", "sess1", transcript)

        assert result["available"] is False

    def test_invalid_json_from_server_returns_unavailable(self, transcript):
        """Embedding server returns malformed JSON → ValueError must NOT propagate."""
        import http.client

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not-json"

        with patch.object(http.client, "HTTPConnection") as mock_conn_cls:
            mock_conn_cls.return_value.getresponse.return_value = mock_resp
            result = ups._query_topic_server("test prompt", "sess1", transcript)

        assert result["available"] is False


# =============================================================================
# Unit tests: detect_question_scatter() — #96
# =============================================================================

class TestDetectQuestionScatter:
    """#96: Question scatter pattern detection."""

    def test_three_fullwidth_question_marks(self):
        result = detect_question_scatter("これは何？どうする？なぜ？")
        assert result["is_scatter"] is True

    def test_three_ascii_question_marks(self):
        result = detect_question_scatter("what? how? why?")
        assert result["is_scatter"] is True

    def test_mixed_question_marks_three(self):
        result = detect_question_scatter("何？what? なぜ？")
        assert result["is_scatter"] is True

    def test_four_markers_no_question_marks(self):
        result = detect_question_scatter("なぜこうなるのか、どうしてこうなのか、比較してほしい、それぞれ教えて")
        assert result["is_scatter"] is True

    def test_ten_question_marks(self):
        result = detect_question_scatter("?" * 10)
        assert result["is_scatter"] is True
        assert result["question_count"] >= 10

    def test_one_question_mark(self):
        result = detect_question_scatter("これは何？")
        assert result["is_scatter"] is False

    def test_two_question_marks(self):
        result = detect_question_scatter("何？どう？")
        assert result["is_scatter"] is False

    def test_no_questions(self):
        result = detect_question_scatter("コードを修正してください")
        assert result["is_scatter"] is False

    def test_empty_string(self):
        result = detect_question_scatter("")
        assert result["is_scatter"] is False
        assert result["question_count"] == 0

    def test_three_markers_below_threshold(self):
        result = detect_question_scatter("なぜこうなのか、どうして動かないのか、比較して")
        assert result["is_scatter"] is False

    def test_url_with_single_question_mark(self):
        result = detect_question_scatter("https://example.com/search?q=test を見てください")
        assert result["is_scatter"] is False

    def test_question_count_accuracy(self):
        result = detect_question_scatter("？？？？？")
        assert result["question_count"] == 5


# =============================================================================
# Unit tests: compute_question_density() — #97
# =============================================================================

class TestComputeQuestionDensity:
    """#97: Session cumulative question density tracking."""

    def _write_transcript(self, tmp_path, messages):
        """Helper to write a fake transcript JSONL."""
        path = tmp_path / "transcript.jsonl"
        lines = []
        for msg in messages:
            lines.append(json.dumps({
                "type": "user",
                "message": {"role": "user", "content": msg}
            }))
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)

    def test_high_density(self, tmp_path):
        # 5 messages, each with 4 question marks = avg 4.0
        path = self._write_transcript(tmp_path, ["？？？？"] * 5)
        density = compute_question_density(path)
        assert density == pytest.approx(4.0)

    def test_boundary_exactly_3(self, tmp_path):
        # 5 messages, each with 3 question marks = avg 3.0 (NOT > 3.0, should not fire)
        path = self._write_transcript(tmp_path, ["？？？"] * 5)
        density = compute_question_density(path)
        assert density == pytest.approx(3.0)

    def test_normal_density(self, tmp_path):
        path = self._write_transcript(tmp_path, ["質問？"] * 5)
        density = compute_question_density(path)
        assert density == pytest.approx(1.0)

    def test_zero_density(self, tmp_path):
        path = self._write_transcript(tmp_path, ["コード修正"] * 5)
        density = compute_question_density(path)
        assert density == 0.0

    def test_empty_transcript(self, tmp_path):
        path = tmp_path / "transcript.jsonl"
        path.write_text("", encoding="utf-8")
        density = compute_question_density(str(path))
        assert density == 0.0

    def test_nonexistent_file(self, tmp_path):
        density = compute_question_density(str(tmp_path / "nonexistent.jsonl"))
        assert density == 0.0

    def test_window_limits(self, tmp_path):
        # 10 messages: first 7 have 0 questions, last 3 have 6 each
        msgs = ["テスト"] * 7 + ["？？？？？？"] * 3
        path = self._write_transcript(tmp_path, msgs)
        density = compute_question_density(path, window=3)
        assert density == pytest.approx(6.0)

    def test_fewer_messages_than_window(self, tmp_path):
        path = self._write_transcript(tmp_path, ["？？"] * 2)
        density = compute_question_density(path, window=5)
        assert density == pytest.approx(2.0)

    def test_mixed_fullwidth_halfwidth(self, tmp_path):
        path = self._write_transcript(tmp_path, ["？?？?？"] * 5)
        density = compute_question_density(path)
        assert density == pytest.approx(5.0)


# =============================================================================
# Integration tests: scatter detection in main() — #96/#97
# =============================================================================

class TestScatterIntegration:
    """Integration: scatter detection in main() additionalContext."""

    @patch.object(ups, "SessionLogger")
    @patch.object(ups, "_run_detection")
    def test_scatter_detected_additional_context(self, mock_detection, mock_logger, tmp_path, capsys):
        """When scatter detected, additionalContext should contain guidance."""
        mock_detection.return_value = {"is_deviation": False, "reason": ""}
        mock_logger_instance = MagicMock()
        mock_logger_instance.get_session_stats.return_value = {"total_tokens": 100}
        mock_logger.return_value = mock_logger_instance

        # Create a transcript with high density
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(
            "\n".join(json.dumps({"type": "user", "message": {"role": "user", "content": "？？？？"}}) for _ in range(5)),
            encoding="utf-8"
        )

        input_data = json.dumps({
            "session_id": "test-session",
            "prompt": "これは何？どうする？なぜ？",
            "transcript_path": str(transcript)
        })

        from io import StringIO
        with patch("sys.stdin", StringIO(input_data)):
            with pytest.raises(SystemExit):
                ups.main()

        output = capsys.readouterr().out
        result = json.loads(output)
        ctx = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "質問散弾パターン検知" in ctx
        assert "gh issue create" in ctx

    @patch.object(ups, "SessionLogger")
    @patch.object(ups, "_run_detection")
    def test_no_scatter_no_issue_guidance(self, mock_detection, mock_logger, tmp_path, capsys):
        """When no scatter, additionalContext should not contain issue guidance."""
        mock_detection.return_value = {"is_deviation": False, "reason": ""}
        mock_logger_instance = MagicMock()
        mock_logger_instance.get_session_stats.return_value = {"total_tokens": 100}
        mock_logger.return_value = mock_logger_instance

        transcript = tmp_path / "t.jsonl"
        transcript.write_text(
            json.dumps({"type": "user", "message": {"role": "user", "content": "修正して"}}),
            encoding="utf-8"
        )

        input_data = json.dumps({
            "session_id": "test-session",
            "prompt": "バグを修正してください",
            "transcript_path": str(transcript)
        })

        from io import StringIO
        with patch("sys.stdin", StringIO(input_data)):
            with pytest.raises(SystemExit):
                ups.main()

        output = capsys.readouterr().out
        result = json.loads(output)
        ctx = result.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "gh issue create" not in ctx
