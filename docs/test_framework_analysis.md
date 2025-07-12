# PSH Test Framework Analysis and Recommendations

## Executive Summary

The PSH test suite has chronic issues with output capture and test isolation, particularly when running tests in parallel. This analysis examines the current state, identifies root causes, and provides actionable recommendations for improvement.

## Current State Analysis

### Test Infrastructure Overview

PSH uses two test suites:
- **Legacy suite** (`tests/`): ~1900 tests with known isolation problems
- **New suite** (`tests_new/`): ~1000 tests with improved but still problematic isolation

### Output Capture Approaches

The test suite uses multiple incompatible approaches for output capture:

1. **pytest's capsys fixture** - Used in 200+ tests
   - Captures Python-level stdout/stderr
   - Works well for simple cases
   - Conflicts with shell's direct file descriptor manipulation

2. **captured_shell fixture** - Custom fixture with MockStdout/MockStderr
   - Attempts to capture shell output directly
   - Inconsistent behavior across test types
   - Only used in ~5 tests (mainly parameter expansion)

3. **Direct stdout/stderr assignment** - Manual capture in some tests
   - Most fragile approach
   - Leads to state leakage between tests

4. **subprocess.run with capture_output** - For conformance tests
   - Most reliable for external process testing
   - Not suitable for unit tests

### Key Problems Identified

#### 1. File Descriptor State Conflicts
- Shell manipulates file descriptors directly for redirections
- pytest's capture mechanisms interfere with this manipulation
- Tests involving `2>&1`, `>&2` frequently fail or are skipped
- 15+ tests skipped in `test_advanced_redirection.py` alone

#### 2. Process Isolation Issues
- Parallel test execution (`pytest -n auto`) causes test failures
- Tests kill each other's processes
- Subprocess tests contaminate the test environment
- ~20 tests marked as `@pytest.mark.serial` to avoid conflicts

#### 3. Output Capture Inconsistency
- Different test files use different capture methods
- No clear guidance on which approach to use when
- Fixture hierarchy unclear: shell → captured_shell → isolated_shell_with_temp_dir

#### 4. Interactive Test Challenges
- All interactive tests skipped due to pexpect/pytest conflicts
- PTY handling incompatible with pytest's I/O capture
- No viable solution for testing interactive features

## Root Cause Analysis

### 1. Architectural Mismatch
The fundamental issue is that PSH is designed to manipulate file descriptors directly (as any shell must), while pytest assumes control over I/O streams for output capture. This creates an irreconcilable conflict.

### 2. Fixture Design Issues
- The `shell` fixture doesn't capture output by default
- The `captured_shell` fixture is underutilized and poorly documented
- No clear separation between unit tests (need capture) and integration tests (need real FDs)

### 3. Test Classification Problems
Many tests are misclassified:
- Unit tests that should be integration tests
- Tests marked as failures that actually work correctly
- Missing test markers for isolation requirements

## Recommendations

### 1. Immediate Actions

#### A. Standardize Output Capture Pattern
Create a clear hierarchy of test types and their appropriate fixtures:

```python
# For unit tests of builtins/components
def test_builtin_echo(captured_shell):
    """Use captured_shell for builtin output testing"""
    result = captured_shell.run_command('echo "hello"')
    assert captured_shell.get_stdout() == "hello\n"

# For integration tests with real I/O
def test_io_redirection(isolated_shell_with_temp_dir):
    """Use isolated shell for file descriptor manipulation"""
    shell = isolated_shell_with_temp_dir
    shell.run_command('echo "test" > output.txt')
    # Verify file contents, not captured output

# For conformance tests
def test_posix_compliance(self):
    """Use subprocess for external comparison"""
    psh_result = subprocess.run(['python', '-m', 'psh', '-c', 'cmd'])
    bash_result = subprocess.run(['bash', '-c', 'cmd'])
    assert psh_result.stdout == bash_result.stdout
```

#### B. Fix Test Misclassification
1. Review all skipped/xfailed tests
2. Reclassify based on actual failure reason:
   - Output capture conflict → Move to integration test
   - Process isolation → Mark as serial
   - Feature not implemented → Keep as xfail

#### C. Document Best Practices
Add to CLAUDE.md:
```markdown
## Test Writing Guidelines

### Choosing the Right Test Type

1. **Unit Tests** (use `captured_shell`)
   - Testing builtin command output
   - Testing parser/lexer components
   - Testing expansion logic
   - No file I/O or process spawning

2. **Integration Tests** (use `isolated_shell_with_temp_dir`)
   - Testing I/O redirection
   - Testing pipelines
   - Testing job control
   - File system operations

3. **System Tests** (use `subprocess`)
   - Testing full shell behavior
   - Comparing with bash
   - Testing process lifecycle
   - Interactive features (when possible)

### Output Capture Rules

1. NEVER use capsys with shell tests that do I/O redirection
2. ALWAYS use captured_shell for builtin output testing
3. PREFER subprocess.run for external command testing
4. AVOID mixing capture methods in the same test
```

### 2. Medium-term Improvements

#### A. Enhanced Fixture System
```python
@pytest.fixture
def unit_test_shell():
    """Shell configured for unit testing with full output capture"""
    shell = Shell()
    # Configure for deterministic unit testing
    shell.stdout = MockStdout()
    shell.stderr = MockStderr()
    # Disable features that interfere with testing
    shell.state.options['interactive'] = False
    return shell

@pytest.fixture
def integration_test_shell(temp_dir):
    """Shell configured for integration testing with real I/O"""
    shell = Shell()
    shell.state.variables['PWD'] = temp_dir
    # Use real file descriptors
    return shell

@pytest.fixture
def conformance_test_env():
    """Environment for subprocess-based conformance testing"""
    return {
        'env': clean_env(),
        'cwd': temp_dir(),
        'timeout': 5
    }
```

#### B. Test Reorganization
1. Create clear directory structure:
   ```
   tests_new/
   ├── unit/          # Pure unit tests with mocked I/O
   ├── integration/   # Component integration with real I/O  
   ├── system/        # Full system tests via subprocess
   └── conformance/   # Bash compatibility tests
   ```

2. Move tests to appropriate categories based on I/O requirements

#### C. Parallel Execution Strategy
1. Run test categories separately:
   ```bash
   # Fast unit tests in parallel
   pytest tests_new/unit -n auto
   
   # Integration tests with process isolation
   pytest tests_new/integration -n 4 --dist loadgroup
   
   # System tests serially
   pytest tests_new/system
   ```

### 3. Long-term Solutions

#### A. Test Mode for PSH
Add a `--test-mode` flag to PSH that:
- Disables interactive features
- Uses simplified I/O handling
- Provides deterministic behavior
- Enables output interception

#### B. Custom Test Runner
Consider alternatives to pytest for shell testing:
- Bats (Bash Automated Testing System) - designed for shell testing
- Custom runner that understands file descriptor semantics
- Docker-based isolation for each test

#### C. Formal Test Strategy Document
Create comprehensive testing strategy covering:
- When to use each test type
- How to handle common scenarios
- Performance vs. isolation tradeoffs
- Migration path from legacy tests

## Implementation Priority

1. **Week 1**: Fix test misclassification and document best practices
2. **Week 2**: Standardize on captured_shell for unit tests
3. **Week 3**: Reorganize tests into proper categories  
4. **Week 4**: Implement enhanced fixtures
5. **Month 2**: Evaluate alternative test frameworks
6. **Month 3**: Implement test mode in PSH if needed

## Success Metrics

- Reduce test skips from 50+ to <10
- Achieve 100% pass rate with `pytest -n auto`
- Clear documentation prevents new test issues
- Conformance test accuracy improves to 95%+
- Developer productivity increases with reliable tests

## Conclusion

The PSH test framework issues stem from fundamental conflicts between shell I/O manipulation and pytest's capture mechanisms. By clearly separating test types, standardizing approaches, and providing proper tooling, we can achieve both reliable testing and good performance. The key is acknowledging that different types of tests require different approaches rather than trying to force a one-size-fits-all solution.