# Runtime Skip Analysis for PSH Test Suite

## Summary
Total skipped tests: **116** (out of 2056 total tests)

## Breakdown by Category

### 1. Interactive Tests (84 tests - 72.4%)
- **Location**: Various files in `integration/interactive/` and `system/interactive/`
- **Skip Reason**: "Interactive tests skipped (use --run-interactive to run)"
- **Controlled by**: `tests_new/conftest.py:353`
- **Files affected**:
  - `test_completion.py` - Tab completion tests
  - `test_history.py` - History navigation tests
  - `test_job_control.py` - Job control tests
  - `test_prompt.py` - Prompt customization tests

### 2. Pexpect Not Installed (22 tests - 19.0%)
- **Location**: `system/interactive/test_line_editing.py`
- **Skip Reason**: "pexpect not installed"
- **Issue**: These tests require the pexpect library for PTY interaction
- **Note**: These are in addition to the @pytest.mark.skip decorators

### 3. Heredoc Architecture Issues (7 tests - 6.0%)
- **Location**: `integration/redirection/test_heredoc.py`
- **Skip Reasons**:
  - "Heredoc execution needs architectural updates for proper input handling" (4 tests)
  - "External command integration with heredocs needs architecture updates" (1 test)
  - "Multiple redirection handling needs architecture updates" (1 test)
  - "Pipeline heredoc integration needs architecture updates" (1 test)

### 4. Feature Not Implemented (2 tests - 1.7%)
- **Background subshells**: 1 test in `test_subshell_implementation.py`
- **Line editing**: 1 test in `test_basic_interactive.py`

### 5. Test Implementation Issues (1 test - 0.9%)
- **Function with heredoc**: 1 test in `test_function_advanced.py`
- **Skip Reason**: "Function definition with here document failed"

## Key Findings

### Interactive Tests are the Main Source
- 84 out of 116 skipped tests (72.4%) are interactive tests
- These are skipped by default unless `--run-interactive` flag is used
- This is by design to avoid issues in CI/automated environments

### Pexpect Dependency
- 22 tests require pexpect library which isn't installed
- These are separate from the @pytest.mark.skip decorators we saw earlier
- Installing pexpect would still leave these skipped due to interactive flag

### Architectural Limitations
- 7 heredoc tests reveal a core limitation in PSH's architecture
- Heredocs don't work properly with the test framework
- This requires changes to how PSH handles input streams

## Runtime vs Static Skips

### Static Skips (from @pytest.mark.skip)
- Previously counted: 22 tests
- These are explicitly marked in code

### Runtime Skips
- 116 tests skipped at runtime
- Main causes:
  1. Interactive flag check (84 tests)
  2. Missing dependencies (22 tests)
  3. Feature detection (10 tests)

## Recommendations

### 1. Run Interactive Tests Separately
```bash
python -m pytest tests_new/ --run-interactive
```

### 2. Install Optional Dependencies
```bash
pip install pexpect
```

### 3. Fix Test Implementation
- Fix the function heredoc test that's failing
- This appears to be a test bug, not a PSH bug

### 4. Address Architectural Issues
- Heredoc handling needs core changes
- Background subshells need implementation

## Test Coverage Impact

- **Total tests**: 2056
- **Passing**: 1757 (85.5%)
- **Skipped**: 116 (5.6%)
- **XFailed**: 130 (6.3%)
- **XPassed**: 52 (2.5%)
- **Failed**: 1 (0.05%)

Even with skips, PSH has strong test coverage with 85.5% of tests passing.

## Interactive Tests Analysis

When running interactive tests with `--run-interactive`:
- **Total interactive tests**: 51 (in integration/interactive/)
- **XFailed**: 12 (marked as expected to fail)
- **XPassed**: 39 (marked as xfail but actually pass!)

This means **76% of interactive tests are actually working** but marked as xfail!

## Action Items

1. **Fix test markings**: 39 interactive tests should have their xfail markers removed
2. **Install pexpect**: Would enable 22 more line editing tests
3. **Fix trap test**: The one failing test needs investigation
4. **Review xfail markers**: Many tests marked as xfail are actually passing