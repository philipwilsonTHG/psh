# Enhanced Test Operators Implementation Context

## Summary

This document captures the context from our discussion about implementing Enhanced String Test Operators in psh.

## Current Status

We've analyzed the requirements for implementing Enhanced String Test Operators as listed in TODO.md:
- `STRING1 < STRING2` - Lexicographic string comparison (in [[ ]])
- `STRING1 > STRING2` - Lexicographic string comparison (in [[ ]])
- `STRING =~ REGEX` - Pattern matching with regular expressions (in [[ ]])

## Architectural Plan

A comprehensive implementation plan has been saved to `/Users/pwilson/src/psh/docs/enhanced_test_operators_plan.md` which includes:

### 1. Tokenizer Changes
- New tokens: DOUBLE_LBRACKET, DOUBLE_RBRACKET, REGEX_MATCH
- Context-aware tokenization (< and > as operators inside [[]], not redirections)

### 2. Parser Changes
- New AST nodes:
  - EnhancedTestStatement
  - TestExpression hierarchy (Binary, Unary, Compound, Negated)
- Parse test expressions with proper operator precedence

### 3. Execution Changes
- execute_enhanced_test_statement() method
- _evaluate_test_expression() with pattern matching
- Regex support using Python's re module
- Lexicographic string comparison

### 4. Key Implementation Notes
- The `[[ ]]` construct provides enhanced features over `[`
- No word splitting inside `[[ ]]` (safer variable handling)
- Pattern matching on right-hand side of = and !=
- Context tracking needed to distinguish operators from redirections

## Next Steps

With the architectural plan saved, the implementation can proceed in phases:
1. Basic `[[ ]]` parsing and execution
2. New operators (< , >, =~)
3. Advanced features (compound expressions, pattern matching)

## Related Files
- `/Users/pwilson/src/psh/TODO.md` - Requirements (lines 83-87)
- `/Users/pwilson/src/psh/docs/enhanced_test_operators_plan.md` - Full implementation plan
- `/Users/pwilson/src/psh/psh/builtins/test_command.py` - Current test command
- `/Users/pwilson/src/psh/psh/tokenizer.py` - Tokenizer to extend
- `/Users/pwilson/src/psh/psh/ast_nodes.py` - AST nodes to add