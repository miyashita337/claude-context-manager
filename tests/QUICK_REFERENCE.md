# Python Hooks Test Suite - Quick Reference

## Quick Start

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with verbose output and coverage
pytest -v --cov=src/hooks
```

## Test Cases Overview (11 total)

### Logger Module (4 tests)
1. ✅ **test_session_logger_file_creation_and_loading** - File I/O basics
2. ✅ **test_add_entry_append_operations** - Entry management
3. ✅ **test_get_session_stats_token_calculation** - Stats calculation
4. ✅ **test_japanese_content_handling** - UTF-8 support

### Config Module (2 tests)
5. ✅ **test_ensure_directories_creation** - Directory management
6. ✅ **test_estimate_tokens_precision** - Token estimation

### Hooks (4 tests)
7. ✅ **test_user_prompt_submit_json_io** - User prompt hook
8. ✅ **test_post_tool_use_json_io** - Tool usage hook
9. ✅ **test_stop_hook_finalize_session_call** - Stop hook
10. ✅ **test_error_handling_invalid_json** - Error handling

### Integration (1 test)
11. ✅ **test_full_workflow_integration** - End-to-end workflow

## Common Commands

```bash
# Run specific test
pytest tests/test_hooks.py::test_japanese_content_handling

# Run tests matching pattern
pytest -k "logger"

# Show print statements
pytest -v -s

# Generate HTML coverage report
pytest --cov=src/hooks --cov-report=html
# Open htmlcov/index.html in browser

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Show slowest tests
pytest --durations=10
```

## Test Categories

### Unit Tests
- logger.py tests (1-4)
- config.py tests (5-6)

### Integration Tests
- Hook tests (7-10)
- Full workflow (11)

## Coverage Summary

| Module | Coverage | Status |
|--------|----------|--------|
| logger.py | 100% | ✅ Complete |
| config.py | 100% | ✅ Complete |
| stop.py | 73% | ⚠️ Partial |
| user-prompt-submit.py | 62% | ⚠️ Partial |

Note: Hook modules have lower coverage because tests verify logic directly rather than subprocess execution.

## Test Data Patterns

### Session IDs
- `test-session-123` - Default fixture
- `test-session-456` - User prompt test
- `test-session-789` - Tool use test
- `test-session-stop` - Stop hook test

### Test Content
- English: "Hello, Claude!"
- Japanese: "こんにちは世界！これはテストです。"
- Mixed: "Hello世界! This is a テスト message."

## Debugging Tests

### Enable verbose output
```bash
pytest -vv
```

### Show local variables on failure
```bash
pytest -l
```

### Drop into debugger on failure
```bash
pytest --pdb
```

### Run with print debugging
```bash
pytest -s
```

## File Structure

```
claude-context-manager/
├── pytest.ini                 # pytest configuration
├── requirements-dev.txt       # test dependencies
└── tests/
    ├── README.md             # detailed documentation
    ├── QUICK_REFERENCE.md    # this file
    └── test_hooks.py         # test suite (11 tests)
```

## Dependencies

- pytest >= 8.0.0
- pytest-mock >= 3.12.0
- pytest-cov >= 4.1.0

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    pip install -r requirements-dev.txt
    pytest --cov=src/hooks --cov-report=xml
```

## Troubleshooting

### Import errors
```bash
# Ensure you're in the project root
cd /Users/harieshokunin/claude-context-manager
pytest
```

### Module not found
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Install in development mode
pip install -e .
```

### Permission errors
```bash
# Tests use temporary directories
# No special permissions needed
```

## Next Steps

1. Run tests: `pytest -v`
2. Check coverage: `pytest --cov=src/hooks --cov-report=html`
3. Review report: Open `htmlcov/index.html`
4. Add new tests as needed

## Resources

- pytest docs: https://docs.pytest.org/
- pytest-mock: https://pytest-mock.readthedocs.io/
- pytest-cov: https://pytest-cov.readthedocs.io/
