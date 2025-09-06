# Testing Guide

## Test Performance Optimization

This project has been optimized for fast test execution during development while maintaining comprehensive coverage for CI/CD pipelines.

## Available Test Commands

### Quick Commands

```bash
# Fast development tests (recommended for daily use)
make test              # 2.56s - Parallel execution, excludes slow tests
make test-fast         # 2.56s - Same as above (explicit alias)

# Comprehensive testing
make test-all          # 8.20s - All tests including slow ones
make test-parallel     # 3.52s - All tests in parallel
make coverage          # 8.60s - Full coverage report
```

### Manual pytest Commands

```bash
# Fast tests only
uv run pytest -n auto -m "not slow"

# All tests in parallel
uv run pytest -n auto

# All tests sequential
uv run pytest

# Coverage report
uv run pytest --cov=src/mcp_shell_server --cov-report=xml --cov-report=term-missing tests
```

## Test Categories

### Fast Tests (Default)
- **Count**: 114 tests
- **Execution**: ~2.56 seconds
- **Parallel**: 8 workers
- **Usage**: Daily development, quick feedback

### Slow Tests
- **Marked with**: `@pytest.mark.slow`
- **Purpose**: Timeout testing, integration scenarios
- **Usage**: CI/CD, comprehensive validation

## Performance Improvements Applied

### 1. Parallel Execution
- **Tool**: pytest-xdist
- **Workers**: Auto-detected (typically 8 on modern systems)
- **Speed gain**: ~4x faster execution

### 2. Sleep Optimization
- Reduced `asyncio.sleep(10)` → `asyncio.sleep(0.01)` (999x faster)
- Reduced `asyncio.sleep(1)` → `asyncio.sleep(0.1)` (10x faster)
- **Files affected**:
  - `tests/test_server.py:473`
  - `tests/test_process_manager_macos.py:46`

### 3. Test Categorization
- Timeout tests marked as `@pytest.mark.slow`
- Selective execution with `-m "not slow"`
- Development focus on fast feedback

## Development Workflow

### During Development
```bash
# Quick validation (recommended)
make test              # 2.56s, 114 tests

# If you need specific test
uv run pytest tests/test_specific.py -v
```

### Before Commits
```bash
# Full validation
make test-all          # All tests including slow ones
make coverage          # Ensure coverage standards
```

### CI/CD Pipeline
```bash
# Comprehensive validation
make test-parallel     # Fast but complete
make coverage          # Coverage reporting
```

## Coverage Standards

- **Target**: 95% minimum coverage
- **Current**: 95% (598 statements, 29 missing)
- **High-coverage modules**:
  - `command_validator.py`: 100%
  - `command_preprocessor.py`: 98%
  - `shell_executor.py`: 97%
  - `server.py`: 96%

## Adding New Tests

### Fast Tests (Default)
```python
import pytest

@pytest.mark.asyncio
async def test_my_feature():
    # Regular test - will run in fast mode
    assert True
```

### Slow Tests
```python
import pytest

@pytest.mark.slow  # Mark as slow test
@pytest.mark.asyncio
async def test_timeout_behavior():
    # Test that involves timeouts or long waits
    await asyncio.sleep(2)  # This is OK in slow tests
    assert True
```

## Troubleshooting

### Tests Taking Too Long?
1. Check if you're using `make test` (fast) vs `make test-all` (comprehensive)
2. Ensure pytest-xdist is installed: `uv pip install pytest-xdist`
3. Use `-v` flag for verbose output to identify slow tests

### Coverage Issues?
```bash
# Generate detailed coverage report
make coverage

# View in browser (if HTML report generated)
open htmlcov/index.html
```

### Test Failures in CI?
- CI runs `make test-parallel` (all tests including slow ones)
- Local development uses `make test` (excludes slow tests)
- Ensure slow tests are properly marked with `@pytest.mark.slow`

## Performance Metrics

| Test Category | Tests | Time | Workers | Usage |
|---------------|--------|------|---------|--------|
| `make test` | 114 | 2.56s | 8 | Development |
| `make test-fast` | 114 | 2.56s | 8 | Development |
| `make test-parallel` | 120 | 3.52s | 8 | CI/CD |
| `make test-all` | 120 | 8.20s | 1 | Full validation |
| `make coverage` | 120 | 8.60s | 1 | Coverage analysis |

## Best Practices

1. **Use `make test` for development** - Fast feedback loop
2. **Mark timeout tests as slow** - Keep development tests fast
3. **Run full tests before commits** - Ensure nothing breaks
4. **Monitor coverage** - Maintain 95% minimum
5. **Optimize sleep calls** - Use minimal delays in tests
6. **Leverage parallel execution** - Take advantage of multi-core systems