# Git Errors Reference

**Extracted from**: `.claude/PITFALLS.md`
**Purpose**: Quick reference for git-related errors in the git-workflow skill
**Last Updated**: 2026-02-15

---

## GIT-001: Initial Commit HEAD Error

**Error Signature**: `fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree`

**Context**: Occurs when trying to unstage files in a new repository with no commits yet.

**Root Cause**: `HEAD` doesn't exist until the first commit is created.

**Solution**:
```bash
# ❌ WRONG (before first commit)
git reset HEAD <file>

# ✅ CORRECT (before first commit)
git rm --cached <file>

# ✅ UNIVERSAL (Git 2.23+)
git restore --staged <file>
```

**Prevention**:
```bash
# Check if HEAD exists before using git reset
git rev-parse HEAD >/dev/null 2>&1 && git reset HEAD <file> || git rm --cached <file>
```

**References**:
- CLAUDE.md: "初回コミット時の注意"
- Git docs: https://git-scm.com/docs/git-rm
- Full entry: PITFALLS.md#GIT-001

**Tags**: `git`, `initial-commit`, `staging`, `HEAD`

**Severity**: Medium

---

## GIT-002: Non-Official Hook Path

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
- Full entry: PITFALLS.md#GIT-002

**Tags**: `hooks`, `configuration`, `path`, `settings`

**Severity**: High

---

**Note**: This is a subset of PITFALLS.md. For complete error database, see `.claude/PITFALLS.md`.
