# Integration Tests - Claude Context Manager

## Overview

This document describes the integration tests for the Claude Context Manager, covering the complete flow from hook execution to Markdown generation.

## Test Structure

```
tests/
├── integration.test.ts    # Main integration test suite (10 test cases)
├── helpers/
│   └── test-utils.ts      # Test utility functions
├── README.md              # Python tests documentation
└── INTEGRATION_TESTS.md   # This file
```

## Test Cases

### End-to-End Tests (6 cases)

1. **Single session complete flow**
   - Tests: user-prompt → post-tool → stop → Markdown generation
   - Verifies: Complete workflow with temp file cleanup

2. **Multiple finalize executions with append**
   - Tests: Running finalize multiple times on same session
   - Verifies: Append behavior and token recalculation

3. **Same session ID with multiple restarts**
   - Tests: Session continuation across multiple Claude restarts
   - Verifies: Log aggregation from multiple runs

4. **Time gap detection**
   - Tests: Detection of time gaps > 5 minutes between entries
   - Verifies: Gap detection algorithm

5. **session-unknown processing**
   - Tests: Handling of unknown session IDs
   - Verifies: Fallback behavior for unknown sessions

6. **Japanese content complete flow**
   - Tests: Full flow with Japanese text
   - Verifies: UTF-8 encoding preservation

### Error Handling Tests (4 cases)

7. **Invalid JSON input**
   - Tests: Recovery from corrupted JSON files
   - Verifies: Error handling and recovery mechanism

8. **Finalize failure recovery**
   - Tests: Handling of filesystem errors during finalization
   - Verifies: Temp file preservation on failure

9. **Disk space simulation**
   - Tests: Handling of large content (1MB+)
   - Verifies: Large file processing capability

10. **Concurrent execution race conditions**
    - Tests: Multiple simultaneous writes to same log file
    - Verifies: Race condition detection (demonstrates need for locking)

## Running Tests

### All Tests

```bash
npm test
```

### Specific Test File

```bash
npm test tests/integration.test.ts
```

### With Coverage

```bash
npm test -- --coverage
```

### Watch Mode

```bash
npm test -- --watch
```

## Test Environment

Tests use a temporary directory structure:

```
.test-context-history/
├── .tmp/
│   └── session-*.json      # Temporary log files
└── sessions/
    └── YYYY-MM-DD/
        └── session-*.md    # Finalized Markdown files
```

This directory is created before each test and cleaned up afterward.

## Test Utilities

The `tests/helpers/test-utils.ts` file provides helper functions:

- `createTestSession()` - Create a test session with initial logs
- `addLogEntry()` - Add a log entry to a session
- `createUserEntry()` - Create a user log entry
- `createAssistantEntry()` - Create an assistant log entry
- `verifyMarkdownContent()` - Verify Markdown output
- `calculateTimeGaps()` - Calculate time gaps in logs
- `setupTestDirectories()` - Setup test directory structure
- `cleanupTestDirectories()` - Cleanup test directories
- `saveSessionMarkdown()` - Save Markdown to session directory
- `fileExists()` - Check if file exists

## Expected Behavior

### Success Criteria

All tests should pass with:
- Correct Markdown generation
- Accurate token counting
- Proper UTF-8 encoding
- Temp file cleanup after finalization
- Error recovery mechanisms

### Known Issues

**Test #10 (Concurrent execution):**
Currently demonstrates a race condition in the non-atomic read-modify-write pattern. This test intentionally shows the issue and will be fixed in Phase 2 with file locking or atomic operations.

## Continuous Integration

These tests should be run:
- Before every commit
- On pull requests
- In CI/CD pipeline

## Debugging

### Enable Verbose Output

```bash
npm test -- --verbose
```

### Run Single Test

```bash
npm test -- -t "Single session complete flow"
```

### Debug Mode

```bash
node --inspect-brk node_modules/.bin/jest --runInBand tests/integration.test.ts
```

## Future Improvements

- Add performance benchmarks
- Add stress tests (1000+ sessions)
- Add E2E tests with actual Claude Code hooks
- Add file locking mechanism to prevent race conditions
- Add test for Markdown diff detection (multiple finalize runs)
