#!/usr/bin/env python3
"""
Claude Code Analytics Engine
Analyzes ~/.claude/projects/*.jsonl to generate dashboard data
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


# ── Config ─────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "thresholds": {
        "tokens_per_day": 70000,
        "duration_minutes": 10,
        "cost_per_day": 10.0
    },
    "priority": ["cost", "duration", "tokens"],
    "time_range": {"default_hours": 6, "options": [1, 3, 6, 12, 24]},
    "detection": {"repetition_threshold": 100}
}

CONFIG_PATH = Path.home() / ".claude" / "analytics-config.json"


def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            # merge with defaults
            merged = DEFAULT_CONFIG.copy()
            for k, v in cfg.items():
                if isinstance(v, dict) and k in merged:
                    merged[k].update(v)
                else:
                    merged[k] = v
            return merged
        except Exception:
            pass
    return DEFAULT_CONFIG


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


# ── Data Loading ───────────────────────────────────────────────────────────

def find_project_dir(project_path=None):
    """Find the Claude projects directory for the given path"""
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return None

    if project_path:
        # Convert path to Claude's directory naming convention
        encoded = str(project_path).replace("/", "-")
        candidate = base / encoded
        if candidate.exists():
            return candidate

    # Default to current project
    cwd = Path.cwd()
    encoded = str(cwd).replace("/", "-")
    candidate = base / encoded
    if candidate.exists():
        return candidate

    # Fallback: return all projects base
    return base


def load_session(jsonl_path):
    """Load and parse a single JSONL session file"""
    events = []
    with open(jsonl_path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime"""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Analysis ───────────────────────────────────────────────────────────────

def analyze_session(events, session_id):
    """
    Analyze a single session's events.
    Returns a structured dict with messages, tools, tokens, anomalies.
    """
    messages = []
    current_msg = None
    tool_counts = defaultdict(int)
    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    session_start = None
    session_end = None

    # Model pricing (USD per 1M tokens) — approximate
    MODEL_PRICES = {
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
    }
    DEFAULT_PRICE = {"input": 3.0, "output": 15.0}

    for event in events:
        etype = event.get("type")

        if etype == "user":
            ts = parse_timestamp(event.get("timestamp"))
            if not session_start:
                session_start = ts
            session_end = ts

            msg_content = event.get("message", {}).get("content", "")
            if isinstance(msg_content, list):
                text = " ".join(
                    c.get("text", "") for c in msg_content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            else:
                text = str(msg_content)

            current_msg = {
                "role": "user",
                "timestamp": ts.isoformat() if ts else None,
                "text_preview": text[:200],
                "tools": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
            messages.append(current_msg)

        elif etype == "assistant":
            ts = parse_timestamp(event.get("timestamp"))
            session_end = ts

            msg = event.get("message", {})
            usage = msg.get("usage", {})
            model = msg.get("model", "")

            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            cc  = usage.get("cache_creation_input_tokens", 0)
            cr  = usage.get("cache_read_input_tokens", 0)

            total_input += inp
            total_output += out
            total_cache_create += cc
            total_cache_read += cr

            # Cost calculation
            price = MODEL_PRICES.get(model, DEFAULT_PRICE)
            cost = (inp * price["input"] + out * price["output"]) / 1_000_000

            # Extract tool_use from content
            tools_used = []
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tools_used.append(tool_name)
                        tool_counts[tool_name] += 1

            if current_msg:
                current_msg["input_tokens"] += inp
                current_msg["output_tokens"] += out
                current_msg["cost"] += cost
                current_msg["tools"].extend(tools_used)

    # Session duration
    duration_minutes = 0.0
    if session_start and session_end:
        try:
            delta = (session_end - session_start).total_seconds() / 60
            duration_minutes = max(0.0, delta)
        except Exception:
            pass

    total_tokens = total_input + total_output + total_cache_create + total_cache_read
    total_cost = sum(m.get("cost", 0) for m in messages if m["role"] == "user")

    return {
        "session_id": session_id,
        "start": session_start.isoformat() if session_start else None,
        "end": session_end.isoformat() if session_end else None,
        "duration_minutes": round(duration_minutes, 1),
        "total_tokens": total_tokens,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cache_create_tokens": total_cache_create,
        "cache_read_tokens": total_cache_read,
        "total_cost": round(total_cost, 4),
        "message_count": len(messages),
        "messages": messages,
        "tool_counts": dict(tool_counts),
    }


# ── Anomaly Detection ──────────────────────────────────────────────────────

def detect_anomalies(session, config):
    """Detect anomalies in a session"""
    anomalies = []
    thresh = config["thresholds"]
    rep_thresh = config["detection"]["repetition_threshold"]

    # Kitchen-Sink: too many tokens
    if session["total_tokens"] > 167_000:
        anomalies.append({
            "type": "kitchen_sink",
            "severity": "high" if session["total_tokens"] > 300_000 else "medium",
            "detail": f"Session has {session['total_tokens']:,} tokens (>167K)",
            "value": session["total_tokens"],
        })

    # High cost session
    if session["total_cost"] > 5.0:
        anomalies.append({
            "type": "high_cost",
            "severity": "high" if session["total_cost"] > 20.0 else "medium",
            "detail": f"Session cost ${session['total_cost']:.2f} (>$5)",
            "value": session["total_cost"],
        })

    # Long duration
    if session["duration_minutes"] > thresh["duration_minutes"]:
        anomalies.append({
            "type": "long_duration",
            "severity": "medium",
            "detail": f"Session ran {session['duration_minutes']:.1f} min (>{thresh['duration_minutes']} min threshold)",
            "value": session["duration_minutes"],
        })

    # Repetitive tool use
    for tool, count in session["tool_counts"].items():
        if count >= rep_thresh:
            anomalies.append({
                "type": "repetition",
                "severity": "high" if count >= rep_thresh * 3 else "medium",
                "detail": f"{tool} called {count} times (>={rep_thresh} threshold)",
                "tool": tool,
                "value": count,
            })

    return anomalies


# ── Summary ────────────────────────────────────────────────────────────────

def build_summary(sessions, config):
    """Build cross-session summary stats"""
    total_tokens = sum(s["total_tokens"] for s in sessions)
    total_cost   = sum(s["total_cost"] for s in sessions)

    # Token type breakdown
    total_input   = sum(s["input_tokens"] for s in sessions)
    total_output  = sum(s["output_tokens"] for s in sessions)
    total_cache_c = sum(s["cache_create_tokens"] for s in sessions)
    total_cache_r = sum(s["cache_read_tokens"] for s in sessions)

    # Tool totals across sessions
    all_tools = defaultdict(int)
    for s in sessions:
        for t, c in s["tool_counts"].items():
            all_tools[t] += c

    # Heaviest sessions
    heavy = sorted(sessions, key=lambda s: s["total_cost"], reverse=True)[:5]

    return {
        "session_count": len(sessions),
        "total_tokens": total_tokens,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_create_tokens": total_cache_c,
        "total_cache_read_tokens": total_cache_r,
        "total_cost": round(total_cost, 4),
        "tool_totals": dict(sorted(all_tools.items(), key=lambda x: -x[1])[:15]),
        "heaviest_sessions": [
            {
                "session_id": s["session_id"],
                "total_cost": s["total_cost"],
                "total_tokens": s["total_tokens"],
                "duration_minutes": s["duration_minutes"],
                "start": s["start"],
                "anomaly_count": len(s.get("anomalies", [])),
            }
            for s in heavy
        ],
        "thresholds": config["thresholds"],
    }


# ── Main ───────────────────────────────────────────────────────────────────

def run_analysis(project_dir=None, max_sessions=10, output_path=None, config=None):
    if config is None:
        config = load_config()

    pdir = find_project_dir(project_dir)
    if not pdir:
        print("❌ No Claude project directory found", file=sys.stderr)
        sys.exit(1)

    # Collect JSONL files, sorted by modification time (newest first)
    jsonl_files = sorted(
        pdir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:max_sessions]

    if not jsonl_files:
        print(f"❌ No session files found in {pdir}", file=sys.stderr)
        sys.exit(1)

    sessions = []
    for path in jsonl_files:
        try:
            events = load_session(path)
            session = analyze_session(events, path.stem)
            session["anomalies"] = detect_anomalies(session, config)
            sessions.append(session)
        except Exception as e:
            print(f"⚠️  Skipping {path.name}: {e}", file=sys.stderr)

    summary = build_summary(sessions, config)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(pdir),
        "config": config,
        "summary": summary,
        "sessions": sessions,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Analytics data saved to {out}", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Code Analytics Engine")
    parser.add_argument("--project", help="Project directory path")
    parser.add_argument("--sessions", type=int, default=10, help="Max sessions to analyze (default: 10)")
    parser.add_argument("--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--config-init", action="store_true", help="Initialize default config file")
    args = parser.parse_args()

    if args.config_init:
        save_config(DEFAULT_CONFIG)
        print(f"✅ Config initialized at {CONFIG_PATH}")
        sys.exit(0)

    run_analysis(
        project_dir=args.project,
        max_sessions=args.sessions,
        output_path=args.output,
    )
