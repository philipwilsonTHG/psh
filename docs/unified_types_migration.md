# Unified Types Migration Guide

## Overview

As of PSH v0.38.0, the old dual Statement/Command types are deprecated in favor of unified control structure types. This guide helps you migrate your code to the new unified types.

## Why Unified Types?

The old architecture had separate types for statements (executed in current shell) and commands (executed in pipelines):
- `WhileStatement` vs `WhileCommand`
- `ForStatement` vs `ForCommand`
- etc.

This led to:
- Code duplication in the parser
- Complex type hierarchies
- Confusion about which type to use

The new unified types:
- Single type for each control structure
- Execution context tracked via `ExecutionContext` enum
- Cleaner, more maintainable code

## Migration Table

| Old Statement Type | Old Command Type | New Unified Type |
|-------------------|------------------|------------------|
| `WhileStatement` | `WhileCommand` | `WhileLoop` |
| `ForStatement` | `ForCommand` | `ForLoop` |
| `CStyleForStatement` | `CStyleForCommand` | `CStyleForLoop` |
| `IfStatement` | `IfCommand` | `IfConditional` |
| `CaseStatement` | `CaseCommand` | `CaseConditional` |
| `SelectStatement` | `SelectCommand` | `SelectLoop` |
| `ArithmeticCommand` | `ArithmeticCompoundCommand` | `ArithmeticEvaluation` |

## Code Examples

### While Loop Migration

```python
# Old code
from psh.ast_nodes import WhileStatement
stmt = WhileStatement(
    condition=condition,
    body=body,
    redirects=redirects
)

# New code
from psh.ast_nodes import WhileLoop, ExecutionContext
stmt = WhileLoop(
    condition=condition,
    body=body,
    redirects=redirects,
    execution_context=ExecutionContext.STATEMENT,
    background=False
)
```

### For Loop Migration

```python
# Old code - ForStatement
from psh.ast_nodes import ForStatement
stmt = ForStatement(variable, iterable, body, redirects)

# Old code - ForCommand
from psh.ast_nodes import ForCommand
cmd = ForCommand(variable, items, body, redirects, background)

# New code - unified
from psh.ast_nodes import ForLoop, ExecutionContext
loop = ForLoop(
    variable=variable,
    items=items,  # Note: 'iterable' renamed to 'items'
    body=body,
    redirects=redirects,
    execution_context=ExecutionContext.STATEMENT,  # or PIPELINE
    background=background
)
```

### Execution Context

The `execution_context` field determines how the control structure is executed:

```python
from psh.ast_nodes import ExecutionContext

# For execution in current shell (like old Statement types)
execution_context=ExecutionContext.STATEMENT

# For execution in pipeline subshell (like old Command types)
execution_context=ExecutionContext.PIPELINE
```

## Parser Usage

### Using the Refactored Parser

```python
from psh.parser_refactored import parse
from psh.state_machine_lexer import tokenize

# Parse with unified types
tokens = tokenize("while true; do echo test; done")
ast = parse(tokens, use_unified_types=True)

# ast.items[0] will be a WhileLoop, not WhileStatement
```

### Gradual Migration

The parser supports both old and new types via a feature flag:

```python
# Use old types (default for backward compatibility)
ast = parse(tokens, use_unified_types=False)

# Use new unified types
ast = parse(tokens, use_unified_types=True)
```

## Deprecation Timeline

- **v0.38.0** (Current): Deprecation warnings added to old types
- **v0.39.0**: Internal code migrated to unified types
- **v0.40.0**: Old dual types removed

## Suppressing Warnings

During migration, you can suppress deprecation warnings:

```python
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from psh.ast_nodes import WhileStatement  # No warning shown
```

## Benefits of Migration

1. **Simpler API**: One type per control structure
2. **Explicit Context**: Clear execution context via enum
3. **Future-Proof**: Aligned with PSH's architectural improvements
4. **Better Type Safety**: Unified inheritance hierarchy

## Need Help?

- Check the test files for migration examples
- See `docs/parser_refactoring_phase3_status.md` for implementation details
- File issues on GitHub for migration problems