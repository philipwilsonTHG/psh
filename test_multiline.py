#!/usr/bin/env python3
"""Test script for multi-line functionality."""

import subprocess
import sys

def test_multiline():
    """Test multi-line commands in psh."""
    
    # Test cases
    tests = [
        # Basic if statement
        ("if [ 1 -eq 1 ]; then\necho 'It works!'\nfi\n", "It works!"),
        
        # For loop
        ("for i in 1 2 3; do\necho $i\ndone\n", "1\n2\n3"),
        
        # While loop
        ("i=0\nwhile [ $i -lt 3 ]; do\necho $i\ni=$((i+1))\ndone\n", "0\n1\n2"),
        
        # Function definition
        ("hello() {\necho 'Hello World'\n}\nhello\n", "Hello World"),
    ]
    
    for i, (input_cmd, expected) in enumerate(tests):
        print(f"\nTest {i+1}: Testing multi-line input")
        print(f"Input:\n{input_cmd}")
        
        # Run psh with the multi-line command
        proc = subprocess.Popen(
            ['python3', '-m', 'psh'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(input=input_cmd)
        
        # Remove prompts from output
        lines = stdout.split('\n')
        output_lines = []
        for line in lines:
            if not line.startswith('psh') and not line.startswith('>') and line.strip():
                output_lines.append(line)
        actual = '\n'.join(output_lines)
        
        if expected in stdout:
            print(f"✓ PASSED: Got expected output")
        else:
            print(f"✗ FAILED:")
            print(f"Expected: {repr(expected)}")
            print(f"Got stdout: {repr(stdout)}")
            print(f"Got stderr: {repr(stderr)}")

if __name__ == '__main__':
    test_multiline()