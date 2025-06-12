#!/usr/bin/env psh
# Simple test to verify control structures as pipeline sources work

echo "Simple Pipeline Source Tests"
echo "==========================="
echo ""

# Test 1: Basic for loop as source (no brace expansion)
echo "Test 1: for loop | wc -l"
for i in a b c; do echo $i; done | wc -l

# Test 2: While loop as source
echo -e "\nTest 2: while loop | tail -2"
count=0
while [ $count -lt 5 ]; do
    echo "Line $count"
    count=$((count + 1))
done | tail -2

# Test 3: If as source
echo -e "\nTest 3: if statement | tr a-z A-Z"
if [ 1 -eq 1 ]; then
    echo "true condition"
else  
    echo "false condition"
fi | tr 'a-z' 'A-Z'

# Test 4: Case as source
echo -e "\nTest 4: case statement | wc -c"
x=hello
case $x in
    hello) echo "matched hello";;
    *) echo "no match";;
esac | wc -c

# Test 5: C-style for as source
echo -e "\nTest 5: C-style for loop | grep 3"
for ((i=1; i<=5; i++)); do
    echo "Number $i"
done | grep 3

# Test 6: The problem - brace expansion
echo -e "\nTest 6: Testing brace expansion separately"
echo "Brace expansion: {1..5}"
echo {1..5}
echo "In for loop:"
for x in {1..5}; do echo $x; done