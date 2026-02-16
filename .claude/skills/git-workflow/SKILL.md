---
name: git-workflow
description: Guide safe git operations with automatic error prevention and recovery
tools: Bash, Read, Grep
model: sonnet
---

# Git Workflow Skill

**Purpose**: Provide a safe, guided workflow for git operations with automatic error prevention, particularly for edge cases like initial commits, force pushes, and staging operations.

**When to Use**:
- Before ANY git commit (especially first commit)
- Before git push (especially to main/master)
- When making commits in a new repository
- When encountering git errors
- As part of CI/CD pipeline

**Key Features**:
- Initial commit detection and HEAD error prevention
- Secret detection before commit
- Force push protection
- Guided commit message creation
- Automatic PITFALLS.md error resolution

---

## Workflow

### Step 1: Pre-Flight Safety Check

Run comprehensive safety checks before any git operation.

**Safety Checklist**:
```bash
# 1. Run pre-git-check
make pre-git-check

# 2. Check git status
git status

# 3. Check for HEAD existence (initial commit detection)
git rev-parse HEAD >/dev/null 2>&1
```

**Tools**:
```python
# Run safety checks
Bash(command='make pre-git-check', description='Run pre-commit safety checks')

# Get git status
Bash(command='git status', description='Check working tree status')

# Detect initial commit scenario
Bash(command='git rev-parse HEAD >/dev/null 2>&1 && echo "HAS_HEAD" || echo "NO_HEAD"',
     description='Check if HEAD exists')
```

**Outcomes**:
- ✅ **All Clear**: Proceed to Step 2
- ❌ **Errors Detected**: Use `/pre-commit` skill to resolve
- ⚠️ **Initial Commit**: Enable special handling for HEAD errors

---

### Step 2: Validate Staging Area

Check what's about to be committed and validate safety.

**Validation Steps**:
1. **List staged files**: `git diff --cached --name-only`
2. **Check file count**: Warn if > 10 files
3. **Check for sensitive files**: `.env`, `credentials.json`, etc.
4. **Check for binary files**: Large files (>1MB)

**Tools**:
```python
# List staged files
Bash(command='git diff --cached --name-only', description='List staged files')

# Check for secrets in staged files
Bash(command='git diff --cached | grep -i "api_key\\|password\\|secret"',
     description='Scan staged changes for secrets')
```

**Decision Points**:
- ✅ **Safe to proceed**: < 10 files, no secrets, no large binaries
- ⚠️ **Warning**: 10-20 files → Confirm with user
- ❌ **Block**: Secrets detected → Run `/pre-commit` to fix

---

### Step 3: Handle Initial Commit Edge Case

Special handling for repositories with no commits yet.

**Detection**:
```bash
git rev-parse HEAD >/dev/null 2>&1
# Exit code 0: Has commits (HEAD exists)
# Exit code 128: No commits (HEAD doesn't exist)
```

**Impact**:
When HEAD doesn't exist:
- ❌ **FAILS**: `git reset HEAD <file>`
- ❌ **FAILS**: `git diff HEAD`
- ✅ **WORKS**: `git rm --cached <file>`
- ✅ **WORKS**: `git diff --cached`

**Safe Commands for Initial Commit**:
```bash
# ❌ WRONG (before first commit)
git reset HEAD file.txt

# ✅ CORRECT (before first commit)
git rm --cached file.txt

# ℹ️  UNIVERSAL (works before and after first commit)
git restore --staged file.txt  # Git 2.23+
```

**Automated Handling**:
```python
# Check HEAD existence
has_head = Bash(command='git rev-parse HEAD >/dev/null 2>&1 && echo "yes" || echo "no"')

if "no" in has_head.stdout:
    # Use initial-commit-safe commands
    unstage_cmd = 'git rm --cached'
    diff_cmd = 'git diff --cached'
else:
    # Use standard commands
    unstage_cmd = 'git reset HEAD'
    diff_cmd = 'git diff HEAD'
```

**Tools**:
```python
Bash(command=f'{unstage_cmd} <file>', description='Unstage file (initial-commit-safe)')
```

---

### Step 4: Create Commit Message

Guide user through creating a proper commit message.

**Commit Message Guidelines** (from git log analysis):
```bash
# Analyze recent commit style
git log --oneline -10
```

**Standard Format**:
```
<type>: <subject>

<body (optional)>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Commit Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation changes
- `test`: Test changes
- `chore`: Build/tooling changes

**Automated Message Generation**:
```python
# Get staged changes summary
diff = Bash(command='git diff --cached --stat', description='Get staged changes summary')

# Analyze changes
if "test" in diff.stdout:
    suggested_type = "test"
elif "README" in diff.stdout or ".md" in diff.stdout:
    suggested_type = "docs"
else:
    suggested_type = "feat"  # User should confirm

# Generate message
suggested_message = f"{suggested_type}: [user fills in subject]\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Tools**:
```python
# Show diff for context
Bash(command='git diff --cached', description='Show staged changes')

# Get commit style
Bash(command='git log --oneline -10', description='Show recent commit messages')
```

---

### Step 5: Execute Commit

Safely execute the commit with proper error handling.

**Commit Command**:
```bash
git commit -m "$(cat <<'EOF'
<commit message here>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Why HEREDOC?**:
- Handles multi-line messages correctly
- Prevents shell escaping issues
- Ensures proper formatting

**Error Handling**:
```python
result = Bash(command='git commit -m "..."', description='Create commit')

if result.returncode != 0:
    # Check for common errors
    if "fatal: ambiguous argument 'HEAD'" in result.stderr:
        # This shouldn't happen if Step 3 was done correctly
        return "❌ HEAD error - see PITFALLS.md GIT-001"
    elif "nothing to commit" in result.stdout:
        return "ℹ️  No changes staged for commit"
    elif "pre-commit hook failed" in result.stderr:
        # Hook failure - need to fix and re-commit
        return "⚠️  Pre-commit hook failed - see error above"
    else:
        # Unknown error
        return f"❌ Commit failed: {result.stderr}"
```

**Tools**:
```python
Bash(
    command='git commit -m "$(cat <<\'EOF\'\n' + commit_message + '\nEOF\n)"',
    description='Create git commit'
)
```

---

### Step 6: Post-Commit Validation

Verify commit was created successfully.

**Validation Steps**:
```bash
# 1. Check commit was created
git log -1 --oneline

# 2. Verify staged area is clean
git status

# 3. Check commit hash
git rev-parse HEAD
```

**Tools**:
```python
# Verify commit
Bash(command='git log -1 --oneline', description='Show latest commit')

# Clean status check
Bash(command='git status', description='Verify clean working tree')
```

**Outcomes**:
- ✅ **Success**: Commit created, staging area clean
- ❌ **Failure**: Commit not created, investigate error

---

### Step 7: Push Workflow (Optional)

If user wants to push, validate safety first.

**Push Safety Checks**:
1. **Branch check**: Are we on main/master?
2. **Force push check**: Is `--force` being used?
3. **Remote check**: Does remote branch exist?
4. **Diff check**: What's being pushed?

**Critical Protection**:
```bash
# ❌ NEVER ALLOW (without explicit user confirmation)
git push --force origin main
git push --force origin master

# ⚠️  WARN
git push origin main  # If pushing to main

# ✅ SAFE
git push origin feature-branch
```

**Automated Safety**:
```python
# Get current branch
branch = Bash(command='git branch --show-current')

# Check if pushing to main/master
if branch.stdout.strip() in ['main', 'master']:
    if '--force' in push_command:
        return "❌ BLOCKED: Force push to main/master not allowed. See CLAUDE.md Git Safety Protocol."
    else:
        return "⚠️  WARNING: Pushing to main/master. Confirm: (y/N)"

# Get commits to be pushed
commits = Bash(command='git log origin/$(git branch --show-current)..HEAD --oneline')

# Show what will be pushed
return f"About to push {len(commits.stdout.splitlines())} commits:\n{commits.stdout}"
```

**Tools**:
```python
# Show branch
Bash(command='git branch --show-current', description='Get current branch')

# Show commits to push
Bash(command='git log origin/HEAD..HEAD --oneline', description='List commits to push')

# Execute push
Bash(command='git push -u origin $(git branch --show-current)',
     description='Push to remote')
```

---

## Common Git Operations

### Operation 1: Stage Specific Files

```python
# ✅ RECOMMENDED: Stage specific files
Bash(command='git add file1.py file2.py', description='Stage specific files')

# ⚠️  USE WITH CAUTION: Stage all changes
# (Can accidentally include secrets, .env files, etc.)
Bash(command='git add .', description='Stage all changes')
```

---

### Operation 2: Unstage Files (Initial-Commit-Safe)

```python
# Detect if HEAD exists
has_head = Bash(command='git rev-parse HEAD >/dev/null 2>&1 && echo "yes" || echo "no"')

if "no" in has_head.stdout:
    # Initial commit - use git rm --cached
    Bash(command='git rm --cached file.txt', description='Unstage file (initial commit)')
else:
    # Has commits - use git reset HEAD
    Bash(command='git reset HEAD file.txt', description='Unstage file')

# Or use universal command (Git 2.23+)
Bash(command='git restore --staged file.txt', description='Unstage file (universal)')
```

---

### Operation 3: Amend Last Commit

```python
# ⚠️  WARNING: Only if commit hasn't been pushed

# Check if last commit is pushed
result = Bash(command='git branch -r --contains HEAD')

if result.stdout.strip():
    return "⚠️  Last commit already pushed. Amending will rewrite history."
else:
    Bash(command='git commit --amend --no-edit', description='Amend last commit')
```

---

### Operation 4: Create Branch

```python
# Create and switch to new branch
Bash(command='git checkout -b feature/new-feature', description='Create new branch')

# Or (Git 2.23+)
Bash(command='git switch -c feature/new-feature', description='Create new branch')
```

---

### Operation 5: Stash Changes

```python
# Stash uncommitted changes
Bash(command='git stash push -m "Description of changes"',
     description='Stash uncommitted changes')

# List stashes
Bash(command='git stash list', description='List stashes')

# Apply stash
Bash(command='git stash pop', description='Apply and remove latest stash')
```

---

## Error Recovery Patterns

### Error 1: Accidentally Committed Secret

```markdown
**Scenario**: Committed file with API key

**CRITICAL**: Secret is now in git history, even if you unstage/delete

**Recovery**:
1. ❌ **DON'T**: `git reset HEAD~1` (secret still in history)
2. ✅ **DO**:
   ```bash
   # If commit hasn't been pushed
   git reset --hard HEAD~1
   git rm --cached file-with-secret.py
   echo "file-with-secret.py" >> .gitignore
   # Move secret to .env
   # Re-commit without secret

   # If commit HAS been pushed
   # → ROTATE THE SECRET IMMEDIATELY
   # → Contact security team
   # → Consider using git-filter-repo to rewrite history
   ```
```

---

### Error 2: Committed to Wrong Branch

```markdown
**Scenario**: Made commit on main instead of feature branch

**Recovery**:
```bash
# Create branch from current position
git branch feature/correct-branch

# Reset main to before commit
git reset --hard origin/main

# Switch to correct branch
git switch feature/correct-branch
```
```

---

### Error 3: Merge Conflict

```markdown
**Recovery**:
```bash
# Check conflicted files
git status

# Manually resolve conflicts in files
# (Edit files, remove conflict markers)

# Stage resolved files
git add <resolved-files>

# Complete merge
git commit
```

**NEVER**: `git reset --hard` during merge (loses all changes)
```

---

### Error 4: Pushed to Wrong Remote

```markdown
**Recovery**:
```bash
# If push just happened and NO ONE pulled yet
git push --force-with-lease origin :branch-name  # Delete remote branch

# If others have pulled
# → Cannot safely undo
# → Create revert commit instead
git revert HEAD
git push origin branch-name
```
```

---

## Best Practices

### 1. Always Run Pre-Checks

```bash
# Before every commit
make pre-git-check

# Or use this skill
/git-workflow
```

---

### 2. Prefer Specific File Staging

```bash
# ✅ GOOD
git add src/feature.py tests/test_feature.py

# ⚠️  RISKY
git add .
```

---

### 3. Never Force Push to main/master

```bash
# ❌ NEVER
git push --force origin main

# ✅ Alternative
# Create new branch, open PR, merge properly
```

---

### 4. Write Meaningful Commit Messages

```bash
# ❌ BAD
git commit -m "fix"
git commit -m "update"

# ✅ GOOD
git commit -m "fix: resolve initial commit HEAD error in pre-commit hook"
git commit -m "feat: add PITFALLS.md error pattern database"
```

---

### 5. Test Before Commit

```bash
# Run tests
make test-all

# If tests pass → commit
# If tests fail → fix first
```

---

## Anti-Patterns

### ❌ Don't: Commit Without Checking Staged Files

```markdown
**Wrong**:
git add .
git commit -m "changes"  # What changes? Could include secrets!

**Correct**:
git add <specific files>
git diff --cached  # Review what's staged
git status  # Double check
git commit -m "feat: specific change description"
```

---

### ❌ Don't: Use git add -A Without Checking

```markdown
**Wrong**:
git add -A  # Adds everything including .env, .DS_Store, etc.

**Correct**:
make pre-git-check  # Will catch unwanted files
git add <specific files>
```

---

### ❌ Don't: Skip Pre-Commit Checks

```markdown
**Wrong**:
git commit --no-verify  # Skips hooks, bypasses safety checks

**Correct**:
# Let hooks run, fix any errors they catch
git commit
```

---

## Integration with Other Skills

### Use `/pre-commit` for Error Resolution

```markdown
When `/git-workflow` detects errors:
1. Report error to user
2. Suggest: "Run `/pre-commit` to automatically resolve"
3. After resolution, continue workflow
```

---

### Use `/fact-check` for Git Command Verification

```markdown
When uncertain about git command syntax:
1. Use `/fact-check` to verify against official docs
2. Apply verified command
3. Document in PITFALLS.md if edge case
```

---

## Reference Files

- `.claude/PITFALLS.md` - Error patterns (GIT-001, GIT-002)
- `.claude/CLAUDE.md` - Git操作ガイドライン
- `scripts/pre-git-check.sh` - Pre-commit validation script
- `.gitignore` - Ignored file patterns

---

## Quick Reference Card

```bash
# Pre-flight check
make pre-git-check

# Stage files
git add <file1> <file2>

# Check staged
git diff --cached

# Commit (initial-commit-safe)
git commit -m "type: subject"

# Push (with safety check)
git push -u origin $(git branch --show-current)

# Unstage (initial-commit-safe)
git restore --staged <file>

# Emergency: Undo last commit (NOT pushed)
git reset --soft HEAD~1
```

---

## Version History

- 2026-02-15: Initial creation with initial commit handling and safety checks
