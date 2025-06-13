#!/bin/bash
# Test script to validate bash associative array behavior
# Run with bash to see expected behavior for PSH implementation

echo "=== Bash Associative Array Behavior Test ==="
echo

# Test 1: Declaration required
echo "Test 1: Declaration requirement"
declare -A assoc1
assoc1[key]="value"
echo "After declare -A: assoc1[key]=${assoc1[key]}"

# This would fail in bash (uncomment to test):
# unset assoc2
# assoc2[key]="value"  # Error: must declare -A first

echo
echo "Test 2: Various key formats"
declare -A assoc2
assoc2[simple]="no quotes"
assoc2["with spaces"]="double quoted key"
assoc2['single quoted']="single quoted key"
key_var="variable_key"
assoc2[$key_var]="key from variable"
assoc2[key$key_var]="compound key"
assoc2[""]="empty key works!"

echo "simple: ${assoc2[simple]}"
echo "with spaces: ${assoc2["with spaces"]}"
echo "single quoted: ${assoc2['single quoted']}"
echo "\$key_var: ${assoc2[$key_var]}"
echo "key\$key_var: ${assoc2[key$key_var]}"
echo "empty key: ${assoc2[""]}"

echo
echo "Test 3: Initialization syntax"
declare -A colors=(
    [red]="#FF0000"
    [green]="#00FF00"
    [blue]="#0000FF"
    ["light blue"]="#ADD8E6"
)
echo "Initialized colors:"
for color in "${!colors[@]}"; do
    echo "  $color => ${colors[$color]}"
done

echo
echo "Test 4: Arithmetic in keys"
declare -A assoc3
assoc3[2+2]="arithmetic not evaluated"
assoc3[4]="literal 4"
echo "assoc3[2+2] = ${assoc3[2+2]}"
echo "assoc3[4] = ${assoc3[4]}"
echo "Keys are: ${!assoc3[@]}"

echo
echo "Test 5: Special expansions"
declare -A fruits=(
    [apple]="red"
    [banana]="yellow"
    [grape]="purple"
    [kiwi]="green"
)
echo "All values: ${fruits[@]}"
echo "All keys: ${!fruits[@]}"
echo "Count: ${#fruits[@]}"
echo "As single string: ${fruits[*]}"

echo
echo "Test 6: Key existence"
if [[ -v fruits[apple] ]]; then
    echo "fruits[apple] exists"
fi
if [[ ! -v fruits[orange] ]]; then
    echo "fruits[orange] does not exist"
fi
# Alternative method
if [[ -n "${fruits[banana]+set}" ]]; then
    echo "fruits[banana] is set"
fi

echo
echo "Test 7: Modification and deletion"
fruits[apple]="green"  # Modify
fruits[orange]="orange"  # Add new
unset fruits[grape]  # Delete key
echo "After modifications:"
for fruit in "${!fruits[@]}"; do
    echo "  $fruit => ${fruits[$fruit]}"
done

echo
echo "Test 8: += operator"
declare -A concat
concat[key]="Hello"
concat[key]+=" World"
echo "Concatenated: ${concat[key]}"

declare -A nums
nums[x]=5
(( nums[x] += 10 ))
echo "After arithmetic +=: ${nums[x]}"

echo
echo "Test 9: Array element in arithmetic"
declare -A calc
calc[a]=10
calc[b]=20
result=$(( ${calc[a]} + ${calc[b]} ))
echo "$result = ${calc[a]} + ${calc[b]}"

echo
echo "Test 10: Tricky keys"
declare -A tricky
tricky['$weird']="dollar sign"
tricky['${var}']="looks like expansion"
tricky[$'\n']="newline key"
tricky['a[b]']="bracket in key"
tricky['*']="asterisk"

echo "Tricky keys:"
printf '%q => %s\n' "$weird" "${tricky['$weird']}"
printf '%q => %s\n' '${var}' "${tricky['${var}']}"
printf '%q => %s\n' $'\n' "${tricky[$'\n']}"
printf '%q => %s\n' 'a[b]' "${tricky['a[b]']}"
printf '%q => %s\n' '*' "${tricky['*']}"

echo
echo "Test 11: Parameter expansion on elements"
declare -A paths
paths[home]="/home/user/documents/file.txt"
paths[work]="/work/projects/code/main.c"

echo "Basename of home: ${paths[home]##*/}"
echo "Directory of work: ${paths[work]%/*}"
echo "Replace .txt: ${paths[home]/.txt/.backup}"

echo
echo "Test 12: Copying arrays"
declare -A original=([a]=1 [b]=2 [c]=3)
declare -A copy

# Copy all elements
for key in "${!original[@]}"; do
    copy[$key]="${original[$key]}"
done

echo "Original keys: ${!original[@]}"
echo "Copy keys: ${!copy[@]}"

echo
echo "=== End of tests ==="