#!/usr/bin/env psh
# Test control structures as pipeline sources
# This tests the limitation mentioned in TODO.md

echo "Testing Control Structures as Pipeline Sources"
echo "============================================="
echo ""

# Test 1: For loop as pipeline source
echo "Test 1: For loop piping to wc -l"
echo "Expected: 3"
echo -n "Result: "
for i in a b c; do echo $i; done | wc -l

echo ""

# Test 2: While loop as pipeline source
echo "Test 2: While loop piping to grep"
echo "Expected: 2"
echo -n "Result: "
i=1
while [ $i -le 5 ]; do
    echo "Line $i"
    i=$((i + 1))
done | grep -c "Line"

echo ""

# Test 3: If statement as pipeline source
echo "Test 3: If statement piping to sed"
echo "Expected: YES"
echo -n "Result: "
if true; then
    echo "yes"
else
    echo "no"
fi | sed 's/yes/YES/'

echo ""

# Test 4: Case statement as pipeline source
echo "Test 4: Case statement piping to tr"
echo "Expected: MATCHED"
echo -n "Result: "
value="test"
case $value in
    test) echo "matched";;
    *) echo "no match";;
esac | tr 'a-z' 'A-Z'

echo ""

# Test 5: Nested control structures piping
echo "Test 5: Nested for/if piping to sort"
echo "Expected: 2 4 6 8 10 (sorted even numbers)"
echo -n "Result: "
for i in 1 2 3 4 5 6 7 8 9 10; do
    if [ $((i % 2)) -eq 0 ]; then
        echo $i
    fi
done | sort -n | tr '\n' ' '
echo ""