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


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_api_response(status: int, body: dict) -> MagicMock:
    """Return a mock HTTPSConnection whose getresponse() yields (status, body)."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body).encode()

    conn = MagicMock()
    conn.getresponse.return_value = resp
    return conn


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
        conn = _mock_api_response(200, _api_ok(True))
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("refactor this function", ["fix bug"])

        assert result["decision"] == "pass"

    def test_off_topic_returns_warn_with_reason(self):
        """ok:false → decision=warn, reason propagated."""
        conn = _mock_api_response(200, _api_ok(False, "weather unrelated to work"))
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("what's the weather today?", ["fix bug"])

        assert result["decision"] == "warn"
        assert "weather" in result["reason"]

    # ── API error codes ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
    def test_api_non_200_returns_warn(self, status):
        """Any non-200 status → warn with api_error tag."""
        conn = _mock_api_response(status, {"error": "something went wrong"})
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_api_error" in result["reason"]
        assert str(status) in result["reason"]

    # ── network / connection errors ──────────────────────────────────────────

    def test_timeout_returns_warn(self):
        """OSError timeout → warn, never raises."""
        import socket

        conn = MagicMock()
        conn.getresponse.side_effect = socket.timeout("timed out")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_error" in result["reason"]

    def test_oserror_returns_warn(self):
        """OSError (connection refused) → warn."""
        conn = MagicMock()
        conn.request.side_effect = OSError("connection refused")
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_error" in result["reason"]

    # ── malformed response ───────────────────────────────────────────────────

    def test_malformed_json_in_text_returns_warn(self):
        """LLM returns non-JSON text → warn, never raises."""
        conn = _mock_api_response(
            200, {"content": [{"type": "text", "text": "I cannot determine..."}]}
        )
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"

    def test_empty_content_array_returns_warn(self):
        """Empty content list → warn."""
        conn = _mock_api_response(200, {"content": []})
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"
        assert "p2_empty_response" in result["reason"]

    def test_missing_ok_field_defaults_to_pass(self):
        """'ok' field absent → default on-topic (conservative: avoid false positives)."""
        conn = _mock_api_response(
            200, {"content": [{"type": "text", "text": '{"reason": "unclear"}'}]}
        )
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "pass"

    def test_entire_response_body_is_not_json(self):
        """API body is plain text (e.g. WAF HTML) → warn."""
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b"<html>Gateway Error</html>"
        conn = MagicMock()
        conn.getresponse.return_value = resp

        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "warn"

    def test_empty_baseline_messages(self):
        """Empty baseline is handled without error."""
        conn = _mock_api_response(200, _api_ok(True))
        with patch("http.client.HTTPSConnection", return_value=conn):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                result = ups._query_llm_p2("some prompt", [])

        assert result["decision"] == "pass"


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
