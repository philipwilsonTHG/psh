#!/usr/bin/env python3
"""Trace the recursion issue in factorial function."""

import sys
from psh.shell import Shell
from psh.arithmetic import ArithmeticEvaluator

# Patch ArithmeticEvaluator to add tracing
original_evaluate = ArithmeticEvaluator.evaluate
call_count = 0

def traced_evaluate(self, expression, variables=None):
    global call_count
    call_count += 1
    indent = "  " * (call_count % 20)  # Limit indent to prevent overflow
    print(f"{indent}ArithmeticEvaluator.evaluate({repr(expression)[:50]}...) [call #{call_count}]")
    try:
        result = original_evaluate(self, expression, variables)
        print(f"{indent}  -> {result}")
        return result
    except Exception as e:
        print(f"{indent}  -> ERROR: {type(e).__name__}")
        raise
    finally:
        call_count -= 1

ArithmeticEvaluator.evaluate = traced_evaluate

# Test the issue
shell = Shell()

# First establish that basic arithmetic works
print("=== Testing basic arithmetic ===")
shell.run_command("echo $((2 + 3))")

print("\n=== Testing command substitution in arithmetic ===")
shell.run_command("echo $((2 * $(echo 3)))")

print("\n=== Defining echo_two function ===")
shell.run_command("""
echo_two() {
    echo 2
}
""")

print("\n=== Testing function in arithmetic (this is where issues start) ===")
try:
    sys.setrecursionlimit(50)  # Very low limit to catch issue quickly
    shell.run_command("echo $((1 * $(echo_two)))")
except RecursionError:
    print("RECURSION ERROR CAUGHT!")
finally:
    sys.setrecursionlimit(1000)

print(f"\nTotal arithmetic evaluation calls: {call_count}")