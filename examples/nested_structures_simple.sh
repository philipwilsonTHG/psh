#!/usr/bin/env psh
# Simple demonstration of nested control structures

echo "Nested Control Structures in PSH"
echo "================================"

# Nested if statements
x=5
y=10
if [ "$x" -lt 10 ]; then
    echo "x ($x) is less than 10"
    if [ "$y" -gt 5 ]; then
        echo "  and y ($y) is greater than 5"
        if [ "$x" -lt "$y" ]; then
            echo "    and x is less than y!"
        fi
    fi
fi

echo

# For loop with nested case
for color in red green blue; do
    echo "Processing color: $color"
    case "$color" in
        red)
            if [ -n "$color" ]; then
                echo "  -> Primary color (warm)"
            fi
            ;;
        blue)
            if [ -n "$color" ]; then
                echo "  -> Primary color (cool)"
            fi
            ;;
        green)
            echo "  -> Secondary color"
            ;;
    esac
done

echo

# While loop with nested for
count=2
while [ "$count" -gt 0 ]; do
    echo "Round $count:"
    for letter in A B C; do
        if [ "$count" = "2" ]; then
            echo "  First round: $letter"
        else
            echo "  Second round: $letter"
        fi
    done
    count=$((count - 1))
done

echo

# Function with deeply nested structures
process_data() {
    echo "Processing data..."
    for num in 1 2 3; do
        if [ "$num" -eq 2 ]; then
            echo "  Found middle number"
            case "$num" in
                2)
                    i=0
                    while [ "$i" -lt 2 ]; do
                        echo "    Iteration $((i + 1))"
                        i=$((i + 1))
                    done
                    ;;
            esac
        else
            echo "  Number: $num"
        fi
    done
}

process_data

echo
echo "All examples completed successfully!"