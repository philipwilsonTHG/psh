#!/usr/bin/env psh

# Fibonacci Calculator for PSH Shell
# Demonstrates arithmetic expansion feature

echo "=== Fibonacci Sequence Calculator ==="
echo "Using PSH arithmetic expansion: \$((...)) "
echo

# How many terms to calculate
terms=20

echo "Calculating first $terms Fibonacci numbers..."
echo

# Initialize the sequence
a=0
b=1
n=0

# First term
echo "F($n) = $a"
n=$((n + 1))

# Second term
echo "F($n) = $b"
n=$((n + 1))

# Calculate remaining terms
while [ $n -lt $terms ]; do
    # Calculate next Fibonacci number
    c=$((a + b))
    echo "F($n) = $c"
    
    # Update for next iteration
    a=$b
    b=$c
    n=$((n + 1))
done

echo
echo "The arithmetic expansion features used:"
echo "1. Addition: \$((a + b))"
echo "2. Increment: \$((n + 1))"
echo "3. Variables in expressions: a, b, n"
echo
echo "Final values: a=$a, b=$b, n=$n"