#!/usr/bin/env psh
# Best practices for using local variables in psh functions
# Based on issues discovered during factorial implementation

echo "=== Best Practices for Local Variables in psh ==="
echo ""

# GOOD: Simple local variable usage
good_example_1() {
    local x=10
    local y=20
    local sum=$((x + y))
    echo "Sum: $sum"
}

echo "1. Simple local variables work well:"
good_example_1
echo ""

# GOOD: Iterative algorithms with local variables
fibonacci_iterative() {
    local n=$1
    local a=0
    local b=1
    local temp
    local i=0
    
    if [ "$n" -eq 0 ]; then
        echo 0
        return
    fi
    
    if [ "$n" -eq 1 ]; then
        echo 1
        return
    fi
    
    while [ "$i" -lt "$((n - 1))" ]; do
        temp=$((a + b))
        a=$b
        b=$temp
        i=$((i + 1))
    done
    
    echo $b
}

echo "2. Iterative algorithms are preferred over recursive:"
echo "Fibonacci sequence (iterative):"
for i in 0 1 2 3 4 5 6 7 8; do
    echo "fib($i) = $(fibonacci_iterative $i)"
done
echo ""

# GOOD: Separate arithmetic from command substitution
safe_calculation() {
    local n=$1
    # Separate steps instead of $((n * $(some_command)))
    local step1=$((n + 5))
    local step2=$((step1 * 2))
    echo $step2
}

echo "3. Separate complex expressions:"
echo "safe_calculation(10) = $(safe_calculation 10)"
echo ""

# GOOD: Error handling in functions
robust_function() {
    local input=$1
    
    # Validate input
    if [ -z "$input" ]; then
        echo "Error: No input provided" >&2
        return 1
    fi
    
    # Do calculation with error checking
    local result=$((input * 2))
    if [ $? -ne 0 ]; then
        echo "Error: Calculation failed" >&2
        return 1
    fi
    
    echo $result
    return 0
}

echo "4. Include error handling:"
result=$(robust_function 5 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "robust_function(5) = $result"
fi

result=$(robust_function "" 2>&1)
echo "robust_function('') = $result"
echo ""

# GOOD: Avoid deep nesting
process_list() {
    local item
    local count=0
    
    # Process arguments one by one
    for item in "$@"; do
        echo "Processing: $item"
        count=$((count + 1))
    done
    
    echo "Total items: $count"
}

echo "5. Simple parameter handling:"
process_list apple banana cherry
echo ""

# DEMONSTRATION: Variable scoping works correctly
echo "6. Variable scoping demonstration:"
global_var="GLOBAL"
local_test() {
    local global_var="LOCAL"
    echo "Inside function: global_var = $global_var"
}

echo "Before function: global_var = $global_var"
local_test
echo "After function: global_var = $global_var"
echo ""

echo "=== Summary of Best Practices ==="
echo "1. Use 'local' for all function variables to avoid side effects"
echo "2. Prefer iterative algorithms over recursive ones"
echo "3. Break complex expressions into simple steps"
echo "4. Add error handling for robust functions"
echo "5. Keep arithmetic expressions simple"
echo "6. Test thoroughly with various inputs"
echo ""
echo "Note: These practices work around current limitations in psh v0.29.1"
echo "See docs/local_variables_known_issues.md for detailed issue documentation"