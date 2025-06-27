# Visitor Executor Function Return Fix

## Problem
When using the visitor executor, recursive functions like factorial were failing with "maximum recursion depth exceeded" errors. Even simple functions with `return` statements were not working correctly - the `return` statement was not actually stopping function execution.

## Root Causes
There were three issues preventing `FunctionReturn` exceptions from working correctly:

### 1. Wrong Attribute Name
In `_execute_function`, the visitor executor was trying to access `ret.code` but the `FunctionReturn` exception has `ret.exit_code`.

### 2. Exception Caught in Builtin Execution
The `_execute_builtin` method was catching all exceptions, including `FunctionReturn`, preventing it from propagating to the function execution context.

### 3. Exception Caught in Command/Statement Execution
Both `visit_SimpleCommand` and `visit_StatementList` were catching exceptions without properly handling `FunctionReturn`, causing it to be swallowed instead of propagating up to stop function execution.

## Solutions

### 1. Fixed Attribute Access
```python
# Changed from:
return ret.code
# To:
return ret.exit_code
```

### 2. Added FunctionReturn to Builtin Exception Handling
```python
except FunctionReturn as e:
    # FunctionReturn must propagate to be caught by function execution
    raise
```

### 3. Added FunctionReturn Handling in visit Methods
Both `visit_SimpleCommand` and `visit_StatementList` now properly propagate `FunctionReturn`:
```python
except FunctionReturn:
    # Function return must propagate
    raise
```

## Testing
Created comprehensive tests demonstrating:
1. Simple function returns now work correctly
2. Recursive functions (factorial) work up to large values (30+)
3. Performance matches the legacy executor
4. Return statements properly stop function execution

## Result
The visitor executor now correctly handles:
- Function returns with exit codes
- Recursive function calls
- Early returns from functions
- Command substitution with functions that return values

The recursive factorial example now works correctly with the visitor executor, computing `factorial(30)` without any recursion depth issues.