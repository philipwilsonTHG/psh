# Pattern Substitution Implementation Plan

## Problem Statement

Array pattern substitution operations like `${arr[@]/pattern/replacement}` are returning empty strings instead of applying pattern substitution to each array element. This is a critical POSIX compliance gap affecting multiple conformance tests.

## Root Cause Analysis

**Problem**: Array pattern substitution like `${arr[@]/pattern/replacement}` returns empty strings instead of applying pattern substitution to each array element.

**Location**: `/Users/pwilson/src/psh/psh/expansion/variable.py`, lines 315-344

**Root Cause**: 
1. The code correctly identifies `var_name = "arr[@]"` with operator `"/"` and operand `"pattern/replacement"`
2. It extracts `array_name = "arr"` and `index_expr = "@"`
3. **BUG**: At line 326, it tries to expand `"@"` as a variable, then convert to integer at line 332
4. Since `"@"` can't be converted to an integer, the except block at line 335 returns empty string
5. The pattern substitution operation is applied to this empty string, yielding empty result

## Current Status

### ✅ Working Cases
- ✅ Single element: `${arr[0]/pattern/replacement}` works (confirmed by test analysis)
- ✅ Array expansion: `${arr[@]}` works (has dedicated `expand_array_to_list` method)
- ✅ Pattern substitution on regular variables: `${var/pattern/replacement}` works

### ❌ Broken Cases  
- ❌ Array pattern substitution: `${arr[@]/pattern/replacement}` returns empty
- ❌ Array pattern substitution: `${arr[*]/pattern/replacement}` returns empty  
- ❌ All array operations: `${arr[@]#pattern}`, `${arr[@]%pattern}`, etc.

## Implementation Plan

### Phase 1: Enhance Array Parameter Expansion Detection
**File**: `/Users/pwilson/src/psh/psh/expansion/variable.py`
**Location**: Lines 315-344 (array element parameter expansion section)

**Changes needed**:
1. **Before line 326**: Add check for special indices `@` and `*`
2. **New logic**: When `index_expr` is `@` or `*`:
   - Get all array elements using existing `all_elements()` method
   - Apply the parameter expansion operation to each element  
   - Return space-separated results (for `@`) or IFS-separated results (for `*`)

### Phase 2: Reuse Existing Parameter Expansion Logic
**Architecture**: The existing `ParameterExpansion` class already has all the needed methods:
- `substitute_first(value, pattern, replacement)` 
- `substitute_all(value, pattern, replacement)`
- `remove_shortest_prefix(value, pattern)`
- etc.

**Strategy**: Apply these methods to each array element individually, then join results.

### Phase 3: Handle Both Array Types
**Support**:
- ✅ `IndexedArray` - use `all_elements()` method
- ✅ `AssociativeArray` - use `all_elements()` method  
- ✅ Regular variables treated as single-element arrays

### Phase 4: Comprehensive Testing
**Test cases needed**:
- `${arr[@]/pattern/replacement}` - replace first occurrence in each element
- `${arr[@]//pattern/replacement}` - replace all occurrences in each element  
- `${arr[@]/#pattern/replacement}` - replace prefix in each element
- `${arr[@]/%pattern/replacement}` - replace suffix in each element
- `${arr[@]#pattern}` - remove prefix from each element
- `${arr[@]%pattern}` - remove suffix from each element
- Mixed array types (indexed and associative)
- Edge cases: empty arrays, non-matching patterns

## Specific Code Changes

**In `/Users/pwilson/src/psh/psh/expansion/variable.py`** around line 315:

```python
elif '[' in var_name and var_name.endswith(']'):
    # Array element with parameter expansion
    bracket_pos = var_name.find('[')
    array_name = var_name[:bracket_pos]
    index_expr = var_name[bracket_pos+1:-1]
    
    from ..core.variables import IndexedArray, AssociativeArray
    var = self.state.scope_manager.get_variable_object(array_name)
    
    # Handle special indices @ and * for whole-array operations
    if index_expr in ('@', '*'):
        if var and isinstance(var.value, (IndexedArray, AssociativeArray)):
            elements = var.value.all_elements()
        elif var and var.value:
            # Regular variable treated as single-element array
            elements = [str(var.value)]
        else:
            elements = []
        
        # Apply parameter expansion to each element
        results = []
        for element in elements:
            # Apply the operation to this element
            if operator == '/':
                pattern, replacement = self._split_pattern_replacement(operand)
                if pattern is not None:
                    result = self.param_expansion.substitute_first(element, pattern, replacement)
                else:
                    result = element
            elif operator == '//':
                # ... similar for other operations
            # ... handle all other operators
            results.append(result)
        
        # Join results (@ uses space, * uses IFS)
        separator = ' ' if index_expr == '@' else self.state.get_variable('IFS', ' \t\n')[0:1]
        return separator.join(results)
    
    # Handle regular indexed access (existing code)
    elif var and isinstance(var.value, IndexedArray):
        # ... existing code for single element access
```

## Expected Impact

**POSIX Compliance**: This fix should resolve multiple conformance test failures related to array pattern operations, potentially improving the pass rate significantly.

**User Experience**: Array pattern substitution is a commonly used bash feature, so this fix will greatly improve real-world usability.

**Architecture**: The fix leverages existing, well-tested parameter expansion methods, minimizing risk of regressions.

## Risk Assessment

**Low Risk**: 
- Reuses existing, proven parameter expansion methods
- Only affects currently broken functionality
- Existing working cases remain unchanged
- Clear separation between new and existing code paths

## Success Criteria

1. `${arr[@]/pattern/replacement}` correctly applies substitution to each array element
2. All array parameter expansion operations work: `#`, `##`, `%`, `%%`, `/`, `//`, `/#`, `/%`
3. Both `@` and `*` indices work correctly with appropriate separators
4. Both IndexedArray and AssociativeArray types supported
5. No regressions in existing functionality
6. Conformance test pass rate improves for array pattern operations

## Implementation Timeline

This is a **high-value, medium-complexity** fix that should significantly improve PSH's bash compatibility.

**Estimated effort**: 2-3 hours
- 1 hour: Core implementation
- 1 hour: Comprehensive testing  
- 30 minutes: Documentation and cleanup