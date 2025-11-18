# Lexer Compatibility Issues

This document tracks the compatibility issues found between StateMachineLexer and ModularLexer during integration testing.

## Summary

The ModularLexer is not yet fully compatible with StateMachineLexer. Several key differences were found:

## Issues Found

### 1. Context-Sensitive Operators
- **Issue**: `]]` not recognized as DOUBLE_RBRACKET when inside `[[ ]]`
- **Example**: `[[ -f file ]]` - the closing `]]` is tokenized as WORD instead of DOUBLE_RBRACKET
- **Root Cause**: ModularLexer's context tracking for bracket_depth may not be updating correctly

### 2. Variable Expansion in Quotes
- **Issue**: Variables inside double quotes lose the `$` prefix
- **Example**: `"quotes with $VAR expansion"` becomes `"quotes with VAR expansion"`
- **Root Cause**: Expansion parser may be stripping the `$` when creating token values

### 3. Token Granularity Differences
- **Issue**: Different tokenization of combined text and variables
- **Example**: `text$VAR` produces 1 composite token (WORD with parts) in old lexer, 2 tokens (WORD + VARIABLE) in new
- **Root Cause**: ModularLexer doesn't create composite tokens for adjacent elements
- **Impact**: Parser may need adjustment to handle both patterns
- **Resolution**: This is an architectural difference that may be acceptable if the parser can handle both

### 4. Context-Sensitive Keywords
- **Issue**: `in` not recognized as keyword in for loops
- **Example**: `for i in 1 2 3` - `in` tokenized as WORD instead of IN
- **Root Cause**: Keyword recognizer may not have proper context tracking for for loops

### 5. Escape Sequence Handling
- **Issue**: Backslash handling differs
- **Example**: `\$VAR` produces different token sequences
- **Root Cause**: Different escape handling between lexers

### 6. Error Handling
- **Issue**: Unclosed quotes handled differently
- **Example**: Single `"` causes LexerError in old lexer, but ModularLexer handles it gracefully
- **Root Cause**: Different error recovery strategies

## Resolution Strategy

### Short Term (For Integration)
1. Fix critical issues that affect functionality:
   - Context tracking for `[[ ]]` and keywords
   - Variable expansion in quotes preserving `$`
   - Escape sequence handling

2. Document acceptable differences:
   - Token granularity (can be handled by parser)
   - Error recovery behavior (improvement)

### Long Term
1. Decide on preferred behavior for each difference
2. Update tests to reflect new expected behavior
3. Ensure parser can handle both token patterns

## Next Steps

1. Fix ModularLexer context tracking
2. Update expansion parser to preserve variable syntax
3. Add more comprehensive compatibility tests
4. Create migration guide for any intentional changes