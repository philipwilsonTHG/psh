# Command Substitution in Arithmetic Expressions - Implementation Plan

## Overview

Currently, psh's arithmetic parser doesn't support command substitution within arithmetic expressions. This document outlines a plan to enable expressions like `$(($(get_number) * 2))` to work correctly.

## Problem Statement

The arithmetic parser (`arithmetic.py`) only recognizes:
- Numbers (decimal, hex, octal)
- Variable names (without `$` prefix)
- Operators and parentheses

When it encounters `$(...)` within an arithmetic expression, it fails with a syntax error because `$` is not a recognized character.

### Example of the Issue

```bash
# This works:
get_number() { echo 5; }
result=$(get_number)
echo $((result * 2))  # Output: 10

# This fails:
echo $(($(get_number) * 2))  # Error: Unexpected character '$'
```

## Proposed Solution: Pre-expansion Approach

The recommended approach is to expand command substitutions before passing the expression to the arithmetic parser. This keeps the arithmetic parser simple and reuses existing infrastructure.

### Implementation Steps

#### 1. Modify `execute_arithmetic_expansion()` in `expansion/manager.py`

```python
def execute_arithmetic_expansion(self, expr: str) -> int:
    """Execute arithmetic expansion and return result."""
    # Remove $(( and ))
    if expr.startswith('$((') and expr.endswith('))'):
        arith_expr = expr[3:-2]
    else:
        return 0
    
    # Pre-expand command substitutions in the arithmetic expression
    arith_expr = self._expand_command_subs_in_arithmetic(arith_expr)
    
    from ..arithmetic import evaluate_arithmetic, ArithmeticError
    
    try:
        result = evaluate_arithmetic(arith_expr, self.shell)
        return result
    except ArithmeticError as e:
        import sys
        print(f"psh: arithmetic error: {e}", file=sys.stderr)
        return 0
```

#### 2. Add Helper Method for Command Substitution Expansion

```python
def _expand_command_subs_in_arithmetic(self, expr: str) -> str:
    """Expand command substitutions in arithmetic expression.
    
    This method finds all $(...) patterns in the arithmetic expression
    and replaces them with their evaluated output before arithmetic
    evaluation.
    
    Args:
        expr: The arithmetic expression potentially containing $(...)
        
    Returns:
        The expression with all command substitutions expanded
    """
    result = []
    i = 0
    
    while i < len(expr):
        if expr[i] == '$' and i + 1 < len(expr) and expr[i + 1] == '(':
            # Found potential command substitution
            # Find matching closing parenthesis
            paren_count = 1
            j = i + 2
            
            while j < len(expr) and paren_count > 0:
                if expr[j] == '(':
                    paren_count += 1
                elif expr[j] == ')':
                    paren_count -= 1
                j += 1
            
            if paren_count == 0:
                # Valid command substitution found
                cmd_sub_expr = expr[i:j]  # Include $(...) 
                
                # Execute command substitution
                output = self.command_sub.execute(cmd_sub_expr).strip()
                
                # Convert empty output to 0 (bash behavior)
                result.append(output if output else '0')
                i = j
                continue
        
        # Not a command substitution, copy character as-is
        result.append(expr[i])
        i += 1
    
    return ''.join(result)
```

#### 3. Handle Edge Cases

The implementation should handle:

1. **Nested command substitutions**:
   ```bash
   $(($(echo $(echo 5)) * 2))  # Should evaluate to 10
   ```

2. **Multiple command substitutions**:
   ```bash
   $(($(echo 3) + $(echo 4)))  # Should evaluate to 7
   ```

3. **Command substitutions with arithmetic inside**:
   ```bash
   $(($(echo $((2+3))) * 2))  # Should evaluate to 10
   ```

4. **Invalid command output**:
   ```bash
   $(($(echo "hello") * 2))  # Should treat "hello" as 0
   ```

## Alternative Approach: Extend Arithmetic Parser

While not recommended, we could extend the arithmetic parser itself to handle command substitution. This would require:

1. Adding a `COMMAND_SUB` token type
2. Implementing command substitution tokenization
3. Adding a `CommandSubNode` AST node
4. Updating the parser to handle command substitution tokens
5. Updating the evaluator to execute commands and convert output

This approach is more complex and creates circular dependencies between the arithmetic and command substitution systems.

## Testing Plan

### Unit Tests

1. **Basic command substitution in arithmetic**:
   ```python
   def test_arithmetic_with_command_substitution(self, shell):
       shell.run_command('get_number() { echo 42; }')
       shell.run_command('result=$(($(get_number) * 2))')
       assert shell.variables['result'] == '84'
   ```

2. **Nested command substitutions**:
   ```python
   def test_nested_command_sub_in_arithmetic(self, shell):
       shell.run_command('inner() { echo 5; }')
       shell.run_command('outer() { echo $(inner); }')
       shell.run_command('result=$(($(outer) + 3))')
       assert shell.variables['result'] == '8'
   ```

3. **Multiple command substitutions**:
   ```python
   def test_multiple_command_subs_in_arithmetic(self, shell):
       shell.run_command('get_a() { echo 10; }')
       shell.run_command('get_b() { echo 20; }')
       shell.run_command('result=$(($(get_a) + $(get_b)))')
       assert shell.variables['result'] == '30'
   ```

4. **Error handling**:
   ```python
   def test_non_numeric_command_output(self, shell):
       shell.run_command('get_text() { echo "hello"; }')
       shell.run_command('result=$(($(get_text) + 5))')
       assert shell.variables['result'] == '5'  # "hello" treated as 0
   ```

### Integration Tests

Test with real-world examples:

```bash
# Factorial using command substitution
factorial() {
    n=$1
    if [ $n -le 1 ]; then
        echo 1
    else
        echo $((n * $(factorial $((n - 1)))))
    fi
}

result=$(($(factorial 5) * 2))  # Should be 240
```

## Implementation Priority

**Medium Priority** - This is a useful feature for advanced scripting but not critical for basic shell functionality. The workaround (using intermediate variables) is straightforward.

## Backward Compatibility

This change is fully backward compatible. Existing arithmetic expressions without command substitution will continue to work unchanged.

## Performance Considerations

Pre-expanding command substitutions adds a string scanning pass before arithmetic evaluation. The performance impact should be minimal for typical expressions, but deeply nested substitutions could add overhead.

## Documentation Updates

1. Update `CLAUDE.md` to note that arithmetic expansion supports command substitution
2. Update `TODO.md` to move this from "Known Issues" to completed features
3. Add examples to the arithmetic expansion documentation

## Summary

The pre-expansion approach provides a clean solution that:
- Reuses existing command substitution infrastructure
- Keeps the arithmetic parser simple and focused
- Avoids circular dependencies
- Matches likely bash implementation strategy
- Is easier to test and maintain

This implementation would bring psh closer to full bash compatibility for arithmetic expressions.