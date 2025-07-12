# Analysis of Skipped Tests in tests_new

## Summary

A total of 13 test files contain skipped tests in the `tests_new` directory. These fall into several categories based on the reasons for skipping.

## Categories of Skipped Tests

### 1. Interactive/Terminal Tests (Most Common)

**Files affected:**
- `tests_new/system/interactive/test_basic_interactive.py`
- `tests_new/system/interactive/test_line_editing.py`
- `tests_new/system/interactive/test_simple_commands.py`

**Skip reasons:**
- "Line editing may not be fully supported yet"
- "PSH line editor escape sequences not working properly in PTY environment"
- "Tab completion requires raw terminal mode"
- "Job control tests require special terminal handling"

**Root cause:** These tests require a proper terminal emulator (PTY) environment and raw terminal mode, which conflicts with pytest's test runner and output capture mechanisms.

### 2. File Descriptor/Redirection Issues

**Files affected:**
- `tests_new/integration/redirection/test_advanced_redirection.py`

**Skip reasons:**
- "2>&1 redirection causes file descriptor state issues between tests"
- "Named pipe tests can hang due to blocking I/O coordination issues"
- "Bidirectional named pipe tests are complex and can hang"

**Root cause:** Complex I/O redirection operations can leave file descriptors in inconsistent states, causing test pollution and hangs.

### 3. Unsafe Operations

**Files affected:**
- `tests_new/unit/builtins/test_exec_builtin.py`
- `tests_new/unit/builtins/test_signal_builtins.py`

**Skip reasons:**
- "Exec with command replacement exits the process - unsafe for testing"
- "Signal execution test sends SIGTERM to test process - unsafe"

**Root cause:** These operations would terminate or significantly affect the test process itself.

### 4. Poorly Implemented Tests

**Files affected:**
- `tests_new/integration/redirection/test_advanced_redirection.py`

**Skip reasons:**
- "this is a poorly implemented test" (3 occurrences)

**Root cause:** Tests were written but not properly designed or verified.

### 5. Feature-Specific Issues

**Files affected:**
- Various files with specific feature limitations

**Examples:**
- Timeout command availability for named pipes
- Platform-specific signal handling (Windows vs Unix)

## Detailed Analysis by File

### Interactive Tests (`system/interactive/`)

These tests attempt to verify interactive shell features like:
- Line editing and cursor movement
- Command history navigation
- Tab completion
- Job control (Ctrl-Z)

**Problem:** pexpect/PTY interaction with pytest is problematic. The tests can't properly simulate terminal interactions.

### Redirection Tests (`integration/redirection/`)

Advanced redirection tests that are skipped:
- stderr to stdout duplication (`2>&1`)
- Named pipes (FIFOs)
- Multiple redirections in same command
- Background job redirections
- Subshell redirections

**Problem:** File descriptor manipulation conflicts with pytest's I/O capture and can cause state pollution between tests.

### Builtin Tests (`unit/builtins/`)

Dangerous builtins that can't be safely tested:
- `exec` - replaces the current process
- `trap` with actual signal delivery

**Problem:** These operations would affect the test runner itself.

## Recommendations

### 1. Interactive Tests - Use Alternative Testing Approach

**Short-term:**
- Create a separate test suite that runs outside pytest
- Use a dedicated interactive test runner that properly handles PTY
- Consider using tools like `expect` or `dejagnu` designed for interactive testing

**Long-term:**
- Implement a test mode in PSH that simulates interactive features without requiring actual terminal I/O
- Create mock objects for terminal interactions

**Example approach:**
```python
# Instead of actual PTY interaction
def test_line_editing_mock():
    """Test line editing with mocked terminal."""
    editor = LineEditor()
    editor.insert_text("hello")
    editor.cursor_left(2)
    editor.insert_text("X")
    assert editor.get_line() == "helXlo"
```

### 2. File Descriptor Tests - Improve Test Isolation

**Short-term:**
- Mark these tests with `@pytest.mark.serial` to prevent parallel execution
- Use subprocess isolation for each test
- Implement proper cleanup fixtures

**Long-term:**
- Create a test harness that runs each FD test in a completely isolated process
- Implement FD state verification before/after each test

**Example approach:**
```python
@pytest.mark.serial
@pytest.mark.isolated
def test_stderr_redirection_isolated(isolated_subprocess_env):
    """Test 2>&1 in isolated subprocess."""
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', 'ls /bad 2>&1'],
        **isolated_subprocess_env,
        capture_output=True
    )
    assert "No such file" in result.stdout
```

### 3. Unsafe Operations - Use Subprocess Testing

**Approach:**
- Test these features by spawning PSH as a subprocess
- Monitor the subprocess behavior from outside

**Example:**
```python
def test_exec_replacement():
    """Test exec by monitoring subprocess."""
    proc = subprocess.Popen(
        [sys.executable, '-m', 'psh', '-c', 'exec echo replaced'],
        stdout=subprocess.PIPE
    )
    stdout, _ = proc.communicate()
    assert stdout == b'replaced\n'
    assert proc.returncode == 0
```

### 4. Fix Poorly Implemented Tests

**Action items:**
1. Review each "poorly implemented" test
2. Determine actual test intent
3. Rewrite with proper assertions and cleanup

### 5. Platform-Specific Tests - Use Conditional Skipping

**Approach:**
- Use `@pytest.mark.skipif` with platform detection
- Provide alternative tests for different platforms

**Example:**
```python
@pytest.mark.skipif(sys.platform == "win32", 
                    reason="Unix-specific signal test")
def test_unix_signals():
    # Unix signal tests

@pytest.mark.skipif(sys.platform != "win32",
                    reason="Windows-specific test")
def test_windows_signals():
    # Windows alternatives
```

## Priority Recommendations

### High Priority (Fix Now)
1. **Fix "poorly implemented" tests** - These are low-hanging fruit
2. **Subprocess-based exec/signal tests** - Important functionality that can be tested safely
3. **Basic redirection tests** - Use better isolation to enable these

### Medium Priority (Fix Soon)
1. **Named pipe tests** - Important for POSIX compliance
2. **FD duplication tests** - Core shell functionality
3. **Create interactive test framework** - Separate from pytest

### Low Priority (Future Enhancement)
1. **Full terminal emulation tests** - Complex but less critical
2. **Advanced tab completion** - Nice to have but not essential

## Implementation Plan

### Phase 1: Quick Wins (1 day)
1. Fix the 3 "poorly implemented" tests
2. Convert exec/signal tests to subprocess-based approach
3. Add serial/isolated markers to FD tests

### Phase 2: Isolation Improvements (3 days)
1. Create robust subprocess test fixtures
2. Fix basic redirection tests with proper isolation
3. Enable named pipe tests with timeouts

### Phase 3: Interactive Framework (1 week)
1. Design interactive test framework outside pytest
2. Create mock-based unit tests for line editing
3. Document interactive testing approach

### Phase 4: Complete Coverage (2 weeks)
1. Enable all remaining tests with appropriate solutions
2. Add new tests for previously untestable scenarios
3. Create CI/CD integration for special test suites

## Expected Outcomes

By implementing these recommendations:
- **Immediate**: Enable ~10 currently skipped tests
- **Short-term**: Reduce skipped tests from ~25 to <5
- **Long-term**: Achieve near-100% test coverage with appropriate test strategies

The key insight is that different types of functionality require different testing approaches. By using the right tool for each type of test, we can achieve comprehensive coverage without compromising test reliability or safety.