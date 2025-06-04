#!/usr/bin/env psh
# Working factorial demonstration

# Define factorial function
factorial() {
    if [ $1 -le 1 ]; then
        echo 1
    else
        n=$1
        result=1
        i=2
        while [ $i -le $n ]; do
            result=$((result * i))
            i=$((i + 1))
        done
        echo $result
    fi
}

echo "Factorial function demonstration"
echo "================================"

# Call the function directly
echo "5! = $(factorial 5)"
echo "10! = $(factorial 10)"
echo "15! = $(factorial 15)"

# Alternative: call without command substitution
echo ""
echo "Direct output:"
factorial 0
factorial 1
factorial 5
factorial 10