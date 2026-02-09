# PSH Test Suite

> [!IMPORTANT]
> Current canonical test commands for contributors and CI are in `docs/testing_source_of_truth.md`.

This directory contains the active PSH test suite.

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
# Canonical quick suite
python run_tests.py --quick

# Full suite via smart runner
python run_tests.py

# Focused manual runs
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/conformance/
python -m pytest tests/integration/subshells/ -s
```

## Writing Tests

See the test writing guide in docs/testing/writing_tests.md for:
- Test naming conventions
- Using test frameworks
- Common patterns
- Best practices
