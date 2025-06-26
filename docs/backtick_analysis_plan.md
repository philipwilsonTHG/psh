# Backtick Command Substitution Analysis Plan

## Problem Statement
Backtick command substitution (`echo test`) returns literal text instead of executing commands, while `$()` substitution works correctly.

## Analysis Results

### 1. Tokenization ✅ WORKS
- Backticks are correctly tokenized as `COMMAND_SUB_BACKTICK` when standalone
- Inside quotes, they become part of `STRING` tokens (expected behavior)

### 2. Expansion System Analysis

#### ExpansionManager
- **Standalone backticks**: Handled correctly via `COMMAND_SUB_BACKTICK` case
- **Quoted backticks**: Should be handled via `expand_string_variables()` for `STRING` tokens

#### VariableExpander.expand_string_variables()
- **`$()` substitution**: ✅ Implemented (lines 539-557)
- **Backtick substitution**: ✅ Implemented (lines 591-604)

### 3. Command Substitution Execution
- `CommandSubstitution.execute()` handles both `$()` and backticks correctly
- Uses fork/pipe mechanism for both formats

## Root Cause Hypothesis

The backtick handling in `expand_string_variables()` appears to be implemented correctly. The issue may be:

1. **Logic error in backtick parsing within strings**
2. **Escape handling interfering with backtick recognition**
3. **Different code path being taken in actual execution**

## Investigation Plan

### Phase 1: Debug String Variable Expansion
1. Add detailed debug output to `expand_string_variables()` 
2. Test with both `$()` and backticks in strings
3. Verify which code paths are taken

### Phase 2: Test Standalone vs Quoted Backticks
1. Test standalone backticks: `echo` (should work via `COMMAND_SUB_BACKTICK`)
2. Test quoted backticks: `echo "test"`  (should work via string expansion)

### Phase 3: Root Cause Identification
1. Identify exact point where backtick processing fails
2. Compare with working `$()` implementation
3. Fix the specific issue

### Phase 4: Comprehensive Testing
1. Test all backtick scenarios
2. Run conformance tests to verify fix
3. Ensure no regressions in `$()` functionality

## Expected Outcome
- Backtick command substitution works identically to `$()`
- `echo "test"` returns `"backtick test"` instead of `"`echo "backtick test"`"`
- POSIX compliance improves significantly