# PSH Bugs Found During Test Migration

This document lists bugs discovered during the test migration effort.

## 1. Test Builtin - Missing Error Messages

**Description**: The test/[ builtin doesn't print error messages for invalid operators.

**Expected**: 
```bash
$ test 5 -foo 10
test: -foo: binary operator expected
```

**Actual**:
```bash
$ test 5 -foo 10
# No error message, just exits with code 2
```

**Test**: `tests_new/unit/builtins/test_test_builtin.py::test_invalid_operator`

## 2. Jobs Builtin - Incorrect -p Option

**Description**: `jobs -p` shows full job information instead of just PIDs.

**Expected**:
```bash
$ sleep 10 & jobs -p
98765
```

**Actual**:
```bash
$ sleep 10 & jobs -p
[1]   Running      sleep 10
```

**Test**: `tests_new/unit/builtins/test_job_control_builtins.py::test_jobs_with_options`

## 3. Readonly Builtin - Invalid Variable Names

**Description**: The readonly builtin accepts invalid variable names that start with digits.

**Expected**:
```bash
$ readonly 123VAR="test"
readonly: `123VAR': not a valid identifier
```

**Actual**:
```bash
$ readonly 123VAR="test"
# No error, accepts the invalid name
```

**Test**: `tests_new/unit/builtins/test_function_builtins.py::test_readonly_invalid_name`

## 4. Eval Builtin - Escape Handling

**Description**: eval doesn't handle escaped $ correctly.

**Expected**:
```bash
$ eval "echo \$HOME"
$HOME
```

**Actual**:
```bash
$ eval "echo \$HOME"
/Users/username
```

**Test**: `tests_new/unit/builtins/test_misc_builtins.py::test_eval_quoted_special_chars`

## 5. Output Capture Issues

**Description**: Output from eval and subprocess commands bypasses PSH's output capture mechanism, making it impossible to test properly.

**Affected Commands**:
- `eval` with complex expressions
- Commands that spawn subprocesses (e.g., `bash -c`)

**Impact**: Test framework cannot capture output for verification.

**Tests**: Multiple eval and subprocess-related tests