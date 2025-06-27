# Array Improvements Plan - POSIX Compliance & Bug Fixes

## Problem Analysis

Based on conformance test analysis and codebase examination, PSH has a solid array foundation but several critical execution bugs prevent POSIX compliance.

### Current Issues Identified

1. **Array Initialization with Explicit Indices** ❌
   ```bash
   # Expected: zero two five  
   # Actual:   [0]=zero [2]=two [5]=five
   arr=([0]=zero [2]=two [5]=five)
   ```

2. **Mixed Array Initialization** ❌ 
   ```bash
   # Expected: first fourth fifth eleventh
   # Actual:   first [3]=fourth fifth [10]=eleventh  
   arr=(first [3]=fourth fifth [10]=eleventh)
   ```

3. **Array Element Access with Subscripts** ❌
   ```bash
   # Expected: 2025, 06, 25
   # Actual:   2025 06 25 12 00 00, , 
   date_parts=($(echo "2025 06 25 12 00 00"))
   echo "Year: ${date_parts[0]}, Month: ${date_parts[1]}, Day: ${date_parts[2]}"
   ```

4. **Read Builtin Array Assignment** ❌
   ```bash
   # Expected: apple banana cherry
   # Actual:   (empty array)
   IFS=',' read -ra fruit_array <<< "apple,banana,cherry"
   ```

5. **Brace Expansion in Array Assignment** ❌
   ```bash
   # Expected: a b c d e 1 2 3
   # Actual:   (empty array)
   brace_array=({a..e} {1..3})
   ```

### Root Cause Analysis

1. **Execution Bug**: Array initialization parser creates correct AST but executor doesn't handle explicit indices properly
2. **Read Builtin**: Missing `-a` array option support  
3. **Expansion Integration**: Array assignments not properly integrating with brace expansion
4. **Index Evaluation**: Explicit index syntax `[n]=value` not being evaluated during execution

## Implementation Plan

### Phase 1: Core Array Assignment Execution Fix (HIGH PRIORITY)
**Target**: Fix explicit index and mixed array initialization

**Problem**: The parser correctly creates `ArrayInitialization` nodes with `ArrayElement` entries, but the executor in `visitor/executor_visitor.py` isn't properly handling explicit indices.

**Files to Modify**:
- `psh/visitor/executor_visitor.py` (lines ~1350-1400)
- `psh/ast_nodes.py` (validate ArrayElement structure)

**Changes Required**:
1. **Fix `visit_ArrayInitialization()`**: 
   - Distinguish between simple elements and indexed elements
   - For `ArrayElement` nodes with indices, evaluate the index and use it
   - For simple values, use sequential indexing

2. **Enhance `_process_array_elements()`**:
   - Handle both `str` (simple) and `ArrayElement` (indexed) types
   - Properly evaluate arithmetic expressions in indices
   - Support mixed initialization patterns

### Phase 2: Read Builtin Array Support (HIGH PRIORITY)  
**Target**: Implement `read -a` and `read -ra` for array assignment

**Problem**: Read builtin doesn't support array assignment options.

**Files to Modify**:
- `psh/builtins/core.py` (ReadBuiltin class)

**Changes Required**:
1. **Add array options to ReadBuiltin**:
   - `-a array_name`: Read into indexed array
   - `-ra array_name`: Read into array with raw mode (no backslash escaping)

2. **Implement array reading logic**:
   - Split input based on IFS
   - Create array assignment with proper indexing
   - Support both normal and raw modes

### Phase 3: Brace Expansion Integration (MEDIUM PRIORITY)
**Target**: Fix brace expansion in array assignments

**Problem**: Brace expansion may not be properly applied before array parsing.

**Files to Modify**:
- `psh/visitor/executor_visitor.py` (array assignment handling)
- `psh/expansion/manager.py` (ensure brace expansion in assignment context)

**Changes Required**:
1. **Ensure brace expansion in array context**:
   - Verify brace expansion runs before array assignment parsing
   - Test with both simple and complex brace patterns

### Phase 4: Array Element Access Improvements (MEDIUM PRIORITY)
**Target**: Fix array element access in complex expressions

**Problem**: Array indexing in parameter expansion contexts may have edge cases.

**Files to Modify**:
- `psh/expansion/variable.py` (array expansion logic)

**Changes Required**:
1. **Enhanced array subscript evaluation**:
   - Better error handling for invalid indices
   - Improved arithmetic evaluation in array contexts

### Phase 5: Edge Case Handling & Performance (LOW PRIORITY)
**Target**: Handle remaining edge cases and optimize performance

**Areas to Address**:
1. **Error handling improvements**
2. **Memory optimization for large sparse arrays** 
3. **Better debugging output for array operations**
4. **Associative array edge cases**

## Success Criteria

### Phase 1 Success:
```bash
✅ arr=([0]=zero [2]=two [5]=five)     # → zero two five
✅ echo "${!arr[@]}"                   # → 0 2 5  
✅ arr=(first [3]=fourth fifth)        # → first fourth fifth
✅ echo "${!arr[@]}"                   # → 0 3 4
```

### Phase 2 Success:
```bash
✅ IFS=',' read -ra fruit <<< "a,b,c"  # → fruit=(a b c)
✅ echo "data" | read -a words         # → words=(data)
```

### Phase 3 Success:
```bash
✅ arr=({a..e} {1..3})                 # → a b c d e 1 2 3
✅ arr=({red,green,blue})              # → red green blue
```

### Phase 4 Success:
```bash
✅ date_parts=($(echo "2025 06 25"))   
✅ echo "${date_parts[1]}"             # → 06
```

## Expected Impact

**Before Fix**: ~25.9% POSIX compliance (14/54 tests pass)
**After Fix**: ~30-35% POSIX compliance (16-19/54 tests pass)

**Tests Likely to Pass**:
- `test_array_assignment.input` (currently failing)
- Several array-related sections in other tests
- Improved shell script compatibility for array usage

## Implementation Timeline

- **Phase 1**: 90 minutes - Core array assignment execution fix
- **Phase 2**: 60 minutes - Read builtin array support  
- **Phase 3**: 45 minutes - Brace expansion integration
- **Phase 4**: 45 minutes - Element access improvements
- **Total**: ~4 hours for complete array compliance improvement

## Risk Assessment

**Low Risk**: 
- All changes are in well-defined subsystems
- Comprehensive test suite exists to prevent regressions
- Parser infrastructure already correct

**Medium Risk**:
- Complex interaction between expansion and array assignment
- Need to maintain backward compatibility

**Mitigation**:
- Incremental implementation with testing after each phase
- Focus on execution bugs rather than architectural changes
- Leverage existing robust parser and AST infrastructure

This plan addresses the highest-impact POSIX compliance gaps while building on PSH's already solid array architecture.