#!/usr/bin/env psh

# Fibonacci function using multi-line syntax
echo "Loading Fibonacci function..."

# Define the function
fib() {
    n=$1
    
    # Base cases
    if [ $n -le 0 ]; then
        echo 0
        return
    fi
    
    if [ $n -eq 1 ]; then
        echo 1
        return
    fi
    
    # Calculate iteratively
    a=0
    b=1
    i=2
    
    while [ $i -le $n ]; do
        c=$((a + b))
        a=$b
        b=$c
        i=$((i + 1))
    done
    
    echo $b
}

echo "Function loaded. Testing..."
echo

# Test the function
for n in 0 1 2 3 4 5 6 7 8 9 10; do
    result=$(fib $n)
    echo "fib($n) = $result"
done

echo
echo "Multi-line function definitions now work correctly!"