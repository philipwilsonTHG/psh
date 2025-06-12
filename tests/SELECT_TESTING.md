# Select Statement Testing Guide

## Overview

The `select` statement in PSH is an interactive feature that requires special handling in automated tests. This guide explains why some tests need the `pytest -s` flag and how to work with them.

## Why `pytest -s` is Required

### The Problem
- **Select is interactive**: Displays menus to stderr, reads user input from stdin
- **Pytest captures I/O**: Normal pytest runs capture stdout/stderr for test isolation
- **Stdin conflict**: Even with file redirection, pytest's output capture interferes with stdin reading

### The Solution: `pytest -s`
- **`-s`** is shortcut for **`--capture=no`**
- **Disables output capture**: Allows direct terminal/stdin access
- **Enables real interaction**: Select can read from stdin and write to stderr properly

## How to Run Select Tests

### 1. Interactive Tests (Require `-s`)
```bash
# Run all select tests
pytest -s tests/test_select_statement.py

# Run specific test  
pytest -s tests/test_select_statement.py::TestSelectStatement::test_basic_select

# With verbose output
pytest -sv tests/test_select_statement.py

# Run just one test class
pytest -s tests/test_select_statement.py::TestSelectStatement
```

### 2. Non-Interactive Tests (Work Normally)
```bash
# These work without -s flag
pytest tests/test_select_statement.py::TestSelectStatementNonInteractive
pytest tests/test_select_statement.py::TestSelectStatementDocumentation
```

## Test Structure

### `TestSelectStatement` (Interactive)
- **Requires**: `pytest -s` 
- **Tests**: Full select functionality with stdin/stderr interaction
- **Skipped by default**: To avoid blocking normal test runs
- **Coverage**: 12 comprehensive tests for all select features

### `TestSelectStatementNonInteractive` (Always Available)
- **No special requirements**: Works with normal pytest
- **Tests**: Parsing, syntax validation, basic functionality
- **Always runs**: Included in normal test suite
- **Coverage**: 3 tests for parser and syntax

### `TestSelectStatementDocumentation` (Always Available)
- **No special requirements**: Works with normal pytest  
- **Purpose**: Documents usage patterns and requirements
- **Self-documenting**: Test failure messages explain how to use select tests

## Why This Design?

### 1. **Practical Testing**
- Interactive tests validate real-world usage
- Non-interactive tests ensure parsing works
- Both are needed for complete coverage

### 2. **CI/CD Friendly**
- Normal test runs don't hang waiting for input
- Developers can run interactive tests when needed
- Automated builds skip interactive tests safely

### 3. **Clear Documentation**
- Test names and comments explain requirements
- Error messages guide users to correct usage
- This guide provides comprehensive reference

## Technical Details

### Select Implementation Flow
1. **Display menu** → stderr (numbered options)
2. **Show prompt** → stderr (PS3 variable, default "#? ")  
3. **Read input** → stdin (user selection or EOF)
4. **Set variables** → `$var` (selected item) and `$REPLY` (raw input)
5. **Execute body** → stdout (command output)

### File Redirection in Tests
```bash
# Tests use file redirection to provide predictable input
select fruit in apple banana cherry; do 
    echo "Selected: $fruit"
    break 
done < /tmp/input_file

# input_file contains: "1\n"
# This simulates user typing "1" and pressing Enter
```

### Error Without `-s`
```
psh: <command>:1: unexpected error: pytest: reading from stdin while output is captured!  Consider using `-s`.
```

## Examples

### Running Select Tests Successfully
```bash
# This works
$ pytest -s tests/test_select_statement.py::TestSelectStatement::test_basic_select
============================= test session starts ==============================
tests/test_select_statement.py::TestSelectStatement::test_basic_select PASSED [100%]

# This fails  
$ pytest tests/test_select_statement.py::TestSelectStatement::test_basic_select
tests/test_select_statement.py::TestSelectStatement::test_basic_select SKIPPED
```

### Running Non-Interactive Tests
```bash
# These always work
$ pytest tests/test_select_statement.py::TestSelectStatementNonInteractive
============================= test session starts ==============================
tests/test_select_statement.py::TestSelectStatementNonInteractive::test_select_parsing PASSED
tests/test_select_statement.py::TestSelectStatementNonInteractive::test_select_variable_initialization PASSED  
tests/test_select_statement.py::TestSelectStatementNonInteractive::test_select_syntax_variations PASSED
```

## Summary

- **Use `pytest -s`** for complete select testing
- **Non-interactive tests** provide basic coverage without special requirements
- **Both test types** are needed for full validation
- **Clear documentation** guides proper usage