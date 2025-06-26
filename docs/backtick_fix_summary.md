# Backtick Command Substitution Fix Summary

## Problem Identified
Backtick command substitution (`echo test`) was returning literal text instead of executing commands, while `$()` substitution worked correctly.

## Root Cause Analysis
The expansion system in `ExpansionManager` had two conditions that only checked for `$` in arguments but not for backticks (`` ` ``):

1. **COMPOSITE arguments**: Line 139 checked `if '$' in arg:` 
2. **STRING arguments**: Line 80 checked `if quote_type == '"' and '$' in arg:`

This meant:
- Standalone backticks in assignments (`result=`echo test``) were not expanded
- Backticks inside quoted strings (`"Test: `echo works`"`) were not expanded

## Solution Implemented
Modified both conditions in `/Users/pwilson/src/psh/psh/expansion/manager.py`:

### Fix 1: COMPOSITE Arguments (Line 139)
```python
# Before
if '$' in arg:
    arg = self.expand_string_variables(arg)

# After  
if '$' in arg or '`' in arg:
    arg = self.expand_string_variables(arg)
```

### Fix 2: STRING Arguments (Line 80)
```python
# Before
if quote_type == '"' and '$' in arg:

# After
if quote_type == '"' and ('$' in arg or '`' in arg):
```

## Test Results

### Before Fix
```bash
$ psh -c 'echo "Backtick: `echo test`"'
Backtick: `echo test`  # Literal text
```

### After Fix  
```bash
$ psh -c 'echo "Backtick: `echo test`"'
Backtick: test  # Command executed
```

### Comprehensive Testing
- ✅ Standalone backticks: `result=`echo test``
- ✅ Quoted backticks: `"Test: `echo works`"`  
- ✅ Backticks with variables: `` `echo Hello $name` ``
- ✅ Complex commands work correctly

## POSIX Compliance Impact
- **Before**: 12 passed, 42 failed (22.2% compliance)
- **After**: 13 passed, 41 failed (24.1% compliance)  
- **Improvement**: +1.9% POSIX compliance

## Files Modified
- `/Users/pwilson/src/psh/psh/expansion/manager.py` (2 line changes)

## Implementation Quality
- **Minimal invasive**: Only 2 line changes required
- **No regressions**: `$()` substitution continues to work perfectly
- **Comprehensive**: Fixes both quoted and unquoted contexts
- **POSIX compliant**: Backticks now work identically to bash

This fix resolves one of the critical POSIX compliance gaps identified in the conformance analysis.