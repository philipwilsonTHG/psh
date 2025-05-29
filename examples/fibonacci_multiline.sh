#!/usr/bin/env psh

# Fibonacci with proper multi-line structures
echo "=== Multi-line Fibonacci Calculator ==="
echo

# Function to calculate nth Fibonacci number
fib() {
    n=$1
    if [ $n -le 0 ]; then
        echo 0
        return
    fi
    if [ $n -eq 1 ]; then
        echo 1
        return
    fi
    
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

# Calculate first 10 Fibonacci numbers
echo "First 10 Fibonacci numbers:"
i=0
while [ $i -lt 10 ]; do
    result=$(fib $i)
    echo "F($i) = $result"
    i=$((i + 1))
done

echo
echo "Using arithmetic expansion successfully!"