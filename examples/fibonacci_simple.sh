#!/usr/bin/env psh
# Simple Fibonacci calculator using arithmetic expansion

# Calculate nth Fibonacci number
fib() {
    n=$1
    
    # Handle base cases
    if [ $n -le 0 ]; then
        echo 0
        return
    fi
    
    if [ $n -eq 1 ]; then
        echo 1
        return
    fi
    
    # Calculate using arithmetic expansion
    a=0
    b=1
    i=2
    
    while [ $i -le $n ]; do
        # Arithmetic expansion for Fibonacci calculation
        c=$((a + b))
        a=$b
        b=$c
        i=$((i + 1))
    done
    
    echo $b
}

# Example usage
echo "Fibonacci numbers using arithmetic expansion:"
echo "F(0) = $(fib 0)"
echo "F(1) = $(fib 1)"
echo "F(5) = $(fib 5)"
echo "F(10) = $(fib 10)"
echo "F(15) = $(fib 15)"
echo "F(20) = $(fib 20)"

# Calculate and show a sequence
echo
echo "Fibonacci sequence up to F(12):"
for n in 0 1 2 3 4 5 6 7 8 9 10 11 12; do
    echo -n "$(fib $n) "
done
echo

# Demonstrate variable arithmetic
echo
echo "Using arithmetic expansion with variables:"
x=8
y=13
echo "F($x) = $(fib $x)"
echo "F($y) = $(fib $y)"
echo "F($x) + F($y) = $(($(fib $x) + $(fib $y)))"