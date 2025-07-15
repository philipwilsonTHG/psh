# PSH Test Suite (New)

This is the reorganized test suite for PSH. It runs in parallel with the existing tests during the migration period.

## Directory Structure

### unit/
Pure unit tests for individual components in isolation:
- **lexer/**: Tokenization tests
- **parser/**: AST generation tests  
- **expansion/**: Variable and command expansion tests
- **builtins/**: Individual builtin command tests
- **utils/**: Utility function tests

### integration/
Tests for component interactions:
- **pipeline/**: Pipeline execution tests
- **redirection/**: I/O redirection tests
- **control_flow/**: if/while/for/case tests
- **functions/**: Shell function tests
- **job_control/**: Job control tests

### system/
Full system behavior tests:
- **scripts/**: Script execution tests
- **interactive/**: REPL and terminal tests
- **signals/**: Signal handling tests
- **process/**: Process management tests

### conformance/
Compatibility and standards tests:
- **posix/**: POSIX compliance tests
- **bash/**: Bash compatibility tests
- **differences/**: Documented PSH differences

### performance/
Performance and stress tests:
- **benchmarks/**: Speed benchmarks
- **memory/**: Memory usage tests
- **stress/**: Large input/load tests

### Support Directories
- **fixtures/**: Shared test fixtures
- **resources/**: Test data files
- **helpers/**: Test helper functions

## Running Tests

```bash
# Run all new tests
pytest tests_new/

# Run specific category
pytest tests_new/unit/
pytest tests_new/conformance/

# Run with coverage
pytest --cov=psh tests_new/

# Run in parallel
pytest -n auto tests_new/
```

## Writing Tests

See the test writing guide in docs/testing/writing_tests.md for:
- Test naming conventions
- Using test frameworks
- Common patterns
- Best practices