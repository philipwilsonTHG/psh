#!/usr/bin/env python3
"""Trace the recursion issue in factorial function - fixed version."""

import sys
from psh.shell import Shell
from psh.arithmetic import ArithmeticEvaluator
from psh.expansion.variable import VariableExpander

# Track recursion in various components
arith_call_count = 0
var_expand_call_count = 0
max_depth = 0

# Patch ArithmeticEvaluator.evaluate
original_arith_evaluate = ArithmeticEvaluator.evaluate
def traced_arith_evaluate(self, node):
    global arith_call_count, max_depth
    arith_call_count += 1
    current_depth = arith_call_count
    max_depth = max(max_depth, current_depth)
    
    if arith_call_count <= 20:  # Only print first 20 calls
        indent = "  " * (current_depth - 1)
        print(f"{indent}Arith.evaluate(depth={current_depth}): {type(node).__name__}")
    
    try:
        result = original_arith_evaluate(self, node)
        if arith_call_count <= 20:
            print(f"{indent}  -> {result}")
        return result
    finally:
        arith_call_count -= 1

ArithmeticEvaluator.evaluate = traced_arith_evaluate

# Also trace variable expansion to see if that's involved
original_var_expand = VariableExpander.expand_variable
def traced_var_expand(self, var_token):
    global var_expand_call_count
    var_expand_call_count += 1
    
    if var_expand_call_count <= 10:
        print(f"[VAR_EXPAND #{var_expand_call_count}]: {var_token}")
    
    return original_var_expand(self, var_token)

VariableExpander.expand_variable = traced_var_expand

# Test the issue
shell = Shell()

print("=== Defining simple factorial ===")
shell.run_command("""
factorial() {
    local n=$1
    if [ "$n" -le 1 ]; then
        echo 1
        return  
    fi
    echo "2"  # For now just return 2 to see what happens
}
""")

print("\n=== Testing factorial(1) - should work ===")
shell.run_command("factorial 1")

print("\n=== Testing factorial(2) - returns wrong value ===")
result = shell.run_command("factorial 2")

print("\n=== Now the problematic case: using recursion ===")
shell.run_command("""
factorial_recursive() {
    local n=$1
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    # This is where the problem occurs
    local result=$(factorial_recursive 1)  # Simplest recursive case
    echo $result
}
""")

print("\n=== Testing factorial_recursive(2) ===")
try:
    sys.setrecursionlimit(100)  # Low limit to catch issue
    shell.run_command("factorial_recursive 2")
except RecursionError:
    print(f"\nRECURSION ERROR! Max depth reached: {max_depth}")
    print(f"Total arithmetic evaluations: {arith_call_count}")  
    print(f"Total variable expansions: {var_expand_call_count}")
finally:
    sys.setrecursionlimit(1000)