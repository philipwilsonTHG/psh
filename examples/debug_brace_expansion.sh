#!/usr/bin/env psh
# Debug brace expansion parsing issue

echo "Debugging Brace Expansion in For Loops"
echo "====================================="
echo ""

# Test different contexts
echo "1. Brace expansion alone:"
echo {1..5}
echo {a,b,c}

echo -e "\n2. Brace expansion in command arguments:"
echo "Files:" {file1,file2}.txt

echo -e "\n3. For loop with explicit list:"
for i in 1 2 3; do echo $i; done

echo -e "\n4. For loop with brace expansion (this fails):"
echo "Attempting: for i in {1..3}; do echo \$i; done"
# This will fail with parse error
for i in {1..3}; do echo $i; done

echo -e "\n5. Workaround - expand first:"
items={1..3}
echo "Items expanded: $items"
for i in $items; do echo $i; done

echo -e "\n6. Another workaround - command substitution:"
for i in $(echo {1..3}); do echo $i; done