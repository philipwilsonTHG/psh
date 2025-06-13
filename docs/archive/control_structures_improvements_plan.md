# Control Structures Improvements Plan

## Overview

Based on the comparison test results, psh has improved from 68.5% to 74.1% pass rate on control structures. This document outlines the architectural changes needed to improve bash compatibility and reach near 100% pass rate.

## Progress Update (2025-02-06)

### Completed in v0.26.2:
- ✅ **NOT operator (!)** - Phase 1.2 implemented
  - Command negation: `! command` inverts exit status
  - Test negation: `[ ! condition ]` works correctly
  - Pass rate improved from 68.5% to 70.4% (+1 test)
  
- ✅ **elif support** - Phase 1.1 implemented
  - Full elif/then chains with multiple conditions
  - Proper short-circuit evaluation
  - Pass rate improved from 70.4% to 74.1% (+2 tests)

## Failed Tests Analysis

### 1. ✅ elif Support (2 failures) - COMPLETED
**Current State**: Full elif support implemented
**Result**: Both elif tests now pass

### 2. ✅ NOT Operator (1 failure) - COMPLETED
**Current State**: Full NOT operator support implemented
**Result**: Command negation and test negation both work

### 3. While Read Pattern (1 failure)
**Current State**: Complex while read with here-strings fails parsing
**Required**: Better handling of `while read var; do ... done <<< "data"`

### 4. For Loop Enhancements (6 failures)
**Current State**: 
- No inline brace expansion: `for i in {1..5}`
- Issues with break/continue containing conditions
- Variable expansion problems

**Required**:
- Brace expansion in for loop iterables
- Complex break/continue statements
- Proper variable expansion in for lists

### 5. Case Statement Issues (3 failures)
**Current State**: 
- ;& and ;;& work but cause bash syntax errors (version mismatch?)
- Command substitution in case expressions fails

**Required**:
- Version detection for fallthrough operators
- Command substitution in case expressions

### 6. Break with Level (1 failure)
**Current State**: break only exits innermost loop
**Required**: `break N` to exit N levels of nested loops

### 7. Error Messages (2 failures)
**Current State**: Different wording than bash
**Required**: Match bash error messages exactly

## Implementation Plan

### Phase 1: Parser and AST Extensions (High Priority)

#### 1.1 elif Support
```python
# Extend ast_nodes.py
class ElifClause:
    def __init__(self, condition: CommandList, then_part: CommandList):
        self.condition = condition
        self.then_part = then_part

class IfStatement:
    def __init__(self, condition, then_part, elif_clauses=None, else_part=None):
        self.condition = condition
        self.then_part = then_part
        self.elif_clauses = elif_clauses or []  # List of ElifClause
        self.else_part = else_part
        self.redirects = []
```

**Parser Changes**:
- Add ELIF token to tokenizer
- Modify parse_if_statement to handle multiple elif clauses
- Update execution to evaluate elif conditions in sequence

#### 1.2 NOT Operator Support
```python
# Two contexts to handle:
# 1. Command negation: ! command
# 2. Test negation: [ ! -f file ]

# Add to parser.py
def parse_pipeline(self):
    # Check for leading !
    if self.current_token_is(TokenType.EXCLAMATION):
        self.advance()  # Skip !
        pipeline = self.parse_basic_pipeline()
        pipeline.negated = True
        return pipeline
```

**Execution Changes**:
- Invert exit status when pipeline.negated is True
- Add ! handling to test command for condition negation

### Phase 2: For Loop Enhancements (High Priority)

#### 2.1 Inline Brace Expansion
```python
# Modify parser.py parse_for_statement
def parse_for_statement(self):
    # ... existing code ...
    
    # After getting iterable tokens, check for brace patterns
    iterable_words = []
    for token in iterable_tokens:
        if token.type == TokenType.WORD and '{' in token.value:
            # Apply brace expansion to the token
            expanded = self.expand_braces_inline(token.value)
            iterable_words.extend(expanded)
        else:
            iterable_words.append(token)
```

#### 2.2 Complex Break/Continue
The issue is that break/continue with conditions like:
```bash
for i in 1 2 3; do
    if [ "$i" = "2" ]; then break; fi
done
```

This already works in psh. The failing tests might have syntax we don't support yet.

### Phase 3: Advanced Features (Medium Priority)

#### 3.1 Break with Level
```python
# Extend ast_nodes.py
class BreakStatement:
    def __init__(self, level=1):
        self.level = level  # Default 1, can be N for break N

# Modify parser to accept numeric argument
def parse_break_statement(self):
    self.advance()  # Skip 'break'
    level = 1
    if self.current_token and self.current_token.type == TokenType.WORD:
        if self.current_token.value.isdigit():
            level = int(self.current_token.value)
            self.advance()
    return BreakStatement(level)

# Modify LoopBreak exception
class LoopBreak(Exception):
    def __init__(self, level=1):
        self.level = level
        super().__init__(f"Break {level} levels")
```

**Execution Changes**:
- Track loop nesting depth
- Decrement break level as it propagates up
- Stop when level reaches 0

#### 3.2 Command Substitution in Case
```bash
case $(command) in
    pattern) ... ;;
esac
```

This requires fixing the parser to properly handle command substitution tokens after 'case'.

### Phase 4: Compatibility Fixes (Low Priority)

#### 4.1 Error Message Matching
Update error messages to match bash exactly:
- "only meaningful in a \`for', \`while', or \`until' loop"
- Add backticks around keywords
- Mention 'until' even though we don't support it

#### 4.2 Version-Aware Fallthrough
The ;& and ;;& operators work in psh but fail in the test's bash. This might be because:
- Older bash versions don't support these
- The test runner uses sh instead of bash

Solution: Document this as a bash version compatibility issue.

## Implementation Order

1. **elif support** (Phase 1.1) - Most impactful, enables complex conditionals
2. **NOT operator** (Phase 1.2) - Common pattern, relatively easy
3. **Inline brace expansion in for** (Phase 2.1) - Useful feature
4. **Break with level** (Phase 3.1) - Less common but important for nested loops
5. **Command substitution in case** (Phase 3.2) - Edge case but should work
6. **Error message fixes** (Phase 4.1) - Cosmetic but improves compatibility

## Testing Strategy

1. Add unit tests for each new feature
2. Update existing tests that might be affected
3. Run comparison tests after each phase
4. Target 85%+ pass rate after Phase 1-2
5. Target 95%+ pass rate after all phases

## Estimated Effort

- Phase 1: 2-3 hours (elif is the most complex)
- Phase 2: 1-2 hours (mostly parser work)
- Phase 3: 2-3 hours (break levels need careful implementation)
- Phase 4: 30 minutes (simple text changes)

Total: 6-8 hours of implementation work

## Educational Value

These improvements maintain psh's educational purpose by:
1. Showing how real shells handle complex control flow
2. Demonstrating parser evolution for new syntax
3. Teaching about compatibility considerations
4. Illustrating exception-based control flow (break N)

## Backward Compatibility

All changes are additive - existing scripts will continue to work:
- elif is optional in if statements
- ! is a new operator
- break still works without level argument
- Existing for loops unchanged

## Success Metrics

- Pass rate on control structures tests > 90%
- All existing tests continue to pass
- New features have comprehensive test coverage
- Code remains readable and educational