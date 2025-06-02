#!/bin/bash
# Test multi-line support in interactive mode

echo "Testing multi-line commands in psh interactive mode"
echo "=================================================="
echo

# Test 1: Basic if statement
echo "Test 1: Basic if statement"
echo 'if [ -f /etc/passwd ]; then
echo "File exists"
fi' | python3 -m psh
echo

# Test 2: While loop
echo "Test 2: While loop"
echo 'count=0
while [ $count -lt 3 ]; do
echo "Count: $count"
count=$((count + 1))
done' | python3 -m psh
echo

# Test 3: For loop
echo "Test 3: For loop"
echo 'for i in a b c; do
echo "Item: $i"
done' | python3 -m psh
echo

# Test 4: Function definition
echo "Test 4: Function definition"
echo 'greet() {
echo "Hello, $1!"
}
greet World' | python3 -m psh
echo

# Test 5: Nested structures
echo "Test 5: Nested structures"
echo 'for i in 1 2; do
if [ $i -eq 1 ]; then
echo "First"
else
echo "Second"
fi
done' | python3 -m psh