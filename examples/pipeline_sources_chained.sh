#!/usr/bin/env psh
# Test chaining control structures in pipelines
# Testing: control -> control -> command

echo "Testing Chained Control Structures in Pipelines"
echo "=============================================="
echo ""

# Test 1: For loop piping to while loop
echo "Test 1: For loop | while loop"
echo "Expected: Got: 1, Got: 2, Got: 3"
for i in 1 2 3; do 
    echo $i
done | while read num; do 
    echo "Got: $num"
done

echo ""

# Test 2: While loop piping to for loop (with command substitution)
echo "Test 2: While loop | for loop (should show each line)"
i=0
while [ $i -lt 3 ]; do
    echo "Item $i"
    i=$((i + 1))
done | for line in $(cat); do
    echo "Processing: $line"
done

echo ""

# Test 3: Multiple control structures in a pipeline
echo "Test 3: if | case | while"
echo "Expected: 'HELLO WORLD' repeated 3 times"
if true; then
    echo "hello world"
fi | case $(cat) in
    "hello world") echo "HELLO WORLD";;
    *) echo "no match";;
esac | while read line; do
    echo "1: $line"
    echo "2: $line" 
    echo "3: $line"
done

echo ""

# Test 4: Control structure with multiple outputs piped
echo "Test 4: For loop with multiple outputs | head -3"
for i in {1..10}; do 
    echo "Line $i"
done | head -3