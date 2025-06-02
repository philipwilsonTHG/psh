#!/usr/bin/env python3
"""Test interactive multi-line command behavior."""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add psh to path
sys.path.insert(0, str(Path(__file__).parent))

# Test multi-line commands
test_cases = [
    # Basic if statement
    ("if true; then\necho SUCCESS\nfi\n", "SUCCESS"),
    
    # For loop
    ("for i in 1 2 3; do\necho NUM: $i\ndone\n", "NUM: 1\nNUM: 2\nNUM: 3"),
    
    # While loop
    ("i=0\nwhile [ $i -lt 3 ]; do\necho COUNT: $i\ni=$((i+1))\ndone\n", "COUNT: 0\nCOUNT: 1\nCOUNT: 2"),
    
    # Function definition
    ("greet() {\necho Hello, $1!\n}\ngreet World\n", "Hello, World!"),
    
    # Case statement
    ("x=2\ncase $x in\n1) echo one;;\n2) echo two;;\n*) echo other;;\nesac\n", "two"),
    
    # Nested structures
    ("for i in 1 2; do\nif [ $i -eq 1 ]; then\necho FIRST\nelse\necho SECOND\nfi\ndone\n", "FIRST\nSECOND"),
    
    # Line continuation
    ("echo one \\\ntwo \\\nthree\n", "one two three"),
    
    # Heredoc
    ("cat <<EOF\nline1\nline2\nEOF\n", "line1\nline2"),
]

def test_multiline_interactive():
    """Test multi-line commands in interactive mode."""
    print("Testing interactive multi-line commands...")
    
    # Create a test script to feed to psh
    test_script = "test_multiline_commands.sh"
    with open(test_script, "w") as f:
        # Add PS1/PS2 settings for easier parsing
        f.write("export PS1='PSH> '\n")
        f.write("export PS2='... '\n")
        
        for cmd, expected in test_cases:
            f.write(f"{cmd}")
            f.write("echo '---DIVIDER---'\n")
    
    try:
        # Run psh with the test script
        result = subprocess.run(
            ["python3", "-m", "psh"],
            input=open(test_script).read(),
            capture_output=True,
            text=True
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check outputs
        outputs = result.stdout.split("---DIVIDER---")
        for i, (cmd, expected) in enumerate(test_cases):
            if i < len(outputs):
                output = outputs[i].strip()
                # Remove prompts
                lines = output.split('\n')
                actual_output = []
                for line in lines:
                    if line.startswith('PSH>') or line.startswith('...'):
                        continue
                    if line.strip():
                        actual_output.append(line.strip())
                
                actual = '\n'.join(actual_output)
                if expected in actual:
                    print(f"✓ Test {i+1} passed")
                else:
                    print(f"✗ Test {i+1} failed: expected '{expected}', got '{actual}'")
    
    finally:
        if os.path.exists(test_script):
            os.remove(test_script)

if __name__ == "__main__":
    test_multiline_interactive()