# Visitor Pattern Phase 1 Integration: Debug AST

## Overview

As part of the gradual integration strategy for the visitor pattern, we've successfully completed Phase 1 by reimplementing the `--debug-ast` functionality using the visitor pattern.

## What Was Changed

### 1. Created DebugASTVisitor

Replaced the static `ASTFormatter` utility with a visitor-based implementation:

```python
from psh.visitor import DebugASTVisitor

# Old way (static formatter)
from psh.utils.ast_formatter import ASTFormatter
print(ASTFormatter.format(ast))

# New way (visitor pattern)
debug_visitor = DebugASTVisitor()
print(debug_visitor.visit(ast))
```

### 2. Updated Shell Integration

Modified `shell.py` to use the visitor when `--debug-ast` is enabled:

```python
if self.debug_ast:
    print("=== AST Debug Output ===", file=sys.stderr)
    from .visitor import DebugASTVisitor
    debug_visitor = DebugASTVisitor()
    print(debug_visitor.visit(ast), file=sys.stderr)
    print("======================", file=sys.stderr)
```

## Benefits Achieved

### 1. **Better Maintainability**
- Each AST node type has its own `visit_*` method
- No more giant if/elif chains
- Easy to add support for new node types

### 2. **Type Safety**
- The visitor pattern provides compile-time type checking
- Return type is consistently `str` for all visit methods

### 3. **Extensibility**
- Can easily create variations (verbose, compact, JSON formatters)
- Can compose with other visitors for combined operations

### 4. **Testing**
- Isolated unit tests for the debug visitor
- No need to test through the entire shell pipeline

### 5. **Consistency**
- Follows the same pattern as other visitors (Formatter, Validator)
- Developers familiar with one visitor can easily understand others

## Backward Compatibility

The output format remains essentially the same, ensuring:
- Scripts that parse debug output continue to work
- User expectations are met
- Documentation remains accurate

## Example Output

```bash
$ psh --debug-ast -c 'if [ -f file.txt ]; then echo "Found"; fi'
=== AST Debug Output ===
TopLevel:
  IfConditional (Pipeline):
    Condition:
      CommandList:
        AndOrList:
          Pipeline:
            SimpleCommand: [ -f file.txt ]
    Then:
      CommandList:
        AndOrList:
          Pipeline:
            SimpleCommand: echo Found
======================
```

## Performance Impact

- Minimal overhead from virtual method dispatch
- Only active when `--debug-ast` is enabled
- No impact on normal shell operation

## Next Steps

With the successful Phase 1 integration, we can consider:

1. **Phase 2**: Implement more analysis visitors
   - Performance profiler visitor
   - Security audit visitor
   - Optimization suggestion visitor

2. **Enhance DebugASTVisitor**:
   - Add options for different verbosity levels
   - Support JSON output format
   - Color-coded output for terminals

3. **Continue Integration**:
   - Replace other static utilities with visitors
   - Gradually refactor executor components

## Conclusion

The Phase 1 integration demonstrates that the visitor pattern can be successfully integrated into PSH without disrupting existing functionality. The debug AST feature now benefits from better architecture while maintaining full backward compatibility.