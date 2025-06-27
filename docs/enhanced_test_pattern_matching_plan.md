# Enhanced Test Pattern Matching Implementation Plan

## Problem Statement

Enhanced test statements (`[[ ]]`) are not performing shell pattern matching for the `==` and `!=` operators. Instead, they're doing simple string equality comparison, causing tests like `[[ "file.txt" == *.txt ]]` to fail when they should succeed.

## Root Cause Analysis

**Problem**: The `==` and `!=` operators in enhanced test statements should perform shell pattern matching (like `fnmatch`), not simple string equality.

**Location**: `/Users/pwilson/src/psh/psh/shell.py`, method `_evaluate_binary_test()`, lines 200-205

**Current Incorrect Behavior**:
```python
elif expr.operator == '==':
    return left == right  # String equality - WRONG
elif expr.operator == '!=':
    return left != right  # String inequality - WRONG
```

**Root Cause**: 
1. `[[ "file.txt" == *.txt ]]` currently does `"file.txt" == "*.txt"` (string equality)
2. Should do `fnmatch.fnmatch("file.txt", "*.txt")` (shell pattern matching)
3. In bash, `==` in `[[ ]]` means pattern matching, not string equality

## Current vs Expected Behavior

### Failing Test Cases

From conformance tests:
```bash
# Currently failing (returns false, should return true):
[[ "file.txt" == *.txt ]]
[[ "file-name" == *-* ]] 
[[ "test.txt" == *.txt ]]

# Currently working (returns true, should return false):  
[[ "image.png" != *.txt ]]
```

### Bash vs PSH Behavior

**Bash (correct)**:
- `[[ "file.txt" == *.txt ]]` → 0 (true) - pattern matches
- `[[ "image.png" != *.txt ]]` → 0 (true) - pattern doesn't match

**PSH (incorrect)**:
- `[[ "file.txt" == *.txt ]]` → 1 (false) - string "file.txt" ≠ "*.txt"
- `[[ "image.png" != *.txt ]]` → 0 (true) - string "image.png" ≠ "*.txt"

## Operator Distinctions

PSH needs to handle these operators correctly:

1. **`=` operator**: String equality (current behavior is correct)
2. **`==` operator**: Shell pattern matching (needs fix)
3. **`!=` operator**: Shell pattern non-matching (needs fix)  
4. **`=~` operator**: Regex matching (current behavior is correct)

## Implementation Plan

### Phase 1: Fix Binary Test Evaluation
**File**: `/Users/pwilson/src/psh/psh/shell.py`
**Method**: `_evaluate_binary_test()`
**Lines**: 200-205

**Required Changes**:
```python
# Current (incorrect):
elif expr.operator == '==':
    return left == right
elif expr.operator == '!=':
    return left != right

# Fixed (correct):
elif expr.operator == '==':
    import fnmatch
    return fnmatch.fnmatch(left, right)
elif expr.operator == '!=':
    import fnmatch
    return not fnmatch.fnmatch(left, right)
```

### Phase 2: Pattern Matching Infrastructure

**Existing Infrastructure**: PSH already uses `fnmatch.fnmatch()` correctly in:
- **Case statements**: `/Users/pwilson/src/psh/psh/visitor/executor_visitor.py` line 952
- This proves the infrastructure is available and working

**No New Infrastructure Needed**: Just need to use existing `fnmatch` module.

### Phase 3: Comprehensive Testing

**Test Cases Needed**:
1. **Basic pattern matching**: `[[ "file.txt" == *.txt ]]` → 0
2. **Pattern mismatch**: `[[ "file.doc" == *.txt ]]` → 1
3. **Negation**: `[[ "image.png" != *.txt ]]` → 0  
4. **Complex patterns**: `[[ "test123" == test* ]]` → 0
5. **Character classes**: `[[ "a" == [abc] ]]` → 0
6. **Multiple wildcards**: `[[ "file.tar.gz" == *.tar.* ]]` → 0
7. **Variable expansion**: `pattern="*.txt"; [[ "file.txt" == $pattern ]]` → 0

**Regression Testing**:
1. **String equality preserved**: `[[ "hello" = "hello" ]]` → 0
2. **Regex still works**: `[[ "test" =~ t.*t ]]` → 0
3. **All existing enhanced test functionality preserved**

### Phase 4: Edge Cases and Validation

**Edge Cases**:
1. **Empty patterns**: `[[ "test" == "" ]]`
2. **Special characters**: `[[ "test[1]" == "test[1]" ]]`
3. **Escaped patterns**: `[[ "*.txt" == \*.txt ]]`
4. **Case sensitivity**: Pattern matching should be case-sensitive

**Validation**:
- All conformance test failures for pattern matching should be resolved
- No regressions in existing enhanced test functionality

## Expected Impact

### POSIX Compliance
- Resolves multiple conformance test failures in enhanced test pattern matching
- Brings `[[ ]]` behavior in line with bash standard
- Critical for shell script compatibility

### User Experience  
- `[[ ]]` test statements will work as expected from bash experience
- Common patterns like `[[ "$file" == *.txt ]]` will work correctly
- Improved script portability from bash to PSH

### Test Results Expected

**Before Fix**:
```
Testing pattern matching:
# (no output - tests fail)
```

**After Fix**:
```
Testing pattern matching:
file.txt matches *.txt pattern
image.png does not match *.txt pattern
Dash in filename matched
Wildcard match: *.txt
```

## Risk Assessment

**Very Low Risk**:
- Small, localized change to existing method
- Uses proven `fnmatch` module already used elsewhere in PSH
- Only affects currently broken functionality
- Clear separation between `=` (string) and `==` (pattern) operators
- Preserves all other operator functionality

## Implementation Timeline

**Estimated effort**: 1-2 hours
- 30 minutes: Core implementation (simple change)
- 1 hour: Comprehensive testing and validation
- 30 minutes: Documentation and cleanup

This is a **high-value, low-complexity** fix that should significantly improve PSH's bash compatibility with minimal risk.