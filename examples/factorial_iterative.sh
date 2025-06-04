#!/usr/bin/env psh
# Iterative factorial function using local variables

factorial_iterative() {
    local n=$1
    local result=1
    local i=2
    
    # Handle base cases
    if [ "$n" -lt 0 ]; then
        echo "Error: factorial not defined for negative numbers" >&2
        return 1
    fi
    
    if [ "$n" -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Calculate factorial iteratively
    while [ "$i" -le "$n" ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    
    echo $result
}

# Recursive version with depth limit
factorial_recursive() {
    local n=$1
    local depth=${2:-0}  # Track recursion depth
    
    # Limit recursion depth to prevent stack overflow
    if [ "$depth" -gt 20 ]; then
        echo "Error: recursion depth exceeded" >&2
        return 1
    fi
    
    # Base case
    if [ "$n" -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Recursive case with depth tracking
    local n_minus_1=$((n - 1))
    local next_depth=$((depth + 1))
    local sub_result=$(factorial_recursive $n_minus_1 $next_depth)
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    echo $((n * sub_result))
}

echo "=== Factorial Functions with Local Variables ==="
echo ""

echo "Iterative factorial:"
for num in 0 1 5 10 15; do
    echo "factorial($num) = $(factorial_iterative $num)"
done

echo ""
echo "Recursive factorial (with depth limit):"
for num in 0 1 5 10 15; do
    result=$(factorial_recursive $num 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "factorial($num) = $result"
    else
        echo "factorial($num) = (depth limit exceeded)"
    fi
done

echo ""
echo "Testing variable isolation:"
n=999
result=888
i=777
depth=666

echo "Global vars before: n=$n, result=$result, i=$i, depth=$depth"
factorial_iterative 6 > /dev/null
factorial_recursive 5 > /dev/null 2>&1
echo "Global vars after:  n=$n, result=$result, i=$i, depth=$depth"
echo "(All should be unchanged)"

echo ""
echo "Comparing results:"
echo "factorial(7) iterative = $(factorial_iterative 7)"
echo "factorial(7) recursive = $(factorial_recursive 7 2>/dev/null || echo 'failed')"