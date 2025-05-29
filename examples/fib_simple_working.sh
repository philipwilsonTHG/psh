#!/usr/bin/env psh

# Working Fibonacci Sequence Calculator for PSH
# This version avoids multi-line control structures

echo "=== Fibonacci Sequence Calculator ==="
echo "Demonstrating PSH arithmetic expansion"
echo

# Calculate Fibonacci sequence
a=0
b=1

echo "F(0) = $a"
echo "F(1) = $b"

# Calculate F(2) through F(20)
c=$((a + b)); echo "F(2) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(3) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(4) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(5) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(6) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(7) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(8) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(9) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(10) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(11) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(12) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(13) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(14) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(15) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(16) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(17) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(18) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(19) = $c"; a=$b; b=$c
c=$((a + b)); echo "F(20) = $c"

echo
echo "Arithmetic expansion examples:"
echo "Addition: 5 + 3 = $((5 + 3))"
echo "Subtraction: 10 - 4 = $((10 - 4))"
echo "Multiplication: 6 * 7 = $((6 * 7))"
echo "Division: 20 / 3 = $((20 / 3))"
echo "Remainder: 20 % 3 = $((20 % 3))"
echo "Power: 2^8 = $((2 ** 8))"
echo
echo "Variables in arithmetic:"
x=15
y=4
echo "x=$x, y=$y"
echo "x + y = $((x + y))"
echo "x - y = $((x - y))"
echo "x * y = $((x * y))"
echo "x / y = $((x / y))"
echo "x % y = $((x % y))"