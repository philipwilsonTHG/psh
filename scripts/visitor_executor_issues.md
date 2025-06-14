# Visitor Executor Known Issues

## Command Substitution Output Capture Issue

### Problem
When running tests with pytest, command substitution inside arithmetic expressions causes output to leak. For example:
```bash
result=$(($(echo 42) * 2))
echo $result
```

Expected output: "84"
Actual output in pytest: "42\n0"

### Analysis
1. The arithmetic expansion itself works correctly (result=84)
2. The issue only occurs in pytest context with certain test files
3. Tests with local shell() fixtures that don't respect PSH_USE_VISITOR_EXECUTOR
4. The "42" is from the echo inside command substitution leaking to stdout
5. The "0" suggests the assignment might be failing in some cases

### Affected Tests
- tests/test_arithmetic_command_substitution.py (9 failures)
- tests/test_command_substitution.py (some failures)
- tests/test_function_command_substitution.py (5 failures)
- And others related to command substitution

### Workarounds Attempted
1. Fixed command substitution to use same executor as parent shell ✓
2. Updated test fixture to respect PSH_USE_VISITOR_EXECUTOR ✓
3. Issue persists - appears to be complex interaction with pytest capture

### Root Cause (Hypothesis)
The visitor executor's handling of builtin output (like echo) in nested shell contexts (command substitution) doesn't properly respect pytest's output capture mechanisms. This may be related to how the shell state's stdout/stderr properties interact with forked processes.

## Other Known Issues

### 1. Redirection with Tilde Expansion
- Tilde expansion not working in redirect targets
- Example: `echo "test" > ~/file.txt`
- The tilde is not expanded in the redirect target

### 2. Break/Continue in Functions Called from Loops
- Break/continue in functions should propagate to the calling loop
- Currently they generate an error even when called from within a loop

### 3. Pipeline and Background Job Edge Cases
- Some specific pipeline configurations fail
- Background job notifications may not work correctly

## Progress Summary
- Started with 302 failures
- Currently at 66 failures (78% reduction)
- 94.3% test compatibility with legacy executor

## Priority for Resolution
1. Command substitution output capture (~40 tests)
2. Redirection issues (~10 tests)
3. Pipeline/background jobs (~10 tests)
4. Miscellaneous (~6 tests)