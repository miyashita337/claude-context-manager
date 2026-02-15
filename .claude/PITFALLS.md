# PITFALLS.md

**Purpose**: A grep-friendly database of known error patterns, solutions, and prevention strategies encountered in Claude Context Manager development.

**Last Updated**: 2026-02-15

---

## Table of Contents

- [Git Errors](#git-errors)
- [Hook Errors](#hook-errors)
- [Security Errors](#security-errors)
- [API Errors](#api-errors)
- [Build Errors](#build-errors)

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

## Metadata

**Total Entries**: 4
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

- 2026-02-15: Initial creation with 4 seed entries (GIT-001, GIT-002, HOOK-001, SEC-001)
