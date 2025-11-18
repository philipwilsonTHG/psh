# Subshell Integration Tests

This directory contains comprehensive integration tests for PSH subshell functionality.

## Running the Tests

Due to pytest's output capture mechanism interfering with file descriptor operations in forked child processes, these tests require special handling:

### Recommended: Run with capture disabled

```bash
# Run all subshell tests (recommended)
python -m pytest tests/integration/subshells/ -s

# Run specific test file
python -m pytest tests/integration/subshells/test_subshell_basics.py -s

# Run individual test
python -m pytest tests/integration/subshells/test_subshell_basics.py::test_subshell_basic_execution -s
```

The `-s` flag disables pytest's output capture, allowing file redirections in forked subshells to work correctly.

### Test Status

**With `-s` flag (capture disabled):**
- `test_subshell_basics.py`: 12 passed, 2 xfailed, 1 xpassed ✅
- `test_subshell_implementation.py`: 28 passed, 1 skipped, 3 xfailed ✅
- `test_subshell_terminal_control.py`: 3 passed ✅

**Without `-s` flag:**
- Many tests fail with empty output files due to pytest capture interference

## Technical Details

### The Issue

When pytest captures output (default behavior), it replaces `sys.stdout` and `sys.stderr` with capture objects. When PSH forks a child process for a subshell and tries to redirect output to a file, the forked process inherits these capture objects rather than real file descriptors. This causes file redirections to fail - output goes to pytest's capture instead of the target file.

### Solutions Attempted

1. ✅ **Fixed fixture usage**: Changed from `shell_with_temp_dir` to `isolated_shell_with_temp_dir`
   - This ensures tests run in the correct working directory
   - Properly isolates each test's file system operations

2. ❌ **Using `sys.__stdout__`**: Attempted to use underlying streams
   - Didn't solve the capture interference issue

3. ❌ **Using `capfd.disabled()`**: Attempted to programmatically disable capture
   - Context management complexities, didn't resolve the issue

4. ✅ **Using `-s` flag**: Simplest and most reliable solution
   - Disables pytest's capture entirely
   - All tests pass consistently

### Why Individual Tests Pass

When running a single test in isolation, pytest's capture mechanism behaves differently - there's less contention for file descriptors and output streams. The isolation reduces (but doesn't eliminate) the interference.

## Test Organization

- **test_subshell_basics.py**: Basic subshell functionality (execution, variables, I/O)
- **test_subshell_implementation.py**: Comprehensive implementation tests (isolation, inheritance, compatibility)
- **test_subshell_terminal_control.py**: Terminal control and job control integration

## Verifying Fixes

To verify that subshell functionality works correctly:

```bash
# Manual testing (always works)
python -m psh -c '(echo "hello from subshell") > output.txt && cat output.txt'

# Individual test (usually works)
python -m pytest tests/integration/subshells/test_subshell_basics.py::test_subshell_basic_execution -xvs

# Full suite with proper capture handling (always works)
python -m pytest tests/integration/subshells/ -s
```

## Future Improvements

Potential solutions for running without `-s` flag:

1. Rewrite tests to use subprocess spawning instead of fixture-based Shell instances
2. Implement custom pytest plugin to handle fork-based tests
3. Use lower-level file descriptor manipulation in fixtures
4. Mark tests with custom decorator that auto-disables capture

For now, using `-s` flag is the recommended and supported approach.
