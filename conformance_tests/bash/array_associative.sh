#!/bin/bash
# Test associative arrays

declare -A my_assoc_array

my_assoc_array["name"]="psh"
my_assoc_array["type"]="shell"

echo "Name: ${my_assoc_array[name]}"
echo "Type: ${my_assoc_array[type]}"

# Test initialization
declare -A capitals=( ["USA"]="Washington" ["France"]="Paris" )
echo "Capital of France is ${capitals[France]}"
