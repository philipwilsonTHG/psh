#!/usr/bin/env psh
# Recursive factorial function using local variables

factorial() {
    # Use local to ensure 'n' and 'result' are function-scoped
    local n=$1
    local result
    
    # Base case: factorial of 0 or 1 is 1
    if [ "$n" -le 1 ]; then
        echo 1
        return 0
    fi
    
    # Recursive case: n * factorial(n-1)
    # The arithmetic expansion $((n - 1)) calculates n-1
    # The command substitution $(factorial ...) captures the recursive result
    result=$(factorial $((n - 1)))
    
    # Calculate and return n * factorial(n-1)
    echo $((n * result))
}

# Test the factorial function
echo "Testing factorial function with local variables:"
echo "factorial(0) = $(factorial 0)"
echo "factorial(1) = $(factorial 1)"
echo "factorial(5) = $(factorial 5)"
echo "factorial(10) = $(factorial 10)"

# Demonstrate that variables are properly scoped
n=100
result=200
echo ""
echo "Before calling factorial: n=$n, result=$result"
factorial 6 > /dev/null
echo "After calling factorial: n=$n, result=$result"
echo "(Variables should be unchanged due to local scoping)"