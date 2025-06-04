# Release Notes for v0.28.2

## Overview

Version 0.28.2 is a bug fix release that resolves several critical parsing and tokenization issues. This release achieves 100% test success rate with 596 tests passing.

## Major Bug Fixes

### 1. Fixed != Operator Tokenization
- **Issue**: The `!=` operator was being incorrectly split into `!` and `=` tokens
- **Impact**: Test commands like `[ "$a" != "$b" ]` would fail
- **Fix**: Added special handling to tokenize `!=` as a single WORD token

### 2. Fixed COMPOSITE Argument Variable Expansion
- **Issue**: Variables in composite arguments like `${PREFIX}fix` were not expanding correctly
- **Impact**: Echo commands like `echo ${VAR}suffix` would produce empty output
- **Fix**: Corrected expansion manager to properly handle COMPOSITE arguments with variables

### 3. Fixed PS1 Escape Sequence Handling
- **Issue**: Backslash escape sequences in PS1 were being processed incorrectly
- **Impact**: Setting `PS1="\$"` would result in `$` instead of preserving `\$`
- **Fix**: Modified lexer to preserve `\$` in double quotes for bash compatibility

### 4. Fixed Context-Sensitive Keyword Recognition
- **Issue**: Words like "done" were always treated as keywords
- **Impact**: Commands like `echo done` would fail to parse
- **Fix**: Made keyword recognition context-sensitive based on command position

### 5. Fixed Arithmetic Expansion in Double Quotes
- **Issue**: Arithmetic expansions inside double quotes had an extra closing parenthesis
- **Impact**: Commands like `echo "$((1 + 1))"` would produce incorrect output
- **Fix**: Use correct method for reading balanced double parentheses

## Technical Improvements

- Introduced new state machine lexer (`state_machine_lexer.py`) for more robust tokenization
- Updated 35 test files to use the new lexer
- Improved error messages for unclosed quotes and expansions
- Enhanced token metadata preservation for better parsing

## Migration Notes

If you have custom code that imports from `psh.tokenizer`, update your imports to:
```python
from psh.state_machine_lexer import tokenize
```

## Testing

All 596 tests now pass, providing confidence in the stability of this release. The test suite covers:
- Basic command execution
- Variable expansion
- Control structures
- I/O redirection
- Job control
- Functions and aliases
- All shell features

## Next Steps

With these critical bugs fixed, the shell is now more compatible with standard shell behavior and ready for the next phase of enhancements.