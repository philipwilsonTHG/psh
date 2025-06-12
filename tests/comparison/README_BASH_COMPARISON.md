# Bash Comparison Testing Framework

This directory contains a pytest framework for comparing PSH output with bash output to ensure compatibility and catch regressions.

## Framework Overview

The `bash_comparison_framework.py` provides a comprehensive system for:

1. **Running commands in both shells** and capturing stdout, stderr, and exit codes
2. **Normalizing outputs** to handle legitimate differences (PIDs, timestamps, paths)
3. **Comparing results** with detailed diff reporting
4. **Testing known limitations** to track progress on fixes

## Key Components

### BashComparisonFramework Class

```python
from .bash_comparison_framework import bash_compare

# Test that outputs should match
bash_compare.assert_shells_match("echo hello")

# Test known limitations (expect differences)
bash_compare.expect_shells_differ(
    "echo a'b'c", 
    reason="Tokenizer preserves quotes instead of concatenating"
)
```

### Core Methods

- `assert_shells_match(command)` - Assert PSH and bash produce identical output
- `expect_shells_differ(command, reason)` - Document known differences
- `run_in_shell(command, shell)` - Run command and capture results
- `normalize_output(output)` - Handle legitimate differences
- `compare_results(psh_result, bash_result)` - Detailed comparison

## Test Organization

### test_bash_basic_commands.py
- Basic command execution
- Control structures
- Expansions and redirections
- Builtin commands
- Bulk parametrized tests

### test_bash_parser_limitations.py
- Composite argument quote handling
- Tokenizer quote issues
- Regression checks
- Performance comparisons

## Output Normalization

The framework automatically normalizes:

- **Process IDs**: `12345` → `PID`
- **Job IDs**: `[1]` → `[JOB]`
- **Timestamps**: `12:34:56` → `TIME`
- **Temp paths**: `/tmp/tmpXXX` → `/tmp/TEMP`
- **Error message prefixes**: Different shell names normalized

## Usage Examples

### Basic Compatibility Test

```python
def test_echo_commands():
    bash_compare.assert_shells_match("echo hello")
    bash_compare.assert_shells_match("echo $((2+3))")
```

### Testing Known Limitations

```python
def test_quote_concatenation():
    bash_compare.expect_shells_differ(
        "echo a'b'c",
        reason="Tokenizer includes quotes in output"
    )
```

### With Custom Options

```python
def test_with_timeout():
    bash_compare.assert_shells_match(
        "sleep 1; echo done",
        timeout=5.0
    )

def test_with_environment():
    bash_compare.assert_shells_match(
        "echo $CUSTOM_VAR",
        env={"CUSTOM_VAR": "test_value"}
    )
```

## Running Tests

```bash
# Run all comparison tests
pytest tests/comparison/ -v

# Run specific test file
pytest tests/comparison/test_bash_basic_commands.py -v

# Run with output capture disabled (for debugging)
pytest tests/comparison/ -v -s

# Run only tests that expect differences
pytest tests/comparison/ -v -k "expect_shells_differ"
```

## Benefits

### 1. Compatibility Assurance
- Ensures PSH behaves like bash for standard cases
- Catches regressions when making changes
- Validates new features against bash behavior

### 2. Documentation of Limitations
- `expect_shells_differ()` documents known issues
- Provides concrete examples of limitations
- Tracks progress on fixing issues

### 3. Regression Testing
- Any working feature that suddenly differs from bash triggers a test failure
- Prevents accidentally breaking compatibility