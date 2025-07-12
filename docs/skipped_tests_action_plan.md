# Action Plan for Fixing Skipped Tests

## Overview
- **Total skipped tests**: 42
- **Immediately fixable**: ~15 tests
- **Require architectural changes**: ~20 tests
- **May remain skipped**: ~7 tests (platform-specific or inherently unsafe)

## Immediate Actions (Can be fixed now)

### 1. Fix "Poorly Implemented" Tests (3 tests)
**File**: `tests_new/integration/redirection/test_advanced_redirection.py`

**Tests to fix**:
- `test_multiple_redirections_same_command`
- `test_redirection_with_background_jobs`
- `test_redirection_in_subshells`

**Solution**: Use proper command grouping and isolated execution
```python
# Instead of:
shell.run_command('''
echo "stdout" > file1
echo "stderr" >&2
''')

# Use:
shell.run_command('{ echo "stdout"; echo "stderr" >&2; } > file1 2> file2')
```

### 2. Convert Unsafe Tests to Subprocess (2 tests)
**Files**: 
- `tests_new/unit/builtins/test_exec_builtin.py`
- `tests_new/unit/builtins/test_signal_builtins.py`

**Solution**: Test in isolated subprocess
```python
def test_exec_subprocess():
    proc = subprocess.Popen(
        [sys.executable, '-m', 'psh', '-c', 'exec echo replaced'],
        stdout=subprocess.PIPE
    )
    stdout, _ = proc.communicate()
    assert stdout == b'replaced\n'
```

### 3. Fix Basic Redirection Tests with Isolation (5 tests)
**File**: `tests_new/integration/redirection/test_advanced_redirection.py`

**Tests**:
- `test_stderr_to_stdout_duplication`
- `test_stderr_to_stdout_redirection`

**Solution**: Use `isolated_shell_with_temp_dir` fixture and mark as serial
```python
@pytest.mark.serial
@pytest.mark.isolated
def test_stderr_to_stdout_fixed(isolated_shell_with_temp_dir):
    shell = isolated_shell_with_temp_dir
    # Test implementation
```

### 4. Fix Named Pipe Tests with Timeouts (3 tests)
**File**: `tests_new/integration/redirection/test_advanced_redirection.py`

**Solution**: Use threading and timeouts to prevent hangs
```python
def test_named_pipe_with_timeout():
    import threading
    import time
    
    def writer():
        shell.run_command('echo data > fifo')
    
    def reader():
        shell.run_command('cat < fifo')
    
    # Run with timeout
    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
```

## Medium-term Actions (Require framework changes)

### 1. Create Interactive Test Framework (~20 tests)
**Files**: All in `tests_new/system/interactive/`

**Approach**:
1. Create separate test runner outside pytest
2. Use proper PTY handling with pexpect
3. Run as separate CI job

**Example structure**:
```python
# interactive_test_runner.py
import pexpect
import sys

def run_interactive_tests():
    # Spawn PSH with proper PTY
    child = pexpect.spawn('python -m psh', encoding='utf-8')
    child.expect('psh>')
    
    # Run test sequences
    test_results = []
    test_results.append(test_line_editing(child))
    test_results.append(test_tab_completion(child))
    
    return all(test_results)
```

### 2. Implement Mock-based Unit Tests for Line Editor
**Alternative to PTY tests**:
```python
class TestLineEditorUnit:
    def test_cursor_movement(self):
        editor = LineEditor()
        editor.buffer = "hello world"
        editor.cursor = 5
        
        editor.move_left()
        assert editor.cursor == 4
        
        editor.move_word_right()
        assert editor.cursor == 11
```

## Long-term Actions

### 1. Test Mode for PSH
Add `--test-mode` flag that:
- Disables raw terminal mode
- Provides hooks for test assertions
- Allows programmatic line editing

### 2. Comprehensive Test Isolation Framework
- Docker containers for each test
- Process-level isolation
- FD state verification

## Prioritized Implementation Schedule

### Week 1: Quick Fixes
- [ ] Fix 3 "poorly implemented" tests
- [ ] Convert 2 unsafe tests to subprocess
- [ ] Fix 5 basic redirection tests with isolation
- [ ] Fix 3 named pipe tests with timeouts
- **Total: Enable 13 tests**

### Week 2: Framework Improvements
- [ ] Create interactive test runner
- [ ] Implement basic PTY test suite
- [ ] Add mock-based line editor tests
- **Total: Enable ~10 more tests**

### Week 3: Complete Coverage
- [ ] Implement remaining subprocess tests
- [ ] Add platform-specific conditionals
- [ ] Document permanent skips
- **Total: Reduce skips to <5**

## Success Metrics

### Current State
- 42 skipped tests
- ~1000 active tests
- 4.2% skip rate

### Target State (after 3 weeks)
- <5 skipped tests
- ~1040 active tests
- <0.5% skip rate

### Permanent Skips (Expected)
- Platform-specific tests on wrong platform
- Tests requiring specific external tools
- Inherently unsafe operations in main process

## Testing the Fixes

After implementing fixes:
```bash
# Run all tests including previously skipped
pytest tests_new -v --tb=short

# Run specific categories
pytest tests_new/integration/redirection -v
pytest tests_new/unit/builtins -v

# Run with strict isolation
pytest tests_new -n 1 --strict-isolation

# Run interactive tests separately
python interactive_test_runner.py
```

## Conclusion

Most skipped tests can be enabled with proper test design:
- 13 tests can be fixed immediately with better implementation
- 20 tests need architectural changes but are fixable
- Only ~7 tests may need to remain skipped for safety/platform reasons

The key insight is that different functionality requires different testing approaches. By using the right testing strategy for each type of feature, we can achieve >95% test coverage.