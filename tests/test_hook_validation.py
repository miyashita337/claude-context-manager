#!/usr/bin/env python3
"""Test suite for validating Hook configuration existence and correctness.

This test suite was created in response to a bug where hook settings were
accidentally deleted from settings.json, causing logs after 15:35 to not
be recorded. These tests ensure that the required hooks are always present
and correctly configured.
"""

import json
from pathlib import Path

import pytest

# === Constants ===

PROJECT_ROOT = Path(__file__).parent.parent
HOOKS_DIR = PROJECT_ROOT / "src" / "hooks"

# Project-level hook config (official path)
PROJECT_HOOKS_JSON = PROJECT_ROOT / ".claude" / "settings.json"

# Required hook event types
REQUIRED_HOOK_EVENTS = ["UserPromptSubmit", "PostToolUse", "Stop"]

# Expected hook script files (relative to src/hooks/)
EXPECTED_HOOK_FILES = {
    "UserPromptSubmit": "user-prompt-submit.py",
    "PostToolUse": "post-tool-use.py",
    "Stop": "stop.py",
}

# Shared modules required by hooks
REQUIRED_SHARED_MODULES = ["config.py", "logger.py", "__init__.py"]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def hooks_config():
    """Load the project settings.json hook configuration."""
    assert PROJECT_HOOKS_JSON.exists(), (
        f"Project hooks config not found: {PROJECT_HOOKS_JSON}\n"
        "This file is required for Claude Context Manager to record session logs.\n"
        "Official hook config path: .claude/settings.json"
    )
    with open(PROJECT_HOOKS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# Task #1: Hook Existence Validation Tests
# ============================================================================


class TestHookConfigExists:
    """Verify that the hook configuration file exists and is valid JSON."""

    def test_hooks_json_exists(self):
        """.claude/settings.json must exist with hooks configuration."""
        assert PROJECT_HOOKS_JSON.exists(), (
            f"settings.json not found at {PROJECT_HOOKS_JSON}. "
            "Hook configuration is required for session logging."
        )

    def test_hooks_json_valid_json(self):
        """settings.json must contain valid JSON."""
        with open(PROJECT_HOOKS_JSON, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"settings.json contains invalid JSON: {e}")
        assert isinstance(data, dict), "settings.json root must be a JSON object"

    def test_hooks_json_has_hooks_key(self, hooks_config):
        """settings.json must contain a 'hooks' key."""
        assert "hooks" in hooks_config, (
            "settings.json is missing the 'hooks' key. "
            "No hook events are configured."
        )
        assert isinstance(hooks_config["hooks"], dict), (
            "'hooks' must be a JSON object mapping event types to hook arrays."
        )


class TestRequiredHookEvents:
    """Verify that all required hook events are configured."""

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_required_event_exists(self, hooks_config, event_type):
        """Each required hook event type must be present in the config."""
        hooks = hooks_config.get("hooks", {})
        assert event_type in hooks, (
            f"Required hook event '{event_type}' is missing from .claude/settings.json. "
            f"This will cause session logs to not be recorded for {event_type} events."
        )

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_event_has_hook_entries(self, hooks_config, event_type):
        """Each required event must have at least one hook entry."""
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present (covered by test_required_event_exists)")

        event_hooks = hooks[event_type]
        assert isinstance(event_hooks, list), (
            f"'{event_type}' must be a list of hook groups."
        )
        assert len(event_hooks) > 0, (
            f"'{event_type}' has no hook entries configured."
        )

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_event_has_command_hook(self, hooks_config, event_type):
        """Each required event must have at least one 'command' type hook."""
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present")

        event_hooks = hooks[event_type]
        has_command = False
        for group in event_hooks:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    has_command = True
                    break
            if has_command:
                break

        assert has_command, (
            f"'{event_type}' has no 'command' type hooks. "
            "At least one command hook is required for logging."
        )


class TestHookCommandPaths:
    """Verify that hook commands point to valid Python scripts."""

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_command_references_correct_script(self, hooks_config, event_type):
        """Hook command must reference the expected Python script."""
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present")

        expected_script = EXPECTED_HOOK_FILES[event_type]
        event_hooks = hooks[event_type]

        found_expected = False
        for group in event_hooks:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command", "")
                if expected_script in command:
                    found_expected = True
                    break
            if found_expected:
                break

        assert found_expected, (
            f"'{event_type}' does not reference '{expected_script}' in any command. "
            f"Expected script file: src/hooks/{expected_script}"
        )

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_command_uses_python3(self, hooks_config, event_type):
        """Hook commands must use python3 as the interpreter."""
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present")

        expected_script = EXPECTED_HOOK_FILES[event_type]
        event_hooks = hooks[event_type]

        for group in event_hooks:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command", "")
                if expected_script in command:
                    assert command.startswith("python3 "), (
                        f"Hook command for '{event_type}' must start with 'python3'. "
                        f"Got: {command}"
                    )


class TestHookScriptFiles:
    """Verify that the actual hook Python scripts exist on disk."""

    @pytest.mark.parametrize(
        "event_type,script_name",
        list(EXPECTED_HOOK_FILES.items()),
    )
    def test_hook_script_exists(self, event_type, script_name):
        """Hook Python script must exist in src/hooks/."""
        script_path = HOOKS_DIR / script_name
        assert script_path.exists(), (
            f"Hook script not found: {script_path}\n"
            f"The '{event_type}' hook is configured but the script is missing."
        )

    @pytest.mark.parametrize(
        "event_type,script_name",
        list(EXPECTED_HOOK_FILES.items()),
    )
    def test_hook_script_is_python(self, event_type, script_name):
        """Hook scripts must be valid Python files (contain 'def main')."""
        script_path = HOOKS_DIR / script_name
        if not script_path.exists():
            pytest.skip("Script does not exist (covered by test_hook_script_exists)")

        content = script_path.read_text(encoding="utf-8")
        assert "def main()" in content, (
            f"Hook script '{script_name}' is missing a 'main()' function. "
            "All hook scripts must define a main() entry point."
        )

    @pytest.mark.parametrize("module_name", REQUIRED_SHARED_MODULES)
    def test_shared_module_exists(self, module_name):
        """Required shared modules must exist in src/hooks/shared/."""
        shared_dir = HOOKS_DIR / "shared"
        module_path = shared_dir / module_name
        assert module_path.exists(), (
            f"Shared module not found: {module_path}\n"
            "Hook scripts depend on shared modules for logging functionality."
        )


class TestHookTimeouts:
    """Verify that hook timeouts are configured correctly."""

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_hook_has_timeout(self, hooks_config, event_type):
        """Each hook should have a timeout configured."""
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present")

        expected_script = EXPECTED_HOOK_FILES[event_type]
        event_hooks = hooks[event_type]

        for group in event_hooks:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command", "")
                if expected_script in command:
                    assert "timeout" in hook, (
                        f"Hook for '{event_type}' is missing a timeout. "
                        "Hooks without timeouts can block Claude Code indefinitely."
                    )
                    timeout = hook["timeout"]
                    assert isinstance(timeout, (int, float)), (
                        f"Timeout for '{event_type}' must be a number, got {type(timeout)}"
                    )
                    assert timeout > 0, (
                        f"Timeout for '{event_type}' must be positive, got {timeout}"
                    )

    def test_stop_hook_timeout_is_adequate(self, hooks_config):
        """Stop hook should have a longer timeout (>= 10s) for finalization."""
        hooks = hooks_config.get("hooks", {})
        if "Stop" not in hooks:
            pytest.skip("Stop hook not present")

        for group in hooks["Stop"]:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command", "")
                if "stop.py" in command:
                    timeout = hook.get("timeout", 0)
                    assert timeout >= 10, (
                        f"Stop hook timeout should be >= 10 seconds for finalization. "
                        f"Current: {timeout}s"
                    )
