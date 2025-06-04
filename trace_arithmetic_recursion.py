#!/usr/bin/env python3
"""Trace arithmetic recursion issue more precisely."""

import sys
from psh.shell import Shell
from psh.expansion.command_sub import CommandSubstitutionExpander

# Track command substitution recursion
cmd_sub_depth = 0
max_cmd_sub_depth = 0

original_expand = CommandSubstitutionExpander.expand
def traced_cmd_sub_expand(self, text):
    global cmd_sub_depth, max_cmd_sub_depth
    cmd_sub_depth += 1
    max_cmd_sub_depth = max(max_cmd_sub_depth, cmd_sub_depth)
    
    print(f"{'  ' * (cmd_sub_depth - 1)}[CMD_SUB depth={cmd_sub_depth}] Expanding: {text[:50]}...")
    
    try:
        result = original_expand(self, text)
        print(f"{'  ' * (cmd_sub_depth - 1)}[CMD_SUB depth={cmd_sub_depth}] Result: {result}")
        return result
    finally:
        cmd_sub_depth -= 1

CommandSubstitutionExpander.expand = traced_cmd_sub_expand

# Test
shell = Shell()

print("=== Define factorial with arithmetic ===")
shell.run_command("""
factorial() {
    local n=$1
    if [ "$n" -le 1 ]; then
        echo 1
        return
    fi
    # The problematic line:
    local n_minus_1=$((n - 1))
    local sub_result=$(factorial $n_minus_1)
    local result=$((n * sub_result))
    echo $result
}
""")

print("\n=== Test factorial(1) ===")
shell.run_command("factorial 1")

print("\n=== Test factorial(2) - this is where issues start ===")
try:
    sys.setrecursionlimit(50)  # Very low limit
    shell.run_command("factorial 2")
except RecursionError:
    print(f"\nRECURSION ERROR!")
    print(f"Max command substitution depth: {max_cmd_sub_depth}")
except Exception as e:
    print(f"\nOther error: {type(e).__name__}: {e}")
finally:
    sys.setrecursionlimit(1000)

# Let's also test a simpler case
print("\n\n=== Testing arithmetic with command sub directly ===")
shell.run_command("echo_five() { echo 5; }")
print("\nSimple command sub:")
shell.run_command("echo $(echo_five)")
print("\nCommand sub in arithmetic:")
shell.run_command("echo $((2 * $(echo_five)))")