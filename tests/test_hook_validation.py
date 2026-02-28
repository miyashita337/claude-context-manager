#!/usr/bin/env python3
"""Test suite for validating Hook configuration existence and correctness.

This test suite was created in response to a bug where hook settings were
accidentally deleted from settings.json, causing logs after 15:35 to not
be recorded. These tests ensure that the required hooks are always present
and correctly configured.
"""

import json
import subprocess
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
                    assert "python3" in command, (
                        f"Hook command for '{event_type}' must use 'python3'. "
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


class TestHookPathResolution:
    """Verify that hook commands use CWD-independent path resolution.

    Bug: Using $(git rev-parse --show-toplevel) is CWD-dependent and breaks when:
    1. Running from a git worktree (resolves to worktree root, not main repo)
    2. tmux session with CWD in another git repo (resolves to wrong repo entirely)

    Fix: Use $CLAUDE_PROJECT_DIR, an officially documented Claude Code env var
    that always points to the project root regardless of CWD.
    """

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_command_uses_claude_project_dir(self, hooks_config, event_type):
        """Hook commands must use $CLAUDE_PROJECT_DIR for path resolution."""
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
                    assert "$CLAUDE_PROJECT_DIR" in command, (
                        f"Hook command for '{event_type}' must use $CLAUDE_PROJECT_DIR "
                        f"for CWD-independent path resolution. Got: {command}"
                    )

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_command_does_not_use_git_rev_parse(self, hooks_config, event_type):
        """Hook commands must NOT use git rev-parse (CWD-dependent)."""
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
                    assert "git rev-parse" not in command, (
                        f"Hook command for '{event_type}' must NOT use "
                        f"'git rev-parse --show-toplevel' as it is CWD-dependent "
                        f"and breaks in worktrees and tmux sessions. "
                        f"Use $CLAUDE_PROJECT_DIR instead. Got: {command}"
                    )


class TestHookPathBoundary:
    """Boundary-value tests: verify git rev-parse --show-toplevel is CWD-dependent.

    These tests document WHY the old approach was broken, by proving that
    git rev-parse --show-toplevel returns different values depending on CWD.
    """

    MAIN_REPO_ROOT = PROJECT_ROOT

    def _find_worktree(self):
        """Find an existing worktree path, or return None."""
        worktrees_dir = self.MAIN_REPO_ROOT / ".claude" / "worktrees"
        if not worktrees_dir.exists():
            return None
        for child in worktrees_dir.iterdir():
            if child.is_dir() and (child / ".git").exists():
                return child
        return None

    def test_hook_path_repo_root_returns_correct_toplevel(self):
        """From main repo root, show-toplevel returns the repo root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(self.MAIN_REPO_ROOT),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        toplevel = Path(result.stdout.strip())
        assert toplevel == self.MAIN_REPO_ROOT.resolve(), (
            f"Expected {self.MAIN_REPO_ROOT.resolve()}, got {toplevel}"
        )

    def test_hook_path_deep_subdir_returns_correct_toplevel(self):
        """From a deeply nested subdir, show-toplevel still returns repo root."""
        deep_dir = self.MAIN_REPO_ROOT / "src" / "hooks" / "shared"
        if not deep_dir.exists():
            pytest.skip(f"Deep subdir not found: {deep_dir}")

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(deep_dir),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        toplevel = Path(result.stdout.strip())
        assert toplevel == self.MAIN_REPO_ROOT.resolve(), (
            f"Expected {self.MAIN_REPO_ROOT.resolve()}, got {toplevel}"
        )

    def test_hook_path_worktree_returns_wrong_toplevel(self):
        """From a worktree, show-toplevel returns the WORKTREE root, not main repo.

        This documents the bug that $CLAUDE_PROJECT_DIR fixes.
        """
        worktree_path = self._find_worktree()
        if worktree_path is None:
            pytest.skip("No worktree found to test with")

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(worktree_path),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        toplevel = Path(result.stdout.strip())
        # The bug: worktree returns its own root, not the main repo root
        assert toplevel != self.MAIN_REPO_ROOT.resolve(), (
            f"show-toplevel from worktree should NOT equal main repo root, "
            f"but got {toplevel}. This test documents the CWD-dependency bug."
        )

    def test_hook_path_outside_git_returns_error(self):
        """From outside any git repo, show-toplevel fails with exit code 128."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd="/tmp",
            capture_output=True, text=True,
        )
        assert result.returncode != 0, (
            "git rev-parse --show-toplevel should fail outside a git repo"
        )
        assert "not a git repository" in result.stderr, (
            f"Expected 'not a git repository' error, got: {result.stderr}"
        )


class TestHookPathSuccess:
    """Success tests: verify the fixed hook commands resolve to valid paths.

    With $CLAUDE_PROJECT_DIR set to the project root, every hook command
    must resolve to an existing Python script.
    """

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_hook_path_resolved_command_points_to_existing_script(
        self, hooks_config, event_type,
    ):
        """When $CLAUDE_PROJECT_DIR = PROJECT_ROOT, hook script path must exist."""
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
                if expected_script not in command:
                    continue
                # Simulate $CLAUDE_PROJECT_DIR expansion
                resolved = command.replace(
                    "$CLAUDE_PROJECT_DIR", str(PROJECT_ROOT),
                )
                # Extract the script path (between quotes after python3)
                # Format: python3 "<path>"
                parts = resolved.split('"')
                assert len(parts) >= 2, (
                    f"Cannot parse script path from command: {resolved}"
                )
                script_path = Path(parts[1])
                assert script_path.exists(), (
                    f"Resolved hook script does not exist: {script_path}\n"
                    f"Command: {command}\n"
                    f"$CLAUDE_PROJECT_DIR would be: {PROJECT_ROOT}"
                )

    @pytest.mark.parametrize("event_type", REQUIRED_HOOK_EVENTS)
    def test_hook_path_command_format_is_correct(self, hooks_config, event_type):
        """Hook command must follow: env -u GIT_DIR -u GIT_WORK_TREE python3 "$CLAUDE_PROJECT_DIR/src/hooks/<script>.py" """
        hooks = hooks_config.get("hooks", {})
        if event_type not in hooks:
            pytest.skip(f"{event_type} not present")

        expected_script = EXPECTED_HOOK_FILES[event_type]
        expected_command = (
            f'env -u GIT_DIR -u GIT_WORK_TREE python3 "$CLAUDE_PROJECT_DIR/src/hooks/{expected_script}"'
        )
        event_hooks = hooks[event_type]

        found = False
        for group in event_hooks:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                command = hook.get("command", "")
                if expected_script in command:
                    found = True
                    assert command == expected_command, (
                        f"Hook command format mismatch for '{event_type}'.\n"
                        f"Expected: {expected_command}\n"
                        f"Got:      {command}"
                    )
        assert found, f"No command found for {event_type}"

    def test_hook_path_worktree_also_has_hook_scripts(self):
        """In worktrees, hook scripts should also exist (git-tracked files)."""
        worktrees_dir = PROJECT_ROOT / ".claude" / "worktrees"
        if not worktrees_dir.exists():
            pytest.skip("No worktrees directory found")

        worktree_path = None
        for child in worktrees_dir.iterdir():
            if child.is_dir() and (child / ".git").exists():
                worktree_path = child
                break

        if worktree_path is None:
            pytest.skip("No worktree found to test with")

        for script_name in EXPECTED_HOOK_FILES.values():
            script_path = worktree_path / "src" / "hooks" / script_name
            assert script_path.exists(), (
                f"Hook script missing in worktree: {script_path}\n"
                "Git-tracked files should be present in worktrees."
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
