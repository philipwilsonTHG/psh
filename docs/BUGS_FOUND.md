# PSH Bugs Found During Test Migration

This document lists bugs discovered during the test migration effort.

## Fixed Bugs

### 1. Test Builtin - Missing Error Messages [FIXED]

**Fixed in commit**: 0d95925

**Description**: The test/[ builtin didn't print error messages for invalid operators.

**Fix**: Added error messages by passing shell object through to evaluation methods.

### 2. Jobs Builtin - Incorrect -p Option [FIXED]

**Fixed in commit**: 9c3a1c5

**Description**: `jobs -p` showed full job information instead of just PIDs.

**Fix**: Added option parsing to jobs builtin to handle -p flag correctly.

### 3. Readonly Builtin - Invalid Variable Names [FIXED]

**Fixed in commit**: 5efa92d

**Description**: The readonly builtin accepts invalid variable names that start with digits.

**Fix**: Added `_is_valid_identifier()` method to DeclareBuiltin to validate variable names.

## Open Bugs

### 4. Eval Builtin - Escape Handling [NOT A BUG]

**Resolution**: The test had incorrect expectations. PSH behavior matches bash.

**Description**: The test expected `eval "echo \$HOME"` to print literal `$HOME`, but this is not how bash works.

**Correct behavior**:
- `eval "echo \$HOME"` expands to `/Users/username` (correct)
- `eval 'echo \$HOME'` prints literal `$HOME` (single quotes)

**Test**: Fixed in `tests_new/unit/builtins/test_misc_builtins.py::test_eval_quoted_special_chars`

### 5. Output Capture Issues

**Description**: Output from eval and subprocess commands bypasses PSH's output capture mechanism, making it impossible to test properly.

**Affected Commands**:
- `eval` with complex expressions
- Commands that spawn subprocesses (e.g., `bash -c`)

**Impact**: Test framework cannot capture output for verification.

**Tests**: Multiple eval and subprocess-related tests