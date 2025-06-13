#!/usr/bin/env psh
# Example script demonstrating execution debug output

echo "=== Builtin Command ==="
echo "Hello from builtin"

echo -e "\n=== External Command ==="
ls -la /tmp | head -n 5

echo -e "\n=== Function Execution ==="
my_function() {
    echo "Inside function: $1"
    return 42
}

my_function "test arg"
echo "Function returned: $?"

echo -e "\n=== Pipeline Execution ==="
echo "one two three" | tr ' ' '\n' | sort | head -2

echo -e "\n=== Background Job ==="
sleep 2 &
echo "Started background job: $!"
wait

echo -e "\n=== Command with Variable Assignment ==="
MSG="temporary" echo "Message is: $MSG"