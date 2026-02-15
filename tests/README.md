# Tests for Claude Context Manager

This directory contains test suites for the Claude Context Manager Python hooks.

## Setup

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_hooks.py
```

Run specific test case:
```bash
pytest tests/test_hooks.py::test_session_logger_file_creation_and_loading
```

Run with coverage report:
```bash
pytest --cov=src/hooks --cov-report=html
```

## Test Structure

### Test Cases (10 total)

#### logger.py Tests (4 cases)
1. **test_session_logger_file_creation_and_loading**: Basic file operations
2. **test_add_entry_append_operations**: Multiple entry handling
3. **test_get_session_stats_token_calculation**: Token counting logic
4. **test_japanese_content_handling**: UTF-8/multi-byte character support

#### config.py Tests (2 cases)
5. **test_ensure_directories_creation**: Directory initialization
6. **test_estimate_tokens_precision**: Token estimation accuracy

#### Hook Tests (4 cases)
7. **test_user_prompt_submit_json_io**: user-prompt-submit.py I/O
8. **test_post_tool_use_json_io**: post-tool-use.py I/O
9. **test_stop_hook_finalize_session_call**: stop.py subprocess handling
10. **test_error_handling_invalid_json**: Error handling for malformed input

#### Integration Test (1 bonus)
11. **test_full_workflow_integration**: End-to-end workflow verification

## Test Coverage

The test suite aims for high coverage of:
- Core logging functionality
- Configuration management
- Hook input/output processing
- Error handling
- UTF-8/Unicode support
- Token estimation

## Continuous Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: pip install -r requirements-dev.txt

- name: Run tests
  run: pytest --cov=src/hooks --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```
