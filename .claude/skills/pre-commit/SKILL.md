---
name: pre-commit
description: Run pre-commit checks and resolve errors using PITFALLS.md
tools: Bash, Read, Grep
model: sonnet
---

# Pre-Commit Skill

**Purpose**: Automate pre-commit safety checks and automatically resolve common errors using the PITFALLS.md knowledge base.

**When to Use**:
- Before `git commit` (always)
- After making changes to hook configuration
- When adding new files to staging area
- As part of CI/CD pipeline validation

**Core Functionality**:
1. Run `make pre-git-check` (safety validation)
2. If errors occur, search PITFALLS.md for solutions
3. Apply solutions automatically (when safe)
4. Report status to user

---

## Workflow

### Step 1: Run Pre-Commit Checks

Execute the project's pre-commit validation script.

**Command**:
```bash
make pre-git-check
```

**What It Checks**:
- `.gitignore` completeness
- Secret pattern detection (API keys, passwords)
- Unwanted file detection (`__pycache__`, `*.backup`, etc.)
- Hook configuration validity
- File size limits

**Expected Outcomes**:
- ✅ **Success** (exit code 0): All checks passed
- ❌ **Failure** (exit code 1): Errors detected

**Tools**:
```python
Bash(
    command='make pre-git-check',
    description='Run pre-commit safety checks'
)
```

---

### Step 2: Parse Check Results

Analyze the output to identify specific errors.

**Error Categories**:
1. **Security Errors**: API keys, secrets in staged files
2. **Git Errors**: Staging issues, HEAD errors
3. **Build Errors**: Missing dependencies, syntax errors
4. **Validation Errors**: Invalid configuration, missing files

**Parsing Strategy**:
```python
# Capture output
result = Bash(command='make pre-git-check', ...)

# Check exit code
if result.returncode == 0:
    # Success - proceed to commit
    return "✅ All pre-commit checks passed"
else:
    # Errors detected - extract error messages
    errors = parse_errors(result.stdout + result.stderr)
```

**Common Error Patterns**:
```bash
# Security
"OpenAI API key detected in staged file: config.py"
"Secret pattern found: GEMINI_API_KEY"

# Git
"fatal: ambiguous argument 'HEAD'"
"Hook not executing despite proper configuration"

# Validation
".gitignore incomplete: missing __pycache__"
"Unwanted file detected: .DS_Store"
```

---

### Step 3: Search PITFALLS.md for Solutions

Use **Grep** to search the error pattern database.

**Search Strategy**:
1. Extract key error signature (e.g., "fatal: ambiguous argument 'HEAD'")
2. Search PITFALLS.md for matching error signature
3. Retrieve error ID, solution, and prevention steps

**Tools**:
```python
# Search by error signature
Grep(
    pattern='fatal: ambiguous argument',
    path='.claude/PITFALLS.md',
    output_mode='content',
    -B=5,  # Include error ID
    -A=20  # Include solution
)

# Search by error ID (if known)
Grep(
    pattern='GIT-001',
    path='.claude/PITFALLS.md',
    output_mode='content',
    -A=30
)

# Search by category
Grep(
    pattern='## Security Errors',
    path='.claude/PITFALLS.md',
    output_mode='content',
    -A=100
)
```

**Fallback**: If no match in PITFALLS.md:
1. Use `/fact-check` to verify against official docs
2. Report to user for manual resolution
3. **Add new entry to PITFALLS.md** after resolution

---

### Step 4: Apply Automated Fixes

For known errors with safe automated solutions, apply the fix.

**Automated Fix Criteria**:
- ✅ Solution is in PITFALLS.md
- ✅ Solution is reversible (or user confirms)
- ✅ Solution has no side effects
- ✅ Solution is tested

**Safe Automated Fixes**:

#### Fix 1: Remove Staged Secret Files
```python
# For: SEC-001 (OpenAI API key detected)
Bash(command='git rm --cached config.py', description='Unstage file with secrets')
Bash(command='echo "config.py" >> .gitignore', description='Add to .gitignore')
# Report: "⚠️  File 'config.py' unstaged and added to .gitignore. Move secrets to .env file."
```

#### Fix 2: Initial Commit HEAD Error
```python
# For: GIT-001 (fatal: ambiguous argument 'HEAD')
# Already handled by make pre-git-check logic, just inform user
# Report: "ℹ️  Initial commit detected. Using 'git rm --cached' instead of 'git reset HEAD'."
```

#### Fix 3: Add Missing .gitignore Entries
```python
# For: Validation error (missing .gitignore entries)
Bash(command='echo "__pycache__/" >> .gitignore', description='Add __pycache__ to .gitignore')
Bash(command='echo "*.pyc" >> .gitignore', description='Add *.pyc to .gitignore')
# Report: "✅ Updated .gitignore with missing entries"
```

**Manual Fixes** (require user confirmation):
- Deleting files
- Modifying source code
- Changing configuration files

---

### Step 5: Re-Run Checks

After applying fixes, re-run pre-commit checks to verify.

**Re-Check Command**:
```bash
make pre-git-check
```

**Outcomes**:
- ✅ **Success**: Report "All checks passed, ready to commit"
- ❌ **Still Failing**: Report remaining errors + manual steps required
- 🔄 **Loop Detection**: If same error occurs 3+ times, stop and request user intervention

**Tools**:
```python
# Re-run checks
retry_result = Bash(command='make pre-git-check', ...)

if retry_result.returncode == 0:
    return "✅ All pre-commit checks passed after fixes. Ready to commit."
else:
    return "⚠️  Some errors remain. Manual intervention required:\n" + retry_result.stderr
```

---

### Step 6: Report Results

Provide a comprehensive report with:
1. **Check Status**: ✅ Passed / ⚠️ Warnings / ❌ Failed
2. **Errors Found**: List of all detected issues
3. **Automated Fixes Applied**: What was automatically resolved
4. **Manual Steps Required**: What user must do (if any)
5. **Next Steps**: How to proceed (commit, fix, etc.)

**Report Template**:
```markdown
## Pre-Commit Check Report

### Status
[✅ / ⚠️ / ❌] [One-line summary]

### Checks Performed
- [x] .gitignore completeness
- [x] Secret pattern detection
- [x] Unwanted file detection
- [x] Hook configuration validity

### Errors Found
1. **[Error ID]**: [Error message]
   - **Category**: [Security/Git/Validation]
   - **Severity**: [Critical/High/Medium/Low]

### Automated Fixes Applied
1. ✅ [Fix description]
2. ✅ [Fix description]

### Manual Steps Required
1. [ ] [Step 1]
2. [ ] [Step 2]

### Next Steps
[Instructions for user]

### Reference
- PITFALLS.md entries: [GIT-001, SEC-001, ...]
- Related docs: [.claude/CLAUDE.md section]
```

---

## Examples

### Example 1: Secret Detection & Auto-Fix

**Initial Check**:
```bash
$ make pre-git-check
❌ ERROR: OpenAI API key detected in staged file: src/config.py
```

**Step 1 - Search PITFALLS.md**:
```python
Grep(pattern='OpenAI API key detected', path='.claude/PITFALLS.md', output_mode='content', -B=5, -A=20)
```

**Step 2 - Extract Solution** (from SEC-001):
```markdown
**Solution**:
1. git rm --cached <filename>
2. Add to .gitignore
3. Move secret to .env
```

**Step 3 - Apply Automated Fix**:
```python
Bash(command='git rm --cached src/config.py')
Bash(command='echo "src/config.py" >> .gitignore')
```

**Step 4 - Report**:
```markdown
## Pre-Commit Check Report

### Status
⚠️  **WARNING** - Secret detected and removed from staging

### Errors Found
1. **SEC-001**: OpenAI API key detected in staged file: src/config.py
   - **Category**: Security
   - **Severity**: Critical

### Automated Fixes Applied
1. ✅ Unstaged src/config.py
2. ✅ Added src/config.py to .gitignore

### Manual Steps Required
1. [ ] Move API key to .env file:
   ```bash
   echo "OPENAI_API_KEY=sk-..." >> .env
   ```
2. [ ] Update src/config.py to load from environment:
   ```python
   import os
   OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
   ```
3. [ ] Re-stage other changes (if any):
   ```bash
   git add <files>
   ```

### Next Steps
Complete manual steps above, then re-run `/pre-commit` or `make pre-git-check`.

### Reference
- PITFALLS.md: SEC-001
- CLAUDE.md: "機密情報の取り扱い"
```

---

### Example 2: All Checks Passed

**Check Result**:
```bash
$ make pre-git-check
✅ All pre-commit checks passed
```

**Report**:
```markdown
## Pre-Commit Check Report

### Status
✅ **PASSED** - All checks passed, ready to commit

### Checks Performed
- [x] .gitignore completeness
- [x] Secret pattern detection (0 secrets found)
- [x] Unwanted file detection (0 unwanted files)
- [x] Hook configuration validity

### Errors Found
None

### Next Steps
Safe to proceed with commit:
```bash
git commit -m "Your commit message"
```

Or use the `/git-workflow` skill for guided commit process.
```

---

## Error Resolution Strategies

### Strategy 1: Direct Match in PITFALLS.md

```markdown
**When**: Error signature exactly matches a PITFALLS.md entry

**Action**:
1. Grep for error signature
2. Extract error ID and solution
3. Apply solution (if safe)
4. Report with PITFALLS.md reference
```

---

### Strategy 2: Partial Match / Similar Error

```markdown
**When**: Error is similar but not exact match

**Action**:
1. Grep for keywords from error message
2. Review related entries (same category)
3. Use judgment to adapt solution
4. Report with caveat: "Similar to [Error ID], adapted solution"
5. **Add new entry to PITFALLS.md** if solution works
```

---

### Strategy 3: No Match in PITFALLS.md

```markdown
**When**: Error is not in PITFALLS.md

**Action**:
1. Use `/fact-check` to search official docs
2. If still no solution, report to user for manual resolution
3. **After user resolves**: Add entry to PITFALLS.md:
   - Assign next error ID
   - Document error signature
   - Document solution
   - Document prevention
   - Update metadata (total entries)
```

---

## Best Practices

### 1. Always Run Before Commit

```bash
# Add to .git/hooks/pre-commit (optional automation)
#!/bin/bash
make pre-git-check || exit 1
```

---

### 2. Batch Fixes When Safe

```markdown
**If multiple safe fixes needed**:
- Apply all automated fixes at once
- Re-run check once
- Report all fixes in single report
```

---

### 3. Prioritize Critical Errors

```markdown
**Processing Order**:
1. **Critical** (Security): Fix immediately, block commit
2. **High** (Git errors): Fix before commit
3. **Medium** (Validation): Warn, allow commit with confirmation
4. **Low** (Warnings): Report only
```

---

### 4. Update PITFALLS.md Proactively

```markdown
**After resolving new error**:
1. Verify solution works
2. Add to PITFALLS.md immediately
3. Update tests to catch this error
4. Increment metadata count
```

---

## Anti-Patterns

### ❌ Don't: Auto-Fix Without User Awareness

```markdown
**Wrong**:
[Detect secret] → [Auto unstage] → [Don't tell user] → [Commit continues]

**Correct**:
[Detect secret] → [Auto unstage] → [Report clearly] → [Block commit until user confirms fix]
```

---

### ❌ Don't: Ignore Warnings

```markdown
**Wrong**:
[Warning: .DS_Store detected] → [Ignore] → [Commit with .DS_Store]

**Correct**:
[Warning: .DS_Store detected] → [Auto-fix: add to .gitignore] → [Report fix] → [Clean commit]
```

---

### ❌ Don't: Get Stuck in Error Loops

```markdown
**Wrong**:
[Error] → [Fix] → [Same error] → [Same fix] → [Loop forever]

**Correct**:
[Error] → [Fix attempt 1] → [Same error] → [Fix attempt 2] → [Same error] → [STOP, report to user]

**Rule**: Max 3 fix attempts, then require user intervention
```

---

## Related Resources

- `.claude/PITFALLS.md` - Error pattern database
- `scripts/pre-git-check.sh` - Pre-commit check script
- `Makefile` - Command shortcuts
- `.claude/CLAUDE.md` - Git operation guidelines

---

## Version History

- 2026-02-15: Initial creation for automated error resolution
