#!/usr/bin/env python3
"""Configuration management for Claude Context Manager hooks."""

import os
from pathlib import Path

# Base paths
HOME_DIR = Path.home()
CONTEXT_HISTORY_DIR = HOME_DIR / '.claude' / 'context-history'
TMP_DIR = CONTEXT_HISTORY_DIR / '.tmp'
SESSIONS_DIR = CONTEXT_HISTORY_DIR / 'sessions'
ARCHIVES_DIR = CONTEXT_HISTORY_DIR / 'archives'
METADATA_DIR = CONTEXT_HISTORY_DIR / '.metadata'

# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

# Token estimation (simple heuristic: 1 token ≈ 4 characters)
def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    return len(text) // 4
