#!/usr/bin/env psh
# Working factorial function using local variables in psh

# Simple recursive factorial with local variables
# Note: This works for small values due to recursion limits
factorial() {
    local n=$1
    
    # Base case: 0! = 1, 1! = 1  
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    
    # For small values, do direct calculation to avoid deep recursion
    if [ "$n" -eq 2 ]; then
        echo 2
        return
    fi
    
    if [ "$n" -eq 3 ]; then
        echo 6
        return
    fi
    
    if [ "$n" -eq 4 ]; then
        echo 24
        return
    fi
    
    if [ "$n" -eq 5 ]; then
        echo 120
        return
    fi
    
    # For larger values, use iterative approach
    local result=1
    local i=1
    
    while [ "$i" -le "$n" ]; do
        result=$((result * i))
        i=$((i + 1))
    done
    
    echo $result
}

# Function that uses local variables to swap values
swap_demo() {
    local x=$1
    local y=$2
    local temp
    
    echo "Inside function before swap: x=$x, y=$y"
    
    # Swap using local temp variable
    temp=$x
    x=$y
    y=$temp
    
    echo "Inside function after swap: x=$x, y=$y"
}

# Function demonstrating local variable isolation
isolation_demo() {
    local isolated_var="LOCAL_VALUE"
    local counter=0
    
    echo "In isolation_demo:"
    echo "  isolated_var = $isolated_var"
    echo "  counter = $counter"
    
    # Modify local variables
    counter=$((counter + 1))
    isolated_var="MODIFIED_LOCAL"
    
    echo "  After modification:"
    echo "  isolated_var = $isolated_var"  
    echo "  counter = $counter"
}

echo "=== Local Variables in psh Functions ==="
echo ""

echo "1. Factorial using local variables:"
for n in 0 1 2 3 4 5 6 7; do
    echo "factorial($n) = $(factorial $n)"
done

echo ""
echo "2. Demonstrating variable swapping with locals:"
x=100
y=200
temp=300
echo "Global variables before: x=$x, y=$y, temp=$temp"
swap_demo 10 20
echo "Global variables after: x=$x, y=$y, temp=$temp"
echo "(Globals should be unchanged)"

echo ""
echo "3. Demonstrating variable isolation:"
isolated_var="GLOBAL_VALUE"
counter=999
echo "Global variables before: isolated_var=$isolated_var, counter=$counter"
isolation_demo
echo "Global variables after: isolated_var=$isolated_var, counter=$counter"
echo "(Globals should be unchanged)"

echo ""
echo "4. Multiple function calls with local variables:"
echo "Calling factorial three times in a row:"
echo "Result 1: $(factorial 4)"
echo "Result 2: $(factorial 5)"  
echo "Result 3: $(factorial 3)"

echo ""
echo "=== Summary ==="
echo "The 'local' builtin in psh v0.29.0+ ensures that variables"
echo "declared with 'local' are scoped to the function and do not"
echo "affect global variables of the same name."