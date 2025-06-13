# Test Migration Guide for Unified Types

## Overview

This guide explains how to migrate existing tests to support both legacy and unified control structure types.

## Migration Strategy

### 1. Parametrized Tests (Recommended)

Use pytest parametrization to run tests with both type systems:

```python
import pytest
from psh.parser import parse as parse_legacy
from psh.parser_refactored import parse as parse_refactored

@pytest.mark.parametrize("use_unified,expected_type", [
    (False, WhileStatement),
    (True, WhileLoop),
])
def test_while_loop_type(use_unified, expected_type):
    code = "while true; do echo test; done"
    tokens = tokenize(code)
    
    if use_unified:
        ast = parse_refactored(tokens, use_unified_types=True)
    else:
        ast = parse_legacy(tokens)
    
    assert isinstance(ast.items[0], expected_type)
```

### 2. Helper Functions

Use the provided helper functions:

```python
from tests.helpers.unified_types_helper import parse_with_unified_types

def test_control_structure():
    # Parse with unified types
    ast = parse_with_unified_types("while true; do break; done", use_unified=True)
    
    # Parse with legacy types
    ast = parse_with_unified_types("while true; do break; done", use_unified=False)
```

### 3. Type Mapping

| Legacy Statement Type | Legacy Command Type | Unified Type |
|----------------------|-------------------|--------------|
| WhileStatement | WhileCommand | WhileLoop |
| ForStatement | ForCommand | ForLoop |
| CStyleForStatement | CStyleForCommand | CStyleForLoop |
| IfStatement | IfCommand | IfConditional |
| CaseStatement | CaseCommand | CaseConditional |
| SelectStatement | SelectCommand | SelectLoop |
| ArithmeticCommand | ArithmeticCommand | ArithmeticEvaluation |

### 4. Execution Context

Unified types include an `execution_context` field:
- `ExecutionContext.STATEMENT`: Execute in current shell
- `ExecutionContext.PIPELINE`: Execute in subshell

### 5. Migration Checklist

- [ ] Add imports for both legacy and unified types
- [ ] Add imports for parse functions (legacy and refactored)
- [ ] Parametrize tests that check AST types
- [ ] Update type assertions to handle both variants
- [ ] Test execution context for unified types
- [ ] Ensure backward compatibility

## Example Migration

### Before (Legacy Only)

```python
def test_while_statement():
    tokens = tokenize("while true; do echo test; done")
    ast = parse(tokens)
    assert isinstance(ast.items[0], WhileStatement)
```

### After (Supporting Both)

```python
@pytest.mark.parametrize("use_unified", [False, True])
def test_while_statement(use_unified):
    tokens = tokenize("while true; do echo test; done")
    
    if use_unified:
        ast = parse_refactored(tokens, use_unified_types=True)
        assert isinstance(ast.items[0], WhileLoop)
        assert ast.items[0].execution_context == ExecutionContext.STATEMENT
    else:
        ast = parse_legacy(tokens)
        assert isinstance(ast.items[0], WhileStatement)
```

## Running Migrated Tests

```bash
# Run with legacy types (default)
pytest tests/test_control_structures_unified.py

# Run with unified types enabled
pytest tests/test_control_structures_unified.py --unified-types

# Run specific parametrized test variants
pytest tests/test_control_structures_unified.py -k "legacy"
pytest tests/test_control_structures_unified.py -k "unified"
```