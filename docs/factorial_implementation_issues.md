# Issues Encountered Implementing Factorial in psh

This document summarizes the issues discovered while implementing a recursive factorial function using psh's new local variable feature (v0.29.0+).

## Summary of Issues

### 1. **Recursion Depth Exceeded**
- **Problem**: Even simple recursive calls like `factorial(5)` hit Python's recursion limit
- **Error**: `maximum recursion depth exceeded`
- **Root Cause**: Appears to be related to arithmetic expansion within command substitution in recursive contexts
- **Workaround**: Use iterative algorithms or limit recursion to 2-3 levels

### 2. **Arithmetic Expansion in Nested Contexts**
- **Problem**: `$((n * $(factorial $((n-1)))))` causes immediate recursion errors
- **Workaround**: Break into separate steps with intermediate variables

### 3. **Command Substitution Return Values**
- **Problem**: Recursive functions returning values via `echo` sometimes evaluate to 0 in arithmetic contexts
- **Example**: `result=$((n * $(factorial 2)))` may give 0 instead of expected value

### 4. **I/O Errors with stderr Redirection**
- **Problem**: Using `>&2` for error messages can cause "I/O operation on closed file" errors
- **Context**: Appears when functions are called within command substitution

### 5. **Special Parameter Expansion**
- **Problem**: `"$@"` and `"$*"` don't always expand as expected in functions
- **Symptom**: Functions receive literal parameter names instead of values

## Working Example

Despite these issues, factorial can be implemented successfully:

```bash
#!/usr/bin/env psh
# Working factorial using local variables

factorial() {
    local n=$1
    local result=1
    local i=1
    
    # Iterative approach avoids recursion issues
    while [ "$i" -le "$n" ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    
    echo $result
}

# Test it
echo "factorial(5) = $(factorial 5)"  # Output: 120
```

## Recommendations

1. **Use iterative algorithms** when possible to avoid recursion depth issues
2. **Keep arithmetic simple** - avoid nested command substitutions in arithmetic contexts
3. **Test with small inputs** before scaling up
4. **Separate complex operations** into discrete steps
5. **Avoid stderr redirection** in functions called via command substitution

## Positive Findings

The local variable feature itself works correctly:
- Variables declared with `local` are properly scoped
- Global variables are not affected by local declarations
- Multiple function calls maintain proper isolation
- Nested functions can access parent scope variables

The issues are primarily with complex recursive patterns and nested expansions, not with the local variable implementation itself.