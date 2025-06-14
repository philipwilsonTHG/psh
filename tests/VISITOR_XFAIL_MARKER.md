# Visitor XFail Marker

The `visitor_xfail` marker is used to mark tests that are expected to fail when using the visitor executor due to pytest output capture limitations.

## Background

The visitor executor implementation uses forking for external commands and pipelines. When processes are forked, their output goes directly to the terminal file descriptors and bypasses pytest's output capture mechanisms. This is a known limitation of pytest when dealing with forked processes.

## Usage

```python
import pytest

@pytest.mark.visitor_xfail(reason="Output capture doesn't work with forked processes")
def test_external_command(shell, capsys):
    """Test that captures output from an external command."""
    exit_code = shell.run_command("/bin/ls")
    captured = capsys.readouterr()
    assert "expected_output" in captured.out  # Will fail with visitor executor
```

## When to Use

Use the `visitor_xfail` marker for tests that:

1. Capture output from external commands (forked processes)
2. Capture output from pipelines (which involve forking)
3. Rely on pytest's `capsys` or `capfd` fixtures to capture stdout/stderr from forked processes

## When NOT to Use

Do not use this marker for tests that:

1. Only test built-in commands (which don't fork)
2. Only check exit codes (not output)
3. Test functionality unrelated to output capture

## How It Works

The marker is implemented in `conftest.py` and:

1. Checks if the `PSH_USE_VISITOR_EXECUTOR` environment variable is set to '1'
2. If the visitor executor is being used, automatically applies `pytest.mark.xfail` to marked tests
3. If the legacy executor is being used, the tests run normally

## Running Tests

```bash
# Run with legacy executor (default)
python -m pytest tests/

# Run with visitor executor
PSH_USE_VISITOR_EXECUTOR=1 python -m pytest tests/

# See which tests are marked as visitor_xfail
python -m pytest -v -k "visitor_xfail"
```

## Future Improvements

Once the test infrastructure is updated to handle forked process output capture (possibly using PTY or other mechanisms), these markers can be removed and all tests should pass with both executors.