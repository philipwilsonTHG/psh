#!/usr/bin/env python3
"""Test ModularLexer usage in true interactive mode."""

import os
import sys
import subprocess
import tempfile

def test_real_interactive_mode():
    """Test ModularLexer in actual interactive shell."""
    print("=== Testing Real Interactive Mode ===\n")
    
    # Create a temporary script to run in interactive mode
    test_commands = """
export PSH_DEBUG_LEXER_SELECTION=true
echo "Testing interactive mode"
exit
"""
    
    # Run psh in interactive mode with commands piped in
    proc = subprocess.Popen(
        [sys.executable, '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy()
    )
    
    stdout, stderr = proc.communicate(input=test_commands)
    
    print("Output:")
    print(stdout)
    print("\nDebug output:")
    print(stderr)
    
    if "ModularLexer in interactive mode" in stderr:
        print("✓ ModularLexer correctly used in interactive mode")
    else:
        print("✗ ModularLexer not used in interactive mode")
    
    # Now test with PSH_MODULAR_INTERACTIVE=false
    print("\n=== Testing with PSH_MODULAR_INTERACTIVE=false ===\n")
    
    env = os.environ.copy()
    env['PSH_MODULAR_INTERACTIVE'] = 'false'
    
    proc = subprocess.Popen(
        [sys.executable, '-m', 'psh'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    stdout, stderr = proc.communicate(input=test_commands)
    
    print("Output:")
    print(stdout)
    print("\nDebug output:")
    print(stderr)
    
    if "StateMachineLexer in interactive mode" in stderr:
        print("✓ StateMachineLexer correctly used when disabled")
    else:
        print("✗ PSH_MODULAR_INTERACTIVE=false not respected")

def test_batch_vs_interactive():
    """Compare batch mode (-c) vs interactive mode."""
    print("\n=== Testing Batch vs Interactive Mode ===\n")
    
    # Enable debug output
    env = os.environ.copy()
    env['PSH_DEBUG_LEXER_SELECTION'] = 'true'
    
    # Test 1: Batch mode with -c
    print("Test 1: Batch mode (-c flag)")
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', 'echo "batch test"'],
        capture_output=True,
        text=True,
        env=env
    )
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")
    
    # Test 2: Script from stdin (non-interactive)
    print("\nTest 2: Script from stdin")
    result = subprocess.run(
        [sys.executable, '-m', 'psh'],
        input='echo "stdin test"',
        capture_output=True,
        text=True,
        env=env
    )
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")

if __name__ == "__main__":
    test_real_interactive_mode()
    test_batch_vs_interactive()
    print("\n=== Testing Complete ===")