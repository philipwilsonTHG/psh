#!/bin/bash
# Test interactive multi-line commands

# Set custom prompts for testing
export PS1='PSH> '
export PS2='... '

# Test multi-line if statement
if [ -f /etc/passwd ]; then
    echo "Password file exists"
fi

# Test multi-line for loop
for i in 1 2 3; do
    echo "Number: $i"
done

# Test function definition
greet() {
    echo "Hello, $1!"
}
greet World

# Test nested structures
for i in A B; do
    if [ "$i" = "A" ]; then
        echo "First letter"
    else
        echo "Second letter"
    fi
done

# Test line continuation
echo "This is a long line that" \
     "continues on the next line" \
     "and even the third line"

# Test case statement
x=2
case $x in
    1) echo "one";;
    2) echo "two";;
    *) echo "other";;
esac

echo "All tests completed"