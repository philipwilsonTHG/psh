#!/usr/bin/env psh
# Example script demonstrating expansion debug output

echo "=== Basic Variable Expansion ==="
VAR="hello world"
echo $VAR

echo -e "\n=== Array Expansion ==="
arr=(one two three)
echo ${arr[@]}
echo ${arr[1]}

echo -e "\n=== Command Substitution ==="
result=$(echo "command output")
echo "Result: $result"

echo -e "\n=== Arithmetic Expansion ==="
num=$((5 + 3 * 2))
echo "5 + 3 * 2 = $num"

echo -e "\n=== Tilde Expansion ==="
echo ~
echo ~/Documents

echo -e "\n=== Glob Expansion ==="
echo *.sh

echo -e "\n=== Complex Example ==="
prefix="file"
echo ${prefix}*.txt