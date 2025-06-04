#!/usr/bin/env psh
# Practical examples of local variables in psh functions

# Function to find the maximum of two numbers
max() {
    local a=$1
    local b=$2
    
    if [ "$a" -gt "$b" ]; then
        echo $a
    else
        echo $b
    fi
}

# Function to calculate the sum of all arguments
sum_all() {
    local total=0
    local arg
    
    for arg in "$@"; do
        total=$((total + arg))
    done
    
    echo $total
}

# Function to reverse a string word by word
reverse_words() {
    local input="$*"
    local result=""
    local word
    
    for word in $input; do
        if [ -z "$result" ]; then
            result="$word"
        else
            result="$word $result"
        fi
    done
    
    echo "$result"
}

# Function that demonstrates local variables with function calls
calculate_stats() {
    local nums="$*"
    local count=0
    local sum=0
    local max_val=""
    local num
    
    for num in $nums; do
        count=$((count + 1))
        sum=$((sum + num))
        
        if [ -z "$max_val" ]; then
            max_val=$num
        else
            max_val=$(max $max_val $num)
        fi
    done
    
    if [ "$count" -gt 0 ]; then
        local avg=$((sum / count))
        echo "Count: $count"
        echo "Sum: $sum"
        echo "Average: $avg"
        echo "Maximum: $max_val"
    else
        echo "No numbers provided"
    fi
}

# Demonstrate the functions
echo "=== Practical Local Variable Examples ==="
echo ""

echo "1. Finding maximum of two numbers:"
echo "max(10, 20) = $(max 10 20)"
echo "max(42, 17) = $(max 42 17)"
echo ""

echo "2. Sum of multiple arguments:"
echo "sum_all 1 2 3 4 5 = $(sum_all 1 2 3 4 5)"
echo "sum_all 10 20 30 = $(sum_all 10 20 30)"
echo ""

echo "3. Reversing words:"
echo "Original: hello world from psh"
echo "Reversed: $(reverse_words hello world from psh)"
echo ""

echo "4. Calculate statistics:"
calculate_stats 5 2 8 1 9 3
echo ""

echo "5. Variable scoping test:"
# Set global variables
total=9999
count=8888
sum=7777
avg=6666
max_val=5555
word=4444
input="GLOBAL_INPUT"
result="GLOBAL_RESULT"

echo "Global variables before function calls:"
echo "total=$total, count=$count, sum=$sum, avg=$avg"
echo "max_val=$max_val, word=$word, input='$input', result='$result'"

# Call functions
max 100 200 > /dev/null
sum_all 1 2 3 > /dev/null
reverse_words test words > /dev/null
calculate_stats 10 20 30 > /dev/null

echo ""
echo "Global variables after function calls:"
echo "total=$total, count=$count, sum=$sum, avg=$avg"
echo "max_val=$max_val, word=$word, input='$input', result='$result'"
echo "(All values should remain unchanged)"

# Function composition example
echo ""
echo "6. Function composition:"
echo "The maximum of sums: max(sum_all(1 2 3), sum_all(4 5)) = $(max $(sum_all 1 2 3) $(sum_all 4 5))"