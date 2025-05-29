#!/usr/bin/env psh
# Demonstration of nested control structures in PSH

echo "=== PSH Nested Control Structures Demo ==="
echo

# Example 1: If inside For
echo "1. If statement inside for loop:"
for fruit in apple banana cherry; do
    if [ "$fruit" = "banana" ]; then
        echo "   Found my favorite: $fruit!"
    else
        echo "   Regular fruit: $fruit"
    fi
done
echo

# Example 2: While inside If
echo "2. While loop inside if statement:"
counter=3
if [ "$counter" -gt 0 ]; then
    echo "   Starting countdown..."
    while [ "$counter" -gt 0 ]; do
        echo "   $counter..."
        counter=$((counter - 1))
    done
    echo "   Blast off!"
fi
echo

# Example 3: Case inside For inside If
echo "3. Deeply nested - case inside for inside if:"
process_files=true
if [ "$process_files" = "true" ]; then
    for extension in txt py sh; do
        case "$extension" in
            txt)
                echo "   Text files: for documentation"
                ;;
            py)
                echo "   Python files: for scripts"
                ;;
            sh)
                echo "   Shell files: for automation"
                ;;
        esac
    done
fi
echo

# Example 4: Function with nested structures
echo "4. Function with nested control structures:"
categorize_numbers() {
    echo "   Categorizing numbers from 1 to $1:"
    for i in $(seq 1 $1); do
        if [ "$i" -le 3 ]; then
            case "$i" in
                1) echo "     $i: First" ;;
                2) echo "     $i: Second" ;;
                3) echo "     $i: Third" ;;
            esac
        else
            echo "     $i: Greater than three"
        fi
    done
}

# Note: seq is not implemented, so let's use a different approach
categorize_numbers() {
    echo "   Categorizing numbers:"
    for i in 1 2 3 4 5; do
        if [ "$i" -le 3 ]; then
            case "$i" in
                1) echo "     $i: First" ;;
                2) echo "     $i: Second" ;;
                3) echo "     $i: Third" ;;
            esac
        else
            echo "     $i: Greater than three"
        fi
    done
}

categorize_numbers
echo

# Example 5: Nested loops with break
echo "5. Nested loops with break control:"
for outer in A B C; do
    echo "   Outer: $outer"
    for inner in 1 2 3; do
        echo "     Inner: $inner"
        if [ "$inner" = "2" ]; then
            echo "     Breaking inner loop at 2"
            break
        fi
    done
done
echo

# Example 6: Complex nesting with multiple levels
echo "6. Complex multi-level nesting:"
mode="process"
if [ "$mode" = "process" ]; then
    count=0
    while [ "$count" -lt 2 ]; do
        echo "   Pass $((count + 1)):"
        for item in red green blue; do
            case "$item" in
                red|blue)
                    if [ "$count" = "0" ]; then
                        echo "     Primary color: $item (first pass)"
                    else
                        echo "     Primary color: $item (second pass)"
                    fi
                    ;;
                green)
                    echo "     Secondary color: $item"
                    ;;
            esac
        done
        count=$((count + 1))
    done
fi

echo
echo "=== Demo Complete ==="
echo "PSH now supports arbitrarily nested control structures!"