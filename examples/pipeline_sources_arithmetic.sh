#!/usr/bin/env psh
# Test arithmetic commands and C-style for loops as pipeline sources

echo "Testing Arithmetic Constructs as Pipeline Sources"
echo "==============================================="
echo ""

# Test 1: C-style for loop as pipeline source
echo "Test 1: C-style for loop | grep even"
echo "Expected: Lines with even numbers"
for ((i=0; i<10; i++)); do
    if [ $((i % 2)) -eq 0 ]; then
        echo "Even: $i"
    else
        echo "Odd: $i"
    fi
done | grep "Even"

echo ""

# Test 2: Arithmetic command in pipeline (this likely won't work)
echo "Test 2: Arithmetic command result"
echo "Note: Arithmetic commands likely can't be pipeline sources"
# This probably won't work as (()) doesn't output anything
((5 + 3)) | cat

echo ""

# Test 3: C-style for with arithmetic operations piped
echo "Test 3: Fibonacci sequence first 10 | tail -5"
echo "Expected: Last 5 Fibonacci numbers"
a=0
b=1
for ((i=0; i<10; i++)); do
    echo $a
    temp=$((a + b))
    a=$b
    b=$temp
done | tail -5

echo ""

# Test 4: Nested C-style for loops
echo "Test 4: Multiplication table | grep '12'"
for ((i=1; i<=4; i++)); do
    for ((j=1; j<=4; j++)); do
        echo "$i x $j = $((i * j))"
    done
done | grep "12"