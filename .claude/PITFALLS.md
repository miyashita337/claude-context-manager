# PITFALLS.md

**Purpose**: A grep-friendly database of known error patterns, solutions, and prevention strategies encountered in Claude Context Manager development.

**Last Updated**: 2026-02-17

---

## Table of Contents

- [Git Errors](#git-errors)
- [Hook Errors](#hook-errors)
- [Security Errors](#security-errors)
- [API Errors](#api-errors)
- [Build Errors](#build-errors)
- [ccusage Errors](#ccusage-errors)

---

## Git Errors

### GIT-001: Initial Commit HEAD Error

**Error Signature**: `fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree`

**Context**: Occurs when trying to unstage files in a new repository with no commits yet.

**Root Cause**: `HEAD` doesn't exist until the first commit is created.

**Solution**:
```bash
# ❌ WRONG (before first commit)
git reset HEAD <file>

# ✅ CORRECT (before first commit)
git rm --cached <file>
```

**Prevention**:
```bash
# Check if HEAD exists before using git reset
git rev-parse HEAD >/dev/null 2>&1 && git reset HEAD <file> || git rm --cached <file>
```

**References**:
- CLAUDE.md: "初回コミット時の注意"
- Git docs: https://git-scm.com/docs/git-rm

**Tags**: `git`, `initial-commit`, `staging`, `HEAD`

**Severity**: Medium

**Date Added**: 2026-02-15

---

### GIT-002: Non-Official Hook Path

**Error Signature**: Hook not executing despite proper configuration

**Context**: Hooks configured in `.claude/hooks/hooks.json` (non-official path) don't execute.

**Root Cause**: Claude Code only recognizes `.claude/settings.json` as the official hook configuration path.

**Solution**:
```bash
# ❌ WRONG PATH
.claude/hooks/hooks.json

# ✅ OFFICIAL PATH
.claude/settings.json
```

**Migration**:
```bash
# 1. Read old configuration
cat .claude/hooks/hooks.json

# 2. Merge into official settings.json
# Edit .claude/settings.json and add "hooks" section

# 3. Verify
make startup-check
```

**Prevention**:
- Always use `.claude/settings.json` for hook configuration
- Run `/fact-check` to verify paths against official documentation
- Include path validation in tests

**References**:
- Official docs: https://docs.claude.com/claude-code/hooks
- Previous incident: Session 2026-02-14 (non-official path caused silent failure)

**Tags**: `hooks`, `configuration`, `path`, `settings`

**Severity**: High

**Date Added**: 2026-02-15

---

## Hook Errors

### HOOK-001: Hook Execution Not Detected in Tests

**Error Signature**: Tests pass but hooks don't actually execute in real usage

**Context**: Unit tests mock subprocess calls, missing actual hook execution validation.

**Root Cause**: Insufficient integration testing - tests only verify configuration, not execution.

**Solution**:
```python
# ❌ INSUFFICIENT (unit test only)
def test_hook_config():
    assert config["hooks"]["start"] == "scripts/start.sh"

# ✅ BETTER (integration test)
def test_hook_actually_executes(tmp_path):
    result = subprocess.run(
        ["python", "hook_runner.py", "--hook", "start"],
        capture_output=True,
        text=True
    )
    assert "Hook executed successfully" in result.stdout
    assert result.returncode == 0
```

**Prevention**:
- Add end-to-end tests that actually execute hooks
- Test both success and failure scenarios
- Verify output files are created
- Check process exit codes

**Testing Strategy**:
```python
# tests/test_hook_integration.py
class TestHookExecution:
    def test_hook_creates_expected_output(self):
        """Verify hook actually runs and produces output"""

    def test_hook_fails_on_invalid_input(self):
        """Verify hook error handling works"""
```

**References**:
- pytest docs: https://docs.pytest.org/en/stable/
- Previous incident: Session 2026-02-14 (hook path error not caught by tests)

**Tags**: `testing`, `hooks`, `integration`, `subprocess`

**Severity**: High

**Date Added**: 2026-02-15

---

### HOOK-002: UserPromptSubmit JSON Parse Error

**Error Signature**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

**Context**: "UserPromptSubmit hook error" appears in Claude Code, debug log shows JSON parse failures

**Root Cause**:
1. Shell profile (`.bashrc`, `.zshrc`) prints text on startup
2. This text pollutes the JSON stdin that hook receives
3. Hook script fails to parse malformed JSON

**Solution**:

**Step 1 - Diagnose**:
```bash
# Check debug log for exact error
tail -50 ~/.claude/hook-debug.log | grep -A 5 "UserPromptSubmit Error"
```

**Step 2 - Fix Shell Profile**:
```bash
# Add guards to .bashrc / .zshrc
if [[ -z "$PS1" ]]; then
    # Non-interactive shell - suppress all output
    return
fi

# Or guard individual print statements
[[ -n "$PS1" ]] && echo "Welcome message"
```

**Step 3 - Improve Hook Error Handling**:
```python
# Add stdin logging to hook script
stdin_content = sys.stdin.read()

# Log raw stdin for debugging
debug_log = Path.home() / '.claude' / 'hook-debug.log'
with open(debug_log, 'a') as f:
    f.write(f"\n=== Raw stdin ===\n{repr(stdin_content)}\n")

# Handle empty/invalid stdin
if not stdin_content or not stdin_content.strip():
    print(json.dumps({"hookSpecificOutput": {"status": "skipped"}}))
    sys.exit(0)
```

**Step 4 - Add Stdin Sanitization (2026-02-15 Update)**:
```python
def sanitize_stdin(stdin_content: str, hook_name: str) -> str:
    """Remove non-JSON text from stdin before the first '{' or '['."""
    if not stdin_content:
        return stdin_content

    # Find first JSON character
    start_idx = -1
    for i, char in enumerate(stdin_content):
        if char in ('{', '['):
            start_idx = i
            break

    # No JSON found
    if start_idx == -1:
        return stdin_content

    # Non-JSON prefix found - sanitize and log
    if start_idx > 0:
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== Stdin Sanitization ({hook_name}) ===\n")
                f.write(f"Removed {start_idx} bytes of non-JSON prefix\n")
                f.write(f"Prefix content: {repr(stdin_content[:start_idx])}\n")
        except:
            pass
        return stdin_content[start_idx:]

    return stdin_content

# Use in main():
stdin_content = sys.stdin.read()
if not stdin_content or not stdin_content.strip():
    print(json.dumps({"hookSpecificOutput": {"status": "skipped"}}))
    sys.exit(0)

# NEW: Sanitize before parsing
stdin_content = sanitize_stdin(stdin_content, "UserPromptSubmit")
input_data = json.loads(stdin_content)
```

**Prevention**:
- Guard all shell profile output with `[[ -n "$PS1" ]]` check
- **Add stdin sanitization to all hook scripts** (implemented 2026-02-15)
- Log raw stdin in hook scripts for debugging
- Test hooks with: `echo '{}' | python3 hook_script.py`
- Test with polluted stdin: `echo 'GARBAGE{"key": "value"}' | python3 hook_script.py`
- Check `$CLAUDE_CODE_REMOTE` env var (set in Claude Code context)

**References**:
- Official docs: https://code.claude.com/docs/en/hooks#json-output
- Debug log location: `~/.claude/hook-debug.log`
- MEMORY.md: "Hook Errors (繰り返し発生)"

**Tags**: `hooks`, `json`, `shell-profile`, `stdin`, `parse-error`

**Severity**: Critical (blocks user interaction)

**Date Added**: 2026-02-15

---

### HOOK-003: stop.py Missing Empty Stdin Guard

**Error Signature**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```
(Occurs only in `stop.py`, not in other hooks)

**Context**: `stop.py` crashes when Claude Code invokes it with empty stdin, while `user-prompt-submit.py` and `post-tool-use.py` handle this gracefully.

**Root Cause**:
- `user-prompt-submit.py` and `post-tool-use.py` have empty stdin guards:
  ```python
  stdin_content = sys.stdin.read()
  if not stdin_content or not stdin_content.strip():
      # graceful skip
  ```
- **`stop.py` uses `json.load(sys.stdin)` directly without this guard**

**Solution**:
```python
# ❌ BEFORE (stop.py - vulnerable to empty stdin)
def main():
    try:
        input_data = json.load(sys.stdin)  # Crashes on empty stdin

# ✅ AFTER (stop.py - safe)
def main():
    try:
        stdin_content = sys.stdin.read()

        # Handle empty stdin gracefully
        if not stdin_content or not stdin_content.strip():
            print(json.dumps({}))
            sys.exit(0)

        # Sanitize stdin (HOOK-002)
        stdin_content = sanitize_stdin(stdin_content, "Stop")

        # Parse JSON
        input_data = json.loads(stdin_content)
```

**Prevention**:
- **Always use `sys.stdin.read()` + empty check pattern** (never `json.load(sys.stdin)` directly)
- Add integration tests with empty stdin: `echo '' | python3 hook_script.py`
- Code review checklist: "Does every hook have empty stdin guard?"

**References**:
- Discovered: 2026-02-15 team investigation (log-analyzer + script-debugger)
- Related: HOOK-002 (stdin pollution)

**Tags**: `hooks`, `stdin`, `error-handling`, `stop-hook`, `json`

**Severity**: High (causes hook failures in production)

**Date Added**: 2026-02-15

---

## Security Errors

### SEC-001: Secret Pattern Detection

**Error Signature**: `OpenAI API key detected in staged file: <filename>`

**Context**: Attempting to commit files containing API keys or secrets.

**Root Cause**: Secrets hardcoded in source files instead of using environment variables.

**Solution**:
```bash
# 1. Unstage the file immediately
git rm --cached <filename>

# 2. Add to .gitignore
echo "<filename>" >> .gitignore

# 3. Move secret to .env
echo "OPENAI_API_KEY=sk-..." >> .env

# 4. Load from environment in code
import os
api_key = os.getenv("OPENAI_API_KEY")
```

**Prevention**:
- Always use `.env` files for secrets
- Add `.env*` to `.gitignore`
- Run `make pre-git-check` before every commit
- Use secret scanning tools (e.g., git-secrets, trufflehog)

**Secret Patterns to Avoid**:
```python
# ❌ NEVER DO THIS
OPENAI_API_KEY = "sk-proj-..."
GEMINI_API_KEY = "AIzaSy..."
PASSWORD = "my_password"

# ✅ ALWAYS DO THIS
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

**References**:
- CLAUDE.md: "機密情報の取り扱い"
- OWASP: https://owasp.org/www-community/vulnerabilities/

**Tags**: `security`, `api-keys`, `secrets`, `environment`

**Severity**: Critical

**Date Added**: 2026-02-15

---

## API Errors

(To be populated as errors are encountered)

**Placeholder**: No entries yet. Add patterns for:
- API rate limiting
- Authentication failures
- Timeout errors
- Malformed requests

---

## Build Errors

(To be populated as errors are encountered)

**Placeholder**: No entries yet. Add patterns for:
- Dependency conflicts
- Build tool errors
- TypeScript compilation issues
- Python import errors

---

## ccusage Errors

### CCUSAGE-001: Wrong Package Name

**Error Signature**: `command not found: ccusage` after installing `@ccusage/codex`

**Context**: Occurs when installing the wrong npm package. `@ccusage/codex` is for Codex CLI (OpenAI), not Claude Code.

**Root Cause**: Two similarly named packages exist:
- `ccusage` — for **Claude Code** ✅
- `@ccusage/codex` — for **OpenAI Codex CLI** ❌

**Solution**:
```bash
# Uninstall wrong package
npm uninstall -g @ccusage/codex

# Install correct package
npm install -g ccusage

# Verify
ccusage --version
```

**Prevention**: Always use `ccusage` (not `@ccusage/codex`) for Claude Code analysis.

**Tags**: ccusage, npm, package, installation
**Severity**: Medium
**Date Added**: 2026-02-17

---

### CCUSAGE-002: Invalid Date Format

**Error Signature**: `Invalid date format` or unexpected empty output from `ccusage daily`

**Context**: ccusage requires dates in `YYYYMMDD` format without hyphens.

**Root Cause**: Using ISO 8601 format (`2026-02-01`) instead of ccusage format (`20260201`).

**Solution**:
```bash
# Wrong
ccusage daily --since 2026-02-01   # ❌

# Correct
ccusage daily --since 20260201     # ✅

# Today's date (dynamic)
ccusage daily --since "$(date +%Y%m%d)"   # ✅
```

**Prevention**: Always use `YYYYMMDD` format for ccusage date arguments.

**Tags**: ccusage, date, format
**Severity**: Low
**Date Added**: 2026-02-17

---

### CCUSAGE-003: jq Not Installed

**Error Signature**: `jq: command not found` when using `ccusage session --json | jq`

**Context**: ccusage's `--json` flag outputs raw JSON; jq is needed for filtering.

**Root Cause**: `jq` is not installed on the system.

**Solution**:
```bash
# Install jq
brew install jq          # macOS
apt-get install jq       # Linux

# Without jq (use --json alone)
ccusage session --json

# Or use built-in jq support
ccusage session --jq '.entries[] | select(.cost > 5)'
```

**Prevention**: Install jq as part of dev environment setup. Alternatively use ccusage's built-in `--jq` flag.

**Tags**: ccusage, jq, json, dependency
**Severity**: Low
**Date Added**: 2026-02-17

---

## Metadata

**Total Entries**: 9
**Categories**: 5
**Phase**: 1 (0-50 entries, flat structure)
**Next Review**: At 20 entries (consider adding indexes)
**Archive Strategy**: JSON index at 50+ entries, SQLite at 100+

**Maintenance Guidelines**:
1. Keep entries grep-friendly (plain text, clear error signatures)
2. Use consistent ID format: `CATEGORY-NNN`
3. Always include: Error Signature, Solution, Prevention, Tags
4. Update "Total Entries" count when adding new entries
5. Review and consolidate duplicate patterns monthly

**Search Performance Target**: `grep <pattern> PITFALLS.md` < 0.5 seconds

**Contribution**:
When adding a new entry:
1. Assign next available ID in category
2. Include all required fields
3. Add to Table of Contents
4. Update metadata
5. Test grep search works

---

## Version History

- 2026-02-17 (Update): Added ccusage Errors category (CCUSAGE-001, CCUSAGE-002, CCUSAGE-003). Total: 9 entries
- 2026-02-15 (Update): Added HOOK-002 stdin sanitization solution, HOOK-003 (stop.py empty stdin guard). Total: 6 entries
- 2026-02-15: Initial creation with 4 seed entries (GIT-001, GIT-002, HOOK-001, SEC-001)
