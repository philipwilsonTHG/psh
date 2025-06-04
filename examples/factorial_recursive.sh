#!/usr/bin/env psh
# Recursive factorial function demonstration

# Recursive factorial implementation
factorial_recursive() {
    n=$1
    
    # Base case
    if [ $n -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Recursive case: n * factorial(n-1)
    prev=$((n - 1))
    prev_factorial=$(factorial_recursive $prev)
    echo $((n * prev_factorial))
}

# Compare iterative and recursive versions
factorial_iterative() {
    if [ $1 -le 1 ]; then
        echo 1
    else
        n=$1
        result=1
        i=2
        while [ $i -le $n ]; do
            result=$((result * i))
            i=$((i + 1))
        done
        echo $result
    fi
}

# Test both implementations
echo "Comparing iterative and recursive factorial:"
echo "==========================================="

for n in 1 5 8 12; do
    iter=$(factorial_iterative $n)
    recur=$(factorial_recursive $n)
    echo "$n! = $iter (iterative) = $recur (recursive)"
done

# Note: The recursive version may hit shell limits for large numbers
echo ""
echo "Note: Large factorials may cause integer overflow"
echo "psh uses standard integer arithmetic"