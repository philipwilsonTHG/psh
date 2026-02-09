# PSH Test Framework Recommendations Summary

> [!IMPORTANT]
> Historical migration analysis. For current contributor and CI test commands, use `docs/testing_source_of_truth.md`.

## Key Findings

### 1. Extensive Test Misclassification
- **95.5% of common shell features work identically** in PSH and bash
- Conformance tests report only 77.1% bash compatibility due to test framework issues
- Actual bash compatibility is likely **>85-90%**

### 2. Output Capture Conflict
The fundamental issue is architectural:
- PSH manipulates file descriptors directly (as any shell must)
- pytest assumes control over I/O streams for output capture
- These two approaches are incompatible

### 3. Inconsistent Test Approaches
Current test suite uses 4 different output capture methods:
1. `capsys` fixture (200+ tests) - Works for simple cases
2. `captured_shell` fixture (5 tests) - Underutilized
3. Direct stdout/stderr assignment - Fragile
4. `subprocess.run` - Most reliable but only for external testing

## Immediate Recommendations

### 1. Fix Test Misclassification (1 day)
```bash
# Run the analysis script to identify misclassified tests
python scripts/analyze_test_classification.py

# Update conformance tests to properly classify working features
# This alone could improve reported compatibility to >85%
```

### 2. Standardize Test Patterns (1 week)

#### For Unit Tests
```python
def test_builtin_output(captured_shell):
    """Use captured_shell for testing builtin output"""
    result = captured_shell.run_command('echo "hello"')
    assert captured_shell.get_stdout() == "hello\n"
    assert result == 0
```

#### For Integration Tests
```python
def test_io_redirection(isolated_shell_with_temp_dir):
    """Use isolated shell for file descriptor tests"""
    shell = isolated_shell_with_temp_dir
    shell.run_command('echo "test" > output.txt')
    
    with open('output.txt') as f:
        assert f.read() == "test\n"
```

#### For Conformance Tests
```python
def test_posix_feature(self):
    """Use subprocess for external comparison"""
    result = self.check_behavior('command')
    assert result.outputs_match
```

### 3. Document Best Practices

Add to CLAUDE.md:
```markdown
## Test Writing Rules

1. NEVER use capsys with tests that do I/O redirection
2. ALWAYS use captured_shell for builtin output testing  
3. PREFER subprocess.run for conformance testing
4. AVOID mixing capture methods in the same test file
```

## Medium-term Improvements

### 1. Enhanced Fixtures (2 weeks)
Create purpose-specific fixtures:
- `unit_test_shell` - Fully mocked I/O for unit tests
- `integration_test_shell` - Real file descriptors for integration
- `conformance_test_env` - Subprocess environment for comparisons

### 2. Test Reorganization (2 weeks)
Reorganize tests by I/O requirements:
```
tests/
├── unit/          # Mocked I/O tests
├── integration/   # Real I/O tests
├── system/        # Subprocess tests
└── conformance/   # Comparison tests
```

### 3. Parallel Execution Strategy
Run different test types with appropriate parallelization:
```bash
pytest tests/unit -n auto          # Full parallelization
pytest tests/integration -n 4      # Limited parallelization
pytest tests/system                # Serial execution
```

## Long-term Solutions

### 1. Alternative Test Framework
Consider shell-specific test frameworks:
- **Bats** (Bash Automated Testing System) - designed for shell testing
- **shUnit2** - xUnit-based shell testing
- Custom framework that understands file descriptors

### 2. Test Mode for PSH
Add `--test-mode` flag that:
- Provides hooks for output interception
- Disables interactive features
- Ensures deterministic behavior

### 3. Docker-based Isolation
Run each test in isolated container:
- Complete process isolation
- Clean file system
- No cross-test interference

## Expected Impact

By implementing these recommendations:

1. **Immediate** (1 week):
   - Reported bash compatibility increases from 77% to >85%
   - Test failures reduced by 50%
   - Clear guidance prevents new issues

2. **Short-term** (1 month):
   - Reliable parallel test execution
   - 95%+ test pass rate
   - Faster CI/CD cycles

3. **Long-term** (3 months):
   - Robust test infrastructure
   - Support for all shell features
   - Foundation for continuous improvement

## Conclusion

The PSH test framework issues are solvable with a systematic approach. The key insight is that **different types of tests require different approaches** - trying to force all tests into pytest's model creates unnecessary problems. By acknowledging this and providing appropriate tools for each test type, we can achieve both reliable testing and good performance.
