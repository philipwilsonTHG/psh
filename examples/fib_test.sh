#!/usr/bin/env psh
# Test Fibonacci with arithmetic expansion

# Simple iterative approach without function
echo "Calculating Fibonacci numbers with arithmetic expansion:"

# F(10)
n=10
a=0
b=1
i=2

if [ $n -eq 0 ]; then
    result=0
elif [ $n -eq 1 ]; then
    result=1
else
    while [ $i -le $n ]; do
        c=$((a + b))
        a=$b
        b=$c
        i=$((i + 1))
    done
    result=$b
fi

echo "F(10) = $result"

# Calculate a few more
echo
echo "Fibonacci sequence:"
echo -n "0 1 "

a=0
b=1
for x in 2 3 4 5 6 7 8 9 10; do
    c=$((a + b))
    echo -n "$c "
    a=$b
    b=$c
done
echo

# Demonstrate arithmetic operations
echo
echo "Arithmetic operations:"
x=5
y=8
echo "F(5) = 5, F(8) = 21"
echo "F(5) + F(8) = $((5 + 21)) = $((x + 21))"
echo "F(5) * F(8) = $((5 * 21))"