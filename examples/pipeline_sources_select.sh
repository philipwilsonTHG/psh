#!/usr/bin/env psh
# Test select statement as pipeline source
# Note: Select is interactive, so this tests the structure

echo "Testing Select Statement as Pipeline Source"
echo "========================================="
echo ""

# Test 1: Basic select as pipeline source (non-interactive simulation)
echo "Test 1: Simulating select output"
echo "If select worked as pipeline source, it would look like:"

# Simulate what select might output
echo "Simulating: select item in A B C; do echo $item; done | tr 'a-z' 'A-Z'"
echo "User selects: 1 (A), 2 (B), 3 (C)"
for choice in A B C; do
    echo $choice
done | tr 'a-z' 'A-Z'

echo ""

# Test 2: Function wrapping select
echo "Test 2: Function containing select"
select_wrapper() {
    # Simulate select behavior
    echo "Option 1"
    echo "Option 2" 
    echo "Option 3"
}

echo "Function output piped to wc -l:"
select_wrapper | wc -l

echo ""

# Note about select limitations
echo "Note: Select statements are interactive and may not work well"
echo "as pipeline sources since they write prompts to stderr and"
echo "read from stdin, which conflicts with pipeline behavior."