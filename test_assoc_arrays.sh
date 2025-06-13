#!/bin/bash

# Test associative array functionality

# Declare an associative array
declare -A colors

# Assign values with string keys
colors[red]="#FF0000"
colors[green]="#00FF00"
colors[blue]="#0000FF"
colors["with space"]="value with space"
colors['single quotes']='single quoted value'

# Access values
echo "Red: ${colors[red]}"
echo "Green: ${colors[green]}"
echo "Blue: ${colors[blue]}"
echo "With space: ${colors[with space]}"
echo "Single quotes: ${colors['single quotes']}"

# All keys
echo "All keys: ${!colors[@]}"

# All values
echo "All values: ${colors[@]}"

# Number of elements
echo "Number of elements: ${#colors[@]}"

# Check if key exists
if [[ -v colors[red] ]]; then
    echo "Key 'red' exists"
fi

# Iterate over keys
echo "Iterating over keys:"
for key in "${!colors[@]}"; do
    echo "  $key => ${colors[$key]}"
done

# Unset an element
unset colors[green]
echo "After unset green: ${!colors[@]}"

# Initialize with values
declare -A fruits=([apple]="red" [banana]="yellow" [grape]="purple")
echo "Fruits: ${!fruits[@]} => ${fruits[@]}"

# Test with variables as keys
key="mykey"
colors[$key]="myvalue"
echo "Variable key: ${colors[$key]}"

# Test arithmetic in keys (should be treated as string)
colors[2+2]="four"
echo "Arithmetic key: ${colors[2+2]}"

# Parameter expansion on array elements
colors[test]="HELLO"
echo "Lowercase: ${colors[test],,}"
echo "Length: ${#colors[test]}"

# declare -p to show array
declare -p colors
declare -p fruits