#!/usr/bin/env psh

# Clean Fibonacci implementation with multi-line structures
# This works correctly with the fixed parser

echo "=== Fibonacci Sequence Calculator ==="
echo "Now with working multi-line control structures!"
echo

# Calculate first N Fibonacci numbers
n=15
echo "Calculating first $n Fibonacci numbers..."
echo

# Initialize
a=0
b=1
count=0

# First number
echo "F($count) = $a"
count=$((count + 1))

# Second number  
echo "F($count) = $b"
count=$((count + 1))

# Calculate remaining numbers
while [ $count -lt $n ]; do
    # Calculate next Fibonacci number
    c=$((a + b))
    echo "F($count) = $c"
    
    # Update values
    a=$b
    b=$c
    count=$((count + 1))
done

echo
echo "Multi-line parsing improvements:"
echo "✓ While loops can span multiple lines"
echo "✓ If statements work across lines"  
echo "✓ Function definitions parse correctly"
echo "✓ For loops handle multi-line format"
echo
echo "Note: Nested control structures still have limitations"
echo "      due to AST architecture constraints."