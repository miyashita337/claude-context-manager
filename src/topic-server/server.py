#!/usr/bin/env python3
"""Topic embedding server for Claude Code hook integration (Issue #28).

Loads sentence-transformers model once at startup and serves similarity
requests via HTTP, enabling low-latency topic deviation detection.

Endpoints:
  GET  /health     → {"status": "ok", "model": "..."}
  POST /similarity → {"prompt": "...", "session_id": "...", "baseline_messages": [...]}
                  ← {"similarity": 0.85, "is_deviation": false, "reason": "..."}
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print(
        "ERROR: sentence-transformers not installed.\n"
        "Run: pip install sentence-transformers",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORT = 8765

# Multilingual model: handles Japanese + English well (420MB)
# Swap to "all-MiniLM-L6-v2" (22MB) if Japanese support is not needed
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Cosine similarity below this value → topic deviation warning
SIMILARITY_THRESHOLD = float(__import__("os").environ.get("TOPIC_THRESHOLD", "0.45"))

# ---------------------------------------------------------------------------
# Model (loaded once at startup)
# ---------------------------------------------------------------------------

print(f"[topic-server] Loading model {MODEL_NAME} ...", file=sys.stderr, flush=True)
_model = SentenceTransformer(MODEL_NAME)
print("[topic-server] Model ready.", file=sys.stderr, flush=True)

# ---------------------------------------------------------------------------
# Session baseline cache  {session_id → np.ndarray}
# ---------------------------------------------------------------------------

_baselines: dict[str, np.ndarray] = {}
_lock = threading.Lock()


def _get_or_create_baseline(session_id: str, baseline_messages: list[str]) -> np.ndarray | None:
    """Return cached baseline embedding, creating it from baseline_messages if absent."""
    with _lock:
        if session_id in _baselines:
            return _baselines[session_id]

    if not baseline_messages:
        return None

    text = " ".join(baseline_messages[:3])  # use first 3 messages
    embedding = _model.encode(text, normalize_embeddings=True)

    with _lock:
        _baselines[session_id] = embedding

    return embedding


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Both vectors are already L2-normalized (normalize_embeddings=True)
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # suppress default access log
        pass

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "model": MODEL_NAME, "port": PORT})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/similarity":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception as e:
            self._send_json(400, {"error": f"invalid request: {e}"})
            return

        prompt: str = body.get("prompt", "")
        session_id: str = body.get("session_id", "")
        baseline_messages: list[str] = body.get("baseline_messages", [])

        if not prompt:
            self._send_json(400, {"error": "prompt is required"})
            return

        baseline = _get_or_create_baseline(session_id, baseline_messages)
        if baseline is None:
            # No baseline yet (first message in session) → no deviation possible
            self._send_json(200, {
                "similarity": 1.0,
                "is_deviation": False,
                "reason": "no_baseline",
            })
            return

        prompt_embedding = _model.encode(prompt, normalize_embeddings=True)
        similarity = _cosine_similarity(baseline, prompt_embedding)
        is_deviation = similarity < SIMILARITY_THRESHOLD

        self._send_json(200, {
            "similarity": round(similarity, 3),
            "is_deviation": is_deviation,
            "reason": f"similarity={similarity:.2f} (threshold={SIMILARITY_THRESHOLD})",
        })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    server = HTTPServer(("127.0.0.1", PORT), _Handler)
    print(f"[topic-server] Listening on 127.0.0.1:{PORT}", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[topic-server] Shutting down.", file=sys.stderr)


if __name__ == "__main__":
    main()
