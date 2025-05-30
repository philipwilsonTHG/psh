#!/usr/bin/env psh
# Example demonstrating the read builtin

echo "Read Builtin Examples"
echo "===================="
echo

# Example 1: Basic user input
echo "What is your name?"
read name
echo "Hello, $name!"
echo

# Example 2: Reading multiple values
echo "Enter three words:"
read first second third
echo "First: $first"
echo "Second: $second"
echo "Third: $third"
echo

# Example 3: Using custom IFS
echo "Enter a colon-separated list (e.g., apple:banana:orange):"
IFS=: read fruit1 fruit2 fruit3
echo "Fruit 1: $fruit1"
echo "Fruit 2: $fruit2"
echo "Fruit 3: $fruit3"
echo

# Example 4: Reading into default REPLY variable
echo "Type something (stored in REPLY):"
read
echo "You typed: $REPLY"
echo

# Example 5: Raw mode to preserve backslashes
echo "Enter text with backslashes (e.g., C:\\Users\\Name):"
read -r path
echo "Path: $path"