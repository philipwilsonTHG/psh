# pexpect Testing Issue with PSH

## Problem Description

When running PSH with pexpect inside pytest, the prompt matching fails even though PSH is working correctly. The issue appears to be related to how pexpect handles buffering when `logfile_read` is set.

## Symptoms

1. PSH starts and shows prompts correctly (visible in logged output)
2. pexpect's `expect()` method times out trying to match the prompt pattern
3. The `before` and `buffer` attributes remain empty even though output is being logged
4. The same code works when run directly outside pytest

## Workarounds

### 1. Use subprocess for non-interactive tests
See `test_subprocess_commands.py` for examples. This approach works well for:
- Basic command execution
- Pipeline testing
- Variable assignment and expansion
- Error handling

### 2. For true interactive tests requiring pexpect
- Consider using a test runner other than pytest
- Run pexpect tests in a separate test suite
- Use expect with more flexible patterns or timeouts

## Technical Details

The issue seems to be a complex interaction between:
- Python's subprocess buffering
- pexpect's PTY handling
- pytest's output capture
- PSH's line editor and prompt display

Even with:
- `PYTHONUNBUFFERED=1`
- `python -u` flag
- `--force-interactive` flag for PSH
- Explicit stdout flushing

The pattern matching still fails within pytest.

## Future Solutions

1. Investigate alternative interactive testing frameworks
2. Consider implementing a testing mode in PSH that uses simpler I/O
3. Use integration tests that run PSH as a complete subprocess
4. Explore using `ptyprocess` directly instead of pexpect