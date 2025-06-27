# PSH Testing Strategy

## Overview

PSH uses a dual testing approach to ensure both API correctness and bash compatibility while working around pytest's output capture limitations with the visitor executor.

## Testing Approaches

### 1. Unit Tests (Direct Shell API)

**Purpose**: Test internal API, state management, and component behavior.

**When to use**:
- Testing internal state changes
- Verifying AST structure
- Testing tokenization and parsing
- Component isolation testing
- Error handling and exceptions

**Example**:
```python
def test_variable_assignment(self):
    shell = Shell()
    shell.run_command("x=42")
    assert shell.state.get_variable('x') == '42'
```

### 2. Bash Comparison Tests (Subprocess-based)

**Purpose**: Verify bash compatibility and correct output behavior.

**When to use**:
- Command substitution testing
- Pipeline behavior verification
- Output format validation
- Complex integration scenarios
- Any test that relies on captured output

**Example**:
```python
def test_command_substitution(self):
    bash_compare.assert_shells_match("echo $(echo hello)")
```

## Known Limitations

### Visitor Executor + pytest Output Capture

The visitor executor properly forks processes for external commands, but pytest's output capture mechanism doesn't work with forked processes. This affects:

1. **Command Substitution**: Output from commands in `$(...)` or `` `...` ``
2. **Pipelines**: Output from pipeline components
3. **File Redirections**: Content written to files by forked processes
4. **Background Jobs**: Output from background processes

### Mitigation Strategy

Tests affected by output capture issues are marked with `@pytest.mark.visitor_xfail`:

```python
@pytest.mark.visitor_xfail(reason="Command substitution output capture issue")
def test_command_substitution_execution(self):
    # This test will be XFAIL with visitor executor
    # but pass with legacy executor
```

## Test Organization

### Directory Structure
```
tests/
├── comparison/           # Bash compatibility tests
│   ├── bash_comparison_framework.py
│   ├── test_bash_basic_commands.py
│   ├── test_bash_command_substitution.py
│   ├── test_bash_arithmetic_expansion.py
│   ├── test_bash_pipelines.py
│   ├── test_bash_functions.py
│   └── test_bash_redirections.py
├── test_*.py            # Unit tests
└── conftest.py          # pytest configuration with visitor_xfail marker
```

### Test Categories

#### Always Use Unit Tests
- Parser tests (`test_parser.py`)
- Tokenizer tests (`test_tokenizer.py`)
- AST node tests (`test_ast_nodes.py`)
- State management tests
- Error handling tests

#### Always Use Comparison Tests
- Output format verification
- Command substitution behavior
- Pipeline output
- Complex integration scenarios

#### Can Use Either
- Simple command execution
- Variable operations
- Control structures (without output capture)

## Running Tests

### Run all tests (visitor executor is default)
```bash
pytest
```

### Run only comparison tests
```bash
pytest tests/comparison/
```

### Run only unit tests
```bash
pytest tests/ -k "not comparison"
```

## Future Improvements

1. **Test Infrastructure Update**: Modify test helpers to use subprocess for output capture
2. **Remove xfail Markers**: As issues are fixed, tests will automatically start passing (xfail → xpass)
3. **Expand Comparison Tests**: Add more bash compatibility tests for edge cases

## Guidelines for New Tests

1. **Default to Unit Tests** for internal behavior and state verification
2. **Use Comparison Tests** for output verification and bash compatibility
3. **Apply visitor_xfail** only when output capture is the issue
4. **Document Why** - Always include a reason in the xfail marker
5. **Test Both Ways** - Ensure tests work with legacy executor before marking xfail