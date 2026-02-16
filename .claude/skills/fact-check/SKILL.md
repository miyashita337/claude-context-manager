---
name: fact-check
description: Verify implementation details against official Claude Code documentation
tools: WebSearch, WebFetch, Read, Grep
model: sonnet
---

# Fact-Check Skill

**Purpose**: Verify that code implementations, configurations, and file paths align with official Claude Code documentation to prevent silent failures from using unofficial or deprecated patterns.

**When to Use**:
- Before implementing new features (verify approach)
- After encountering unexpected behavior (validate assumptions)
- When uncertain about configuration paths or formats
- During code review (validate against docs)

**Critical Use Cases**:
- Hook configuration paths (`.claude/settings.json` vs `.claude/hooks/hooks.json`)
- MCP server configuration format
- Skill directory structure and YAML frontmatter
- CLI command syntax and available flags

---

## Workflow

### Step 1: Understand the Question

Identify what needs to be verified:
- **Configuration path**: "Is `.claude/hooks/hooks.json` the official path?"
- **API usage**: "How do I configure a hook to run before commit?"
- **Feature availability**: "Does Claude Code support pre-commit hooks?"
- **Best practices**: "What's the recommended structure for Skills?"

**Example Questions**:
```
❓ "Verify that .claude/settings.json is the official hook configuration path"
❓ "Check if Claude Code supports multiple hooks for the same event"
❓ "Confirm the required YAML frontmatter fields for Skills"
```

---

### Step 2: Search Official Documentation

Use **WebSearch** to find relevant official documentation.

**Search Strategy**:
1. Start with official sources (docs.claude.com, github.com/anthropics)
2. Include year in query (2026 for latest docs)
3. Be specific (include version numbers if known)

**Search Queries**:
```
# For hook configuration
"Claude Code hooks configuration" site:docs.claude.com 2026

# For skill structure
"Claude Code skills YAML frontmatter" site:docs.claude.com

# For general features
"Claude Code MCP server" official documentation 2026
```

**Tools**: Use `WebSearch` with specific queries:
```python
WebSearch(query='Claude Code hooks settings.json site:docs.claude.com 2026')
```

**Expected Output**: List of relevant documentation URLs with snippets.

---

### Step 3: Fetch and Analyze Documentation

Use **WebFetch** to retrieve full documentation pages.

**Fetching Strategy**:
1. Prioritize official docs over blog posts or forums
2. Check publication/update date
3. Look for canonical examples

**Prompts for WebFetch**:
```
# For configuration verification
"Extract the official hook configuration file path and format. Include any warnings about deprecated paths."

# For feature verification
"List all supported hook types and their execution timing. Include required configuration fields."

# For structure verification
"Extract the required and optional fields for Skill YAML frontmatter. Include validation rules."
```

**Tools**: Use `WebFetch` with targeted prompts:
```python
WebFetch(
    url='https://docs.claude.com/claude-code/hooks',
    prompt='Extract the official hook configuration path and show example configuration'
)
```

---

### Step 4: Cross-Reference with Codebase

Use **Read** and **Grep** to check how the feature is currently implemented in the project.

**Verification Checklist**:
- [ ] Current implementation matches official docs
- [ ] File paths are correct
- [ ] Configuration format is valid
- [ ] No deprecated patterns in use

**Tools**:
```python
# Check current hook configuration
Read(file_path='.claude/settings.json')

# Find hook-related files
Grep(pattern='hooks', glob='**/*.json', output_mode='files_with_matches')

# Search for deprecated patterns
Grep(pattern='.claude/hooks/hooks.json', output_mode='content')
```

**Common Mismatches**:
- Using `.claude/hooks/hooks.json` instead of `.claude/settings.json`
- Missing required YAML frontmatter fields in Skills
- Incorrect MCP server configuration format
- Using deprecated CLI flags

---

### Step 5: Report Findings

Provide a clear, actionable report with:
1. **Verification Result**: ✅ Correct / ❌ Incorrect / ⚠️ Partially Correct
2. **Official Reference**: Direct quote + source URL
3. **Current Implementation**: What the codebase currently uses
4. **Required Changes**: Specific steps to align with docs (if needed)
5. **Impact Assessment**: What could break if not fixed

**Report Template**:
```markdown
## Fact-Check Report: [Topic]

### Verification Result
[✅ / ❌ / ⚠️] [One-line summary]

### Official Documentation
**Source**: [URL]
**Last Updated**: [Date if available]
**Quote**:
> [Direct quote from official docs]

### Current Implementation
**File**: [path]
**Current Usage**:
```[language]
[code snippet]
```

### Discrepancy
[Describe difference between docs and implementation]

### Required Changes
1. [Step 1]
2. [Step 2]
...

### Impact if Not Fixed
- [Consequence 1]
- [Consequence 2]

### Prevention
- [How to avoid this in the future]
```

---

## Examples

### Example 1: Verify Hook Configuration Path

**Question**: "Is `.claude/hooks/hooks.json` the official hook configuration path?"

**Step 1 - WebSearch**:
```
Query: "Claude Code hooks configuration path" site:docs.claude.com 2026
```

**Step 2 - WebFetch**:
```
URL: https://docs.claude.com/claude-code/hooks
Prompt: "What is the official file path for hook configuration? Include any mentions of alternative or deprecated paths."
```

**Step 3 - Read Current Config**:
```python
Read('.claude/settings.json')
Read('.claude/hooks/hooks.json')  # Check if deprecated path exists
```

**Step 4 - Report**:
```markdown
## Fact-Check Report: Hook Configuration Path

### Verification Result
❌ **INCORRECT** - Using non-official path

### Official Documentation
**Source**: https://docs.claude.com/claude-code/hooks
**Quote**:
> "Hooks are configured in the `.claude/settings.json` file under the `hooks` key."

### Current Implementation
**File**: `.claude/hooks/hooks.json`
**Status**: Non-official path, hooks will not execute

### Discrepancy
Project uses `.claude/hooks/hooks.json`, but official path is `.claude/settings.json` with `"hooks"` section.

### Required Changes
1. Migrate configuration to `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "user-prompt-submit": "python src/hooks/user-prompt-submit.py",
       ...
     }
   }
   ```
2. Delete `.claude/hooks/hooks.json`
3. Verify with `make startup-check`

### Impact if Not Fixed
- **Critical**: Hooks will not execute (silent failure)
- **Testing**: Tests may pass but hooks fail in production

### Prevention
- Add path validation in tests
- Use `/fact-check` before implementing new features
- Document official paths in PITFALLS.md
```

---

### Example 2: Verify Skill YAML Frontmatter

**Question**: "What are the required YAML frontmatter fields for Claude Code Skills?"

**Step 1 - WebSearch**:
```
Query: "Claude Code skills YAML frontmatter required fields" 2026
```

**Step 2 - WebFetch**:
```
URL: https://docs.claude.com/claude-code/skills
Prompt: "List all required and optional YAML frontmatter fields for Skills. Include validation rules and examples."
```

**Step 3 - Grep Current Skills**:
```python
Grep(pattern='---', glob='.claude/skills/**/SKILL.md', output_mode='content', -A=5)
```

**Step 4 - Report**:
```markdown
## Fact-Check Report: Skill YAML Frontmatter

### Verification Result
✅ **CORRECT** - All required fields present

### Official Documentation
**Source**: https://docs.claude.com/claude-code/skills
**Required Fields**:
- `name`: Skill name (kebab-case)
- `description`: One-line description

**Optional Fields**:
- `tools`: Comma-separated list of allowed tools
- `model`: Preferred model (sonnet/opus/haiku)

### Current Implementation
**Files**: `.claude/skills/*/SKILL.md`
**Status**: All skills have required fields

### Prevention
- Add YAML frontmatter validation in tests
- Use this skill to verify before creating new skills
```

---

## Anti-Patterns

### ❌ Don't: Trust ChatGPT/Gemini Without Verification

```markdown
**Wrong Approach**:
User: "How do I configure Claude Code hooks?"
You: [Ask ChatGPT for answer] → [Use answer without verification]
```

**Problem**: AI models may provide outdated or incorrect information.

**Correct Approach**:
1. Ask ChatGPT/Gemini for guidance
2. **Use `/fact-check`** to verify against official docs
3. Cross-reference with codebase
4. Report discrepancies

---

### ❌ Don't: Assume Documentation is Complete

```markdown
**Wrong Approach**:
Docs say: "Configure hooks in .claude/settings.json"
You: [Implement exactly as stated] → [Don't test edge cases]
```

**Problem**: Documentation may not cover all scenarios.

**Correct Approach**:
1. Verify primary use case in docs
2. Check for warnings, limitations, or known issues
3. **Test in actual environment** (not just read docs)
4. Document findings in PITFALLS.md

---

### ❌ Don't: Skip Verification for "Simple" Changes

```markdown
**Wrong Approach**:
"This is just a config file path, no need to verify"
→ Uses `.claude/hooks/hooks.json`
→ Hooks silently fail
```

**Problem**: Simple changes can have critical impact.

**Correct Approach**:
- **Always verify** paths, formats, and syntax against official docs
- Especially for configuration files (silent failures are worst)
- Add integration tests that actually execute the feature

---

## Best Practices

### 1. Verify Before Implement

```markdown
**Workflow**:
1. User requests feature
2. **Run `/fact-check`** to verify official approach
3. Implement based on verified docs
4. Test in real environment
5. Document findings (if any discrepancies)
```

---

### 2. Update PITFALLS.md When Discrepancies Found

```markdown
**After finding a discrepancy**:
1. Complete the fact-check report
2. Add entry to `.claude/PITFALLS.md`:
   - Error ID (e.g., HOOK-002)
   - Error Signature
   - Official solution
   - Prevention strategy
3. Update tests to catch the issue
```

---

### 3. Cite Sources in Reports

```markdown
**Always include**:
- Direct URL to official docs
- Publication/update date (if available)
- Direct quote (not paraphrased)
- Version number (if applicable)
```

---

## Limitations

### 1. Documentation May Be Outdated

- Always check publication date
- Cross-reference multiple sources if unclear
- Test in actual environment (don't just trust docs)

### 2. Edge Cases May Not Be Documented

- Official docs cover common scenarios
- Unusual configurations may not be mentioned
- Use judgment and test thoroughly

### 3. WebSearch is US-Only

- If WebSearch fails, try WebFetch directly with known documentation URLs
- Fallback: Use `/research --model gemini --grounding` for international access

---

## Performance Optimization

### Fast Path (< 1 minute)

For simple verifications (path, format):
1. **Direct WebFetch** to known docs URL
2. **Grep** for specific pattern in docs
3. Quick comparison with codebase

### Standard Path (1-3 minutes)

For thorough verification:
1. **WebSearch** for official docs
2. **WebFetch** top 2-3 results
3. **Read/Grep** codebase
4. Full report

### Deep Dive (3-5 minutes)

For critical features or complex verification:
1. **WebSearch** official docs + community discussions
2. **WebFetch** multiple sources
3. **Cross-reference** with GitHub issues, changelog
4. **Read/Grep** entire codebase
5. **Test in real environment**
6. Comprehensive report + PITFALLS.md entry

---

## Maintenance

### Keep Documentation Links Updated

Periodically review and update:
- Official documentation URLs
- API endpoint URLs
- Version numbers in search queries

### Track Common Discrepancies

If the same discrepancy is found multiple times:
- Update PITFALLS.md with permanent entry
- Consider adding automated validation
- Update tests to prevent regression

---

## Related Resources

- `.claude/PITFALLS.md` - Known error patterns and solutions
- `.claude/CLAUDE.md` - Project-specific guidelines
- Official docs: https://docs.claude.com/claude-code/
- GitHub repository: https://github.com/anthropics/claude-code

---

## Version History

- 2026-02-15: Initial creation for P0 error prevention strategy
