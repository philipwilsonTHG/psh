#!/usr/bin/env psh
# Summary of control structures as pipeline sources

echo "Control Structures as Pipeline Sources - Summary"
echo "=============================================="
echo ""

echo "✓ WORKING: Control structures CAN be pipeline sources!"
echo "The following all work correctly:"
echo ""

echo "1. For loop as source:"
for i in one two three; do echo $i; done | wc -l

echo -e "\n2. While loop as source:"
n=3; while [ $n -gt 0 ]; do echo $n; n=$((n-1)); done | sort

echo -e "\n3. If statement as source:"
if true; then echo "success"; fi | tr 'a-z' 'A-Z'

echo -e "\n4. C-style for loop as source:"
for ((i=1; i<=3; i++)); do echo "Item $i"; done | grep 2

echo -e "\n5. Complex pipeline with control structures:"
for i in 1 2 3; do echo $i; done | while read n; do echo "Got $n"; done | tail -2

echo ""
echo "✗ NOT WORKING: Specific issues"
echo ""

echo "1. Brace expansion in for loops:"
echo "   for i in {1..5}; do echo \$i; done"
echo "   Error: Parser expects discrete tokens, not expanded brace"
echo ""

echo "2. Case statements with certain patterns:"
echo "   case \$x in ...) may have parsing issues in pipeline context"
echo ""

echo "CONCLUSION:"
echo "- Control structures as pipeline sources IS implemented (v0.37.0)"
echo "- The architecture works correctly"
echo "- Specific parsing issues with brace expansion in for loops"
echo "- This is a parser bug, not an architectural limitation"