#!/usr/bin/env psh
# Test the specific case mentioned: brace expansion in for loops as pipeline source

echo "Testing Brace Expansion in Pipeline Sources"
echo "=========================================="
echo ""

# Test 1: The specific example that fails
echo "Test 1: for text in {1..10}; do echo \$text; done | while read line; do echo \$line; done"
echo "Expected: Numbers 1 through 10"
echo "Result:"
for text in {1..10}; do echo $text; done | while read line; do echo $line; done

echo ""

# Test 2: Simpler brace expansion test
echo "Test 2: for x in {a..e}; do echo \$x; done | tr 'a-z' 'A-Z'"
echo "Expected: A B C D E"
echo "Result:"
for x in {a..e}; do echo $x; done | tr 'a-z' 'A-Z'

echo ""

# Test 3: List brace expansion
echo "Test 3: for item in {red,green,blue}; do echo \$item; done | grep e"
echo "Expected: red, green, blue (lines with 'e')"
echo "Result:"
for item in {red,green,blue}; do echo $item; done | grep e

echo ""

# Test 4: Without brace expansion (for comparison)
echo "Test 4: for i in 1 2 3 4 5; do echo \$i; done | tail -3"
echo "Expected: 3 4 5"
echo "Result:"
for i in 1 2 3 4 5; do echo $i; done | tail -3

echo ""

# Test 5: Workaround using command substitution
echo "Test 5: Workaround using seq"
echo "for i in \$(seq 1 5); do echo \$i; done | while read x; do echo \"Got: \$x\"; done"
echo "Result:"
for i in $(seq 1 5); do echo $i; done | while read x; do echo "Got: $x"; done