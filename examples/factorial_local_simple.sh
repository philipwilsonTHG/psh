#!/usr/bin/env psh
# Recursive factorial function using local variables
# Simplified version for psh compatibility

factorial() {
    local n=$1
    
    # Base case
    if [ "$n" -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Calculate n-1 using arithmetic expansion
    local n_minus_1=$((n - 1))
    
    # Recursive call
    local sub_result=$(factorial $n_minus_1)
    
    # Calculate final result
    local result=$((n * sub_result))
    echo $result
}

# Test the factorial function
echo "Testing factorial function with local variables:"
echo ""

# Test with small values
echo "factorial(1) = $(factorial 1)"
echo "factorial(2) = $(factorial 2)"  
echo "factorial(3) = $(factorial 3)"
echo "factorial(4) = $(factorial 4)"
echo "factorial(5) = $(factorial 5)"

# Demonstrate local variable scoping
echo ""
echo "Testing variable scoping:"
n=999
result=888
n_minus_1=777
sub_result=666

echo "Global variables before: n=$n, result=$result, n_minus_1=$n_minus_1, sub_result=$sub_result"
factorial 3 > /dev/null
echo "Global variables after:  n=$n, result=$result, n_minus_1=$n_minus_1, sub_result=$sub_result"
echo "(All variables should be unchanged due to local scoping)"