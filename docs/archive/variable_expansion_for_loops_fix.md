# Variable Expansion in For Loops Fix: Implementation Plan

## Overview

This document describes the critical fix for variable expansion in for loops in PSH, which resolved a fundamental POSIX compliance issue where `for item in $items` didn't correctly expand variables.

## Problem Analysis

### Issue Description
Variable expansion in for loops was not working correctly:
```bash
# This should iterate over "apple", "banana", "cherry"
items="apple banana cherry"
for item in $items; do
    echo "Item: $item"
done

# PSH was outputting:
Item: items

# Instead of the correct bash behavior:
Item: apple
Item: banana  
Item: cherry
```

### Root Cause
The bug was located in the `_parse_for_iterable` method in `/Users/pwilson/src/psh/psh/parser.py` (lines 754-764).

**Problem**: When parsing `for item in $items`, the tokenizer correctly creates a VARIABLE token with value `'items'` (without the $). However, the parser was storing just the token value (`'items'`) instead of preserving the fact that it's a variable by including the `$` prefix.

**Impact**: The executor's `visit_ForLoop` method has sophisticated expansion logic that checks for strings starting with `$` to trigger variable expansion. Since the parser stored `'items'` instead of `'$items'`, this expansion logic was never triggered.

## Technical Details

### Original Code (Broken)
```python
# In _parse_for_iterable method (lines 754-762)
iterable = []
for token in tokens:
    if token.type in valid_types:
        iterable.append(token.value)  # Lost $ prefix for VARIABLE tokens
    else:
        break
```

### Fixed Code
```python
# In _parse_for_iterable method (lines 754-764)
iterable = []
for token in tokens:
    if token.type in valid_types:
        # For VARIABLE tokens, preserve the $ prefix for expansion
        if token.type == TokenType.VARIABLE:
            iterable.append(f"${token.value}")
        else:
            iterable.append(token.value)
    else:
        break
```

### Expansion Logic Context
The executor's `visit_ForLoop` method in `/Users/pwilson/src/psh/psh/visitor/executor_visitor.py` contains this expansion logic:

```python
def visit_ForLoop(self, node: ForLoop) -> int:
    # ... other code ...
    
    # Expand the iterable list
    expanded_items = []
    for item in node.iterable:
        if item.startswith('$'):  # ← This check was failing!
            # Variable expansion logic
            expanded = self.shell.expansion_manager.expand_variables(item)
            # Split on whitespace and add to list
            expanded_items.extend(expanded.split())
        elif item.startswith('$(') or item.startswith('`'):
            # Command substitution logic
            # ... 
        else:
            # Literal value
            expanded_items.append(item)
```

The fix ensures that VARIABLE tokens are stored as `$items` so the `item.startswith('$')` check succeeds and triggers proper variable expansion.

## Testing

### Test Cases Verified
1. ✅ **Basic variable expansion**: `for item in $items`
2. ✅ **Mixed literals and variables**: `for item in first $items last`  
3. ✅ **Multiple variables**: `for item in $start middle $end`
4. ✅ **Empty/undefined variables**: Handled gracefully (no iteration)
5. ✅ **Command substitution**: `for item in $(command)` (unchanged)
6. ✅ **Quoted strings**: `for item in "hello world"` (unchanged)
7. ✅ **Complex expressions**: Mixed types work together

### Conformance Test Impact
This fix resolves the critical failure in `conformance_tests/posix/advanced_syntax/test_loop_constructs.input`:

```bash
# Before fix:
Processed items: processed_items

# After fix:
Processed items: processed_apple processed_banana processed_cherry
```

## Implementation Impact

### POSIX Compliance
- **Critical fix**: Variable expansion in for loops is fundamental POSIX shell functionality
- **High impact**: Affects multiple conformance tests
- **Foundation**: Enables basic shell scripting patterns that rely on variable expansion

### Backward Compatibility
- ✅ **No regressions**: All existing for loop functionality preserved
- ✅ **Test suite**: All 1508+ tests continue to pass
- ✅ **API unchanged**: No changes to public interfaces

### Performance
- **Minimal overhead**: Only adds a simple string prefix check during parsing
- **No runtime impact**: Expansion logic was already present, just not triggered

## Related Files Modified

1. **`/Users/pwilson/src/psh/psh/parser.py`** - Fixed `_parse_for_iterable` method
2. **`/Users/pwilson/src/psh/psh/version.py`** - Updated to version 0.59.7 with detailed changelog

## Future Considerations

### Similar Issues
This same pattern should be verified in other contexts where VARIABLE tokens are processed:
- Case statement pattern parsing
- Array initialization 
- Other expansion contexts

### Pattern Recognition
The fix demonstrates the importance of preserving token semantic meaning through the parsing pipeline. When tokens represent expandable constructs (variables, command substitutions), their prefixes/suffixes must be preserved for the executor to recognize them correctly.

## Summary

This critical fix resolves a fundamental POSIX compliance issue by ensuring variable expansion works correctly in for loops. The solution was minimal and targeted, preserving the `$` prefix for VARIABLE tokens during parsing so the executor's expansion logic can function properly. This brings PSH significantly closer to full POSIX compliance for essential shell scripting functionality.