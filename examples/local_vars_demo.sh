#!/usr/bin/env psh
# Demonstration of local variables in psh functions

# Simple function with local variables
add_numbers() {
    local a=$1
    local b=$2
    local sum=$((a + b))
    echo $sum
}

# Function that modifies local variables
process_string() {
    local str=$1
    local prefix="PROCESSED"
    local result="${prefix}: ${str}"
    echo "$result"
}

# Nested function calls with local variables
outer_function() {
    local outer_var="OUTER"
    echo "In outer_function: outer_var=$outer_var"
    
    inner_function() {
        local inner_var="INNER"
        echo "  In inner_function: inner_var=$inner_var"
        echo "  Can access outer_var=$outer_var"
    }
    
    inner_function
    echo "Back in outer_function: outer_var=$outer_var"
}

# Test the functions
echo "=== Testing local variables in functions ==="
echo ""

echo "1. Simple arithmetic with local variables:"
echo "add_numbers 5 3 = $(add_numbers 5 3)"
echo "add_numbers 10 20 = $(add_numbers 10 20)"
echo ""

echo "2. String processing with local variables:"
echo "$(process_string "Hello World")"
echo "$(process_string "Testing local vars")"
echo ""

echo "3. Testing variable scoping:"
a=100
b=200
sum=300
str="GLOBAL"
prefix="GLOBAL_PREFIX"
result="GLOBAL_RESULT"

echo "Before function calls:"
echo "  a=$a, b=$b, sum=$sum"
echo "  str=$str, prefix=$prefix, result=$result"

add_numbers 7 8 > /dev/null
process_string "test" > /dev/null

echo "After function calls:"
echo "  a=$a, b=$b, sum=$sum"
echo "  str=$str, prefix=$prefix, result=$result"
echo "(All should be unchanged)"
echo ""

echo "4. Nested function calls:"
outer_function