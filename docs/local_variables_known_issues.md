# Known Issues with Local Variables and Functions in psh v0.29.1

This document describes issues encountered while implementing recursive factorial functions using the new local variable feature in psh v0.29.0+.

## 1. Recursion Depth Limitations

### Issue
Recursive functions hit Python's recursion depth limit very quickly, even for small inputs like factorial(5).

### Error Message
```
psh: <command>:1: unexpected error: maximum recursion depth exceeded
```

### Root Cause
The arithmetic expansion system appears to have a recursive evaluation problem when used within nested command substitutions in recursive functions.

### Workaround
- Limit recursion to very shallow depths (2-3 levels)
- Use iterative algorithms instead of recursive ones
- Pre-calculate base cases to avoid deep recursion

### Example
```bash
# This fails with recursion error:
factorial() {
    local n=$1
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    local result=$(factorial $((n - 1)))
    echo $((n * result))
}

# Workaround - iterative version:
factorial() {
    local n=$1
    local result=1
    local i=1
    while [ "$i" -le "$n" ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    echo $result
}
```

## 2. Arithmetic Expansion in Command Substitution

### Issue
Arithmetic expressions that work in isolation fail when used inside command substitution within recursive contexts.

### Symptoms
- `$((n - 1))` works fine in a simple context
- `$(factorial $((n - 1)))` causes recursion errors
- Even separating the arithmetic into a separate variable sometimes fails

### Example
```bash
# This pattern causes issues:
result=$(factorial $((n - 1)))

# Better approach - separate the arithmetic:
local n_minus_1=$((n - 1))
local result=$(factorial $n_minus_1)
```

## 3. Function Return Values in Arithmetic Context

### Issue
When recursive functions return values via `echo`, using those values in arithmetic expressions sometimes evaluates to 0 unexpectedly.

### Example
```bash
# factorial(2) returns "2" via echo, but:
result=$((n * $(factorial 2)))  # Sometimes evaluates to 0
```

### Possible Cause
The arithmetic evaluator may have issues with command substitution results in certain nested contexts.

## 4. Variable Expansion in Function Arguments

### Issue
The `"$@"` and `"$*"` special parameters don't always behave as expected inside functions with local variables.

### Example
```bash
# This function had issues:
sum_all() {
    local total=0
    local arg
    for arg in "$@"; do  # "$@" didn't expand properly
        total=$((total + arg))
    done
    echo $total
}

# The function received the literal string "nums" instead of the arguments
```

### Workaround
Use explicit parameter passing rather than relying on `"$@"` in complex scenarios.

## 5. Nested Function Definitions

### Issue
While nested function definitions are supported syntactically, there may be scope resolution issues in complex scenarios involving local variables and nested functions.

### Best Practice
Define functions at the top level rather than nesting them inside other functions when using local variables extensively.

## 6. Error Propagation in Command Substitution

### Issue
When errors occur in command substitution (like recursion depth exceeded), they may not properly propagate or may cause unexpected behavior in the parent context.

### Example
```bash
# Error in nested call doesn't always stop execution cleanly
local result=$(factorial $n)  # If this fails, result may be empty or "0"
echo $((n * result))         # This proceeds with invalid data
```

### Workaround
Add explicit error checking:
```bash
local result=$(factorial $n 2>/dev/null)
if [ $? -ne 0 ]; then
    return 1
fi
```

## Recommendations for psh Users

1. **Prefer Iterative Over Recursive**: Due to recursion depth limitations, iterative algorithms are more reliable in psh.

2. **Separate Complex Expressions**: Break down complex arithmetic and command substitutions into separate steps.

3. **Test with Small Values**: Always test recursive functions with small input values first.

4. **Use Explicit Error Handling**: Check return codes when using command substitution in critical paths.

5. **Avoid Deep Nesting**: Keep function calls and arithmetic expressions as shallow as possible.

## Future Improvements

These issues suggest areas for improvement in psh:

1. **Arithmetic Parser Enhancement**: Better handling of command substitution within arithmetic expressions
2. **Recursion Depth**: Investigate why recursion depth is hit so quickly
3. **Error Propagation**: Improve error handling in nested command substitutions
4. **Special Parameter Handling**: Fix `"$@"` and `"$*"` expansion in all contexts

## Testing Recommendations

When testing functions with local variables:

1. Test with both global and local variables of the same name
2. Verify that global variables remain unchanged after function calls
3. Test with various levels of nesting
4. Include error cases in your test suite
5. Compare behavior with bash when possible

## Conclusion

Despite these limitations, the local variable feature in psh v0.29.0+ is a significant improvement that enables proper function scoping. The issues documented here are edge cases that can be worked around with careful coding practices. The iterative factorial example demonstrates that fully functional code can be written by understanding and working within these constraints.