#!/usr/bin/env psh
# Factorial function demonstration for psh

# Define factorial function
factorial() {
    # Check if argument is provided
    if [ $# -eq 0 ]; then
        echo "Usage: factorial <number>"
        return 1
    fi
    
    # Get the number
    n=$1
    
    # Check if it's a valid number
    if [ $n -lt 0 ]; then
        echo "Error: Factorial is not defined for negative numbers"
        return 1
    fi
    
    # Base cases
    if [ $n -eq 0 ] || [ $n -eq 1 ]; then
        echo 1
        return 0
    fi
    
    # Calculate factorial iteratively
    result=1
    i=2
    while [ $i -le $n ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    
    echo $result
}

# Test the factorial function
echo "Factorial function demonstration:"
echo "================================"

# Test cases
for num in 0 1 5 10 15; do
    echo "factorial($num) = $(factorial $num)"
done

# Test error case
echo ""
echo "Testing error case:"
factorial -5

# Interactive example
echo ""
echo "You can now use the factorial function interactively."
echo "Try: factorial 7"