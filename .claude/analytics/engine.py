#!/usr/bin/env python3
"""
Claude Code Analytics Engine
Analyzes ~/.claude/projects/*.jsonl to generate dashboard data
"""

import json
import os
import re
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

    seen_assistant_ids = set()

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
            msg_id = msg.get("id", "")

            # Dedup: count tokens only on first occurrence of each message id.
            # tool_use items appear on duplicate events, so always extract those.
            is_first = True
            if msg_id:
                if msg_id in seen_assistant_ids:
                    is_first = False
                else:
                    seen_assistant_ids.add(msg_id)

            # Token counting (first occurrence only to avoid triple-counting)
            if is_first:
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

                if current_msg:
                    current_msg["input_tokens"] += inp
                    current_msg["output_tokens"] += out
                    current_msg["cost"] += cost

            # Extract tool_use from content (all occurrences - tools appear on duplicates)
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_counts[tool_name] += 1
                        if current_msg:
                            current_msg["tools"].append(tool_name)

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


# ── Bottleneck Analysis ───────────────────────────────────────────────────

_BASH_FILE_RE = re.compile(r'(?:cat|head|tail|less|more)\s+["\']?(/[^\s"\'|>]+)')


def analyze_bottlenecks(raw_events):
    """
    Fact-based bottleneck scan of raw JSONL events.
    Every reported issue includes concrete evidence: message index, measured
    char/token counts, and file paths extracted from actual event data.

    Returns bottleneck_report dict with:
    - bottleneck_score: 0-100 (higher = more waste)
    - issues: list of detected problems with message indices and measured values
    - issue_counts: breakdown by issue type
    - top_wasteful_messages: top 5 by estimated token waste
    """
    issues = []
    msg_index = -1
    # Track file access across Read, Edit, Write AND Bash cat/head/tail
    file_access_counts = defaultdict(list)  # file_path -> [msg_indices]
    tool_sequence = []  # (tool_name, msg_index) for consecutive detection
    user_question_counts = []
    # Full token count: input + cache_read + cache_create (= real context size)
    per_msg_full_tokens = []  # (msg_index, full_tokens, input, cache_read, cache_create)
    per_msg_waste = defaultdict(int)  # msg_index -> estimated waste tokens
    seen_assistant_ids = set()

    for event in raw_events:
        etype = event.get("type")

        if etype == "user":
            msg_index += 1
            # --- Large tool result detection ---
            msg_content = event.get("message", {}).get("content", "")
            if isinstance(msg_content, list):
                for item in msg_content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "tool_result":
                        content = item.get("content", "")
                        if isinstance(content, list):
                            text_len = sum(
                                len(c.get("text", ""))
                                for c in content
                                if isinstance(c, dict)
                            )
                        elif isinstance(content, str):
                            text_len = len(content)
                        else:
                            text_len = 0
                        if text_len > 5000:
                            # Extract a preview for evidence
                            preview = ""
                            if isinstance(content, str):
                                preview = content[:120].replace("\n", " ")
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("text"):
                                        preview = c["text"][:120].replace("\n", " ")
                                        break
                            issues.append({
                                "type": "large_tool_result",
                                "msg_index": msg_index,
                                "chars": text_len,
                                "detail": f"Msg #{msg_index}: tool result {text_len:,} chars",
                                "preview": preview,
                                "value": text_len,
                            })
                            per_msg_waste[msg_index] += text_len // 4

            # --- Question scatter tracking ---
            content = event.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                q_text = " ".join(text_parts)
            else:
                q_text = str(content)
            q_count = q_text.count("\uff1f") + q_text.count("?")
            user_question_counts.append(q_count)

        elif etype == "assistant":
            msg = event.get("message", {})
            msg_id = msg.get("id", "")
            is_first_for_id = True
            if msg_id:
                if msg_id in seen_assistant_ids:
                    is_first_for_id = False  # skip token counting, but still track tools
                else:
                    seen_assistant_ids.add(msg_id)

            usage = msg.get("usage", {}) if is_first_for_id else {}
            inp = usage.get("input_tokens", 0)
            cr = usage.get("cache_read_input_tokens", 0)
            cc = usage.get("cache_creation_input_tokens", 0)
            full = inp + cr + cc
            if full > 0:
                per_msg_full_tokens.append((msg_index, full, inp, cr, cc))

            # Track tool sequence and file access
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_input = item.get("input", {})
                        tool_sequence.append((tool_name, msg_index))

                        # File access via Read/Edit/Write
                        file_path = tool_input.get("file_path", "")
                        if file_path and tool_name in ("Read", "Edit", "Write"):
                            file_access_counts[file_path].append(msg_index)

                        # File access via Bash cat/head/tail
                        if tool_name == "Bash":
                            cmd = tool_input.get("command", "")
                            for match in _BASH_FILE_RE.findall(cmd):
                                file_access_counts[match].append(msg_index)

    # --- Repeated file access (3+ times same file in session) ---
    for fpath, indices in file_access_counts.items():
        if len(indices) >= 3:
            short_name = fpath.rsplit("/", 1)[-1] if "/" in fpath else fpath
            issues.append({
                "type": "repeated_file_read",
                "msg_indices": indices,
                "file": fpath,
                "short_name": short_name,
                "access_count": len(indices),
                "detail": f"{short_name} accessed {len(indices)}x at msgs {indices}",
                "value": len(indices),
            })
            for idx in indices[2:]:
                per_msg_waste[idx] += 500

    # --- Token spikes (full context > 1.5x session avg AND > 50K) ---
    if per_msg_full_tokens:
        avg_full = sum(t[1] for t in per_msg_full_tokens) / len(per_msg_full_tokens)
        threshold = avg_full * 1.5
        for idx, full, inp, cr, cc in per_msg_full_tokens:
            if full > threshold and full > 50000:
                excess = full - int(avg_full)
                issues.append({
                    "type": "token_spike",
                    "msg_index": idx,
                    "full_tokens": full,
                    "input_tokens": inp,
                    "cache_read": cr,
                    "cache_create": cc,
                    "session_avg": int(avg_full),
                    "detail": f"Msg #{idx}: {full:,} tokens (avg {int(avg_full):,}, {full/avg_full:.1f}x)",
                    "value": full,
                })
                per_msg_waste[idx] += excess

    # --- Tool loops (same tool 3+ consecutive times) ---
    if tool_sequence:
        run_start = 0
        for i in range(1, len(tool_sequence)):
            if tool_sequence[i][0] != tool_sequence[run_start][0]:
                _check_tool_run(tool_sequence, run_start, i, issues, per_msg_waste)
                run_start = i
        _check_tool_run(tool_sequence, run_start, len(tool_sequence), issues, per_msg_waste)

    # --- Question scatter analysis ---
    if user_question_counts:
        avg_q = sum(user_question_counts) / len(user_question_counts)
        if avg_q > 2.5:
            issues.append({
                "type": "question_scatter",
                "avg_questions_per_msg": round(avg_q, 2),
                "total_user_messages": len(user_question_counts),
                "detail": f"Avg {avg_q:.1f} questions/msg across {len(user_question_counts)} messages",
                "value": round(avg_q, 2),
            })

    # --- Bottleneck score ---
    # Weighted by actual measured impact, not just count
    score = 0.0
    for issue in issues:
        itype = issue["type"]
        if itype == "large_tool_result":
            # Scale by size: 78K chars = ~20 points, 5K = ~1 point
            score += min(20, issue["chars"] / 4000)
        elif itype == "repeated_file_read":
            score += issue["access_count"] * 2
        elif itype == "token_spike":
            score += min(15, (issue["full_tokens"] - issue["session_avg"]) / 10000)
        elif itype == "tool_loop":
            score += issue["value"] * 1.5
        elif itype == "question_scatter":
            score += min(10, (issue.get("value", 2.5) - 2.5) * 10)
    score = min(100, int(score))

    # --- Top wasteful messages ---
    top_wasteful = sorted(per_msg_waste.items(), key=lambda x: -x[1])[:5]

    # Build issue_counts
    issue_types = set(i["type"] for i in issues)
    issue_counts = {t: sum(1 for i in issues if i["type"] == t) for t in issue_types}

    return {
        "bottleneck_score": score,
        "issues": issues,
        "issue_counts": issue_counts,
        "top_wasteful_messages": [
            {"msg_index": idx, "estimated_waste_tokens": waste}
            for idx, waste in top_wasteful
        ],
    }


def _check_tool_run(tool_sequence, start, end, issues, per_msg_waste):
    """Helper: detect a consecutive tool run of length >= 3."""
    run_len = end - start
    if run_len >= 3:
        tool_name = tool_sequence[start][0]
        affected = sorted(set(tool_sequence[j][1] for j in range(start, end)))
        issues.append({
            "type": "tool_loop",
            "msg_indices": affected,
            "tool": tool_name,
            "consecutive_count": run_len,
            "detail": f"{tool_name} used {run_len} consecutive times (msgs {affected})",
            "value": run_len,
        })
        for idx in affected:
            per_msg_waste[idx] += 200 * run_len


def compute_cache_patterns(raw_events):
    """
    Fact-based cache usage analysis from per-message token data.
    Returns measured values:
    - first_turn_overhead: cache_creation_input_tokens on first assistant message
    - total_cache_create: total cache_creation tokens across session
    - total_cache_read: total cache_read tokens across session
    - total_input: total non-cached input tokens
    - avg_cache_efficiency: cache_read / (cache_read + input_tokens) ratio
    - sessions_with_poor_cache: 1 if efficiency < 0.5 (with meaningful data), else 0
    - per_turn_detail: first 5 turns with token breakdown for evidence
    """
    seen_ids = set()
    first_turn_overhead = 0
    total_cache_read = 0
    total_input = 0
    total_cache_create = 0
    is_first_assistant = True
    per_turn_detail = []

    for event in raw_events:
        if event.get("type") != "assistant":
            continue

        msg = event.get("message", {})
        msg_id = msg.get("id", "")
        if msg_id:
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

        usage = msg.get("usage", {})
        cc = usage.get("cache_creation_input_tokens", 0)
        cr = usage.get("cache_read_input_tokens", 0)
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)

        if is_first_assistant:
            first_turn_overhead = cc
            is_first_assistant = False

        total_cache_read += cr
        total_input += inp
        total_cache_create += cc

        if len(per_turn_detail) < 5:
            per_turn_detail.append({
                "input": inp, "cache_read": cr, "cache_create": cc, "output": out,
            })

    denominator = total_cache_read + total_input
    avg_efficiency = (total_cache_read / denominator) if denominator > 0 else 0.0
    poor_cache = 1 if (avg_efficiency < 0.5 and denominator > 1000) else 0

    return {
        "first_turn_overhead": first_turn_overhead,
        "total_cache_create": total_cache_create,
        "total_cache_read": total_cache_read,
        "total_input": total_input,
        "avg_cache_efficiency": round(avg_efficiency, 4),
        "sessions_with_poor_cache": poor_cache,
        "per_turn_detail": per_turn_detail,
    }


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

    # Aggregate cache patterns across sessions
    cache_efficiencies = []
    total_first_turn = 0
    poor_cache_count = 0
    for s in sessions:
        cp = s.get("cache_patterns", {})
        total_first_turn += cp.get("first_turn_overhead", 0)
        eff = cp.get("avg_cache_efficiency", 0)
        if eff > 0 or cp.get("sessions_with_poor_cache", 0):
            cache_efficiencies.append(eff)
        poor_cache_count += cp.get("sessions_with_poor_cache", 0)

    avg_cache_eff = (
        sum(cache_efficiencies) / len(cache_efficiencies)
        if cache_efficiencies else 0.0
    )

    # Aggregate bottleneck stats
    total_bottleneck_score = 0
    all_issue_types = defaultdict(int)
    for s in sessions:
        br = s.get("bottleneck_report", {})
        total_bottleneck_score += br.get("bottleneck_score", 0)
        for itype, cnt in br.get("issue_counts", {}).items():
            all_issue_types[itype] += cnt

    avg_bottleneck = (
        total_bottleneck_score / len(sessions) if sessions else 0
    )

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
                "bottleneck_score": s.get("bottleneck_report", {}).get("bottleneck_score", 0),
            }
            for s in heavy
        ],
        "thresholds": config["thresholds"],
        "cache_patterns": {
            "avg_first_turn_overhead": total_first_turn // max(len(sessions), 1),
            "avg_cache_efficiency": round(avg_cache_eff, 4),
            "sessions_with_poor_cache": poor_cache_count,
        },
        "bottleneck_summary": {
            "avg_bottleneck_score": round(avg_bottleneck, 1),
            "total_issues": sum(all_issue_types.values()),
            "issue_breakdown": dict(all_issue_types),
        },
    }


# ── Main ───────────────────────────────────────────────────────────────────

def generate_html_output(result, html_path):
    """Generate a self-contained HTML file with data embedded (works with file://)"""
    template = Path(__file__).parent / "dashboard" / "index.html"
    if not template.exists():
        print(f"❌ Template not found: {template}", file=sys.stderr)
        return
    html = template.read_text(encoding="utf-8")
    data_js = json.dumps(result, ensure_ascii=False)
    injection = f"<script>window.__ANALYTICS_DATA__ = {data_js};</script>"
    html = html.replace("</head>", f"{injection}\n</head>")
    out = Path(html_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard saved to {out}", file=sys.stderr)


def load_reviews():
    """Load review markdown files from ~/.claude/reviews/"""
    reviews_dir = Path.home() / ".claude" / "reviews"
    reviews = []
    if not reviews_dir.exists():
        return reviews
    for md_file in sorted(reviews_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            content = md_file.read_text(encoding="utf-8")
            reviews.append({
                "filename": md_file.name,
                "mtime": md_file.stat().st_mtime,
                "content": content,
            })
        except Exception:
            pass
    return reviews


def run_analysis(project_dir=None, max_sessions=10, output_path=None, html_output_path=None, config=None, session_id=None):
    if config is None:
        config = load_config()

    pdir = find_project_dir(project_dir)
    if not pdir:
        print("❌ No Claude project directory found", file=sys.stderr)
        sys.exit(1)

    # Collect JSONL files, sorted by modification time (newest first)
    all_jsonl = sorted(
        pdir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if session_id:
        jsonl_files = [f for f in all_jsonl if f.stem == session_id]
        if not jsonl_files:
            print(f"❌ Session {session_id} not found in {pdir}", file=sys.stderr)
            sys.exit(1)
    else:
        jsonl_files = all_jsonl[:max_sessions]

    if not jsonl_files:
        print(f"❌ No session files found in {pdir}", file=sys.stderr)
        sys.exit(1)

    sessions = []
    for path in jsonl_files:
        try:
            events = load_session(path)
            session = analyze_session(events, path.stem)
            session["anomalies"] = detect_anomalies(session, config)
            session["bottleneck_report"] = analyze_bottlenecks(events)
            session["cache_patterns"] = compute_cache_patterns(events)
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
        "reviews": load_reviews(),
    }

    if html_output_path:
        generate_html_output(result, html_output_path)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Analytics data saved to {out}", file=sys.stderr)
    if not output_path and not html_output_path:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Code Analytics Engine")
    parser.add_argument("--project", help="Project directory path")
    parser.add_argument("--sessions", type=int, default=10, help="Max sessions to analyze (default: 10)")
    parser.add_argument("--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--html-output", help="Output self-contained HTML path (works with file://)")
    parser.add_argument("--session-id", help="Analyze specific session ID only")
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
        html_output_path=args.html_output,
        session_id=args.session_id,
    )
