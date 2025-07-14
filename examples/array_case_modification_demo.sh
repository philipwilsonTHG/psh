#!/usr/bin/env psh
# Demo script for array case modification parameter expansion

echo "=== Array Case Modification Demo ==="
echo

# Create sample arrays
names=("alice" "BOB" "Charlie")
words=("hello" "WORLD" "Test123")
mixed=("aBc" "DeF" "gHi")

echo "Original arrays:"
echo "names: ${names[@]}"
echo "words: ${words[@]}"
echo "mixed: ${mixed[@]}"
echo

echo "=== Uppercase All (^^) ==="
echo "names uppercase: ${names[@]^^}"
echo "words uppercase: ${words[@]^^}"
echo "mixed uppercase: ${mixed[@]^^}"
echo

echo "=== Lowercase All (,,) ==="
echo "names lowercase: ${names[@],,}"
echo "words lowercase: ${words[@],,}"
echo "mixed lowercase: ${mixed[@],,}"
echo

echo "=== Uppercase First (^) ==="
lower=("hello" "world" "test")
echo "lower array: ${lower[@]}"
echo "first uppercase: ${lower[@]^}"
echo

echo "=== Lowercase First (,) ==="
upper=("HELLO" "WORLD" "TEST")
echo "upper array: ${upper[@]}"
echo "first lowercase: ${upper[@],}"
echo

echo "=== Pattern-Based Case Modification ==="
sentence=("the" "quick" "brown" "fox")
echo "Original: ${sentence[@]}"
echo "Uppercase vowels: ${sentence[@]^^[aeiou]}"
echo "Uppercase 'q' and 'x': ${sentence[@]^^[qx]}"
echo

# Using with IFS
echo "=== Using with IFS (array[*]) ==="
IFS="-"
echo "Joined with dash and uppercase: ${names[*]^^}"
IFS=" "  # Reset IFS
echo

# Creating new arrays from case-modified arrays
echo "=== Creating New Arrays ==="
original=("one" "TWO" "Three")
upper_array=(${original[@]^^})
lower_array=(${original[@],,})

echo "Original: ${original[@]}"
echo "New upper array: ${upper_array[@]}"
echo "New lower array: ${lower_array[@]}"
echo

# Practical example: normalizing filenames
echo "=== Practical Example: Normalizing Filenames ==="
files=("Document.PDF" "Image.JPG" "README.txt" "DATA.CSV")
echo "Original files: ${files[@]}"
echo "Normalized (lowercase): ${files[@],,}"
echo

# Working with associative arrays
echo "=== Associative Arrays ==="
declare -A user_data
user_data[name]="john doe"
user_data[email]="JOHN@EXAMPLE.COM"
user_data[city]="New York"

echo "Original data:"
for key in "${!user_data[@]}"; do
    echo "  $key: ${user_data[$key]}"
done

echo "Values uppercase: ${user_data[@]^^}"
echo "Values lowercase: ${user_data[@],,}"