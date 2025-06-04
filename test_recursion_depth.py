#!/usr/bin/env python3
"""Test to understand the recursion depth issue in psh."""

import sys
from psh.shell import Shell

# Check Python's recursion limit
print(f"Python recursion limit: {sys.getrecursionlimit()}")

# Create a simple recursive factorial for comparison
def python_factorial(n, depth=0):
    print(f"  Python factorial({n}) at depth {depth}")
    if n <= 1:
        return 1
    return n * python_factorial(n - 1, depth + 1)

print("\nPython recursive factorial(5):")
result = python_factorial(5)
print(f"Result: {result}")

# Now test with psh
print("\n\nTesting psh with factorial...")
shell = Shell()

# First, let's test if basic arithmetic works
print("\nBasic arithmetic tests:")
shell.run_command("echo $((5 * 4))")

# Test command substitution
print("\nCommand substitution test:")
shell.run_command("echo $(echo 5)")

# Test arithmetic with command substitution  
print("\nArithmetic with command substitution:")
shell.run_command("echo $((2 * $(echo 3)))")

# Define a simple function that just returns a number
print("\nDefining simple function:")
shell.run_command("""
simple_func() {
    echo 5
}
""")

print("\nCalling simple function:")
shell.run_command("simple_func")

print("\nUsing function in arithmetic:")
try:
    shell.run_command("echo $((2 * $(simple_func)))")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Now test the factorial
print("\n\nDefining factorial function:")
shell.run_command("""
factorial() {
    local n=$1
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    local n_minus_1=$((n - 1))
    local sub_result=$(factorial $n_minus_1)
    local result=$((n * sub_result))
    echo $result
}
""")

print("\nTesting factorial with small values:")
for n in [1, 2, 3]:
    print(f"\nfactorial({n}):")
    try:
        # Add recursion tracking
        sys.setrecursionlimit(100)  # Set a lower limit to catch the issue sooner
        shell.run_command(f"factorial {n}")
        sys.setrecursionlimit(1000)  # Reset
    except RecursionError as e:
        print(f"RecursionError at factorial({n})!")
        sys.setrecursionlimit(1000)  # Reset
        break
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        break