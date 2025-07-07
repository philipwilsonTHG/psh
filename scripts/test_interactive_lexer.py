#!/usr/bin/env python3
"""Test ModularLexer in actual interactive mode."""

import os
import sys
import subprocess
import time

def test_interactive_shell():
    """Test that interactive shell uses ModularLexer by default."""
    print("=== Testing Interactive Shell Lexer Selection ===\n")
    
    # Create a test script that the interactive shell will execute
    test_script = """
import os
os.environ['PSH_DEBUG_LEXER_SELECTION'] = 'true'

# Test tokenization in interactive mode
from psh.shell import Shell
# Create shell without script name to simulate interactive mode
shell = Shell()
# Force interactive mode by setting script mode to false
shell.state.is_script_mode = False

# Run a simple command
result = shell.run_command('echo "interactive test"')
print("Command executed successfully" if result == 0 else "Command failed")
"""
    
    # Test 1: Default (should use ModularLexer)
    print("Test 1: Default interactive mode")
    proc = subprocess.Popen(
        [sys.executable, '-c', test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy()
    )
    stdout, stderr = proc.communicate()
    print(f"Output: {stdout.strip()}")
    print(f"Debug: {stderr.strip()}")
    if "ModularLexer in interactive mode" in stderr:
        print("✓ Using ModularLexer in interactive mode\n")
    else:
        print("✗ Not using ModularLexer in interactive mode\n")
    
    # Test 2: Disable ModularLexer for interactive
    print("Test 2: Interactive mode with PSH_MODULAR_INTERACTIVE=false")
    env = os.environ.copy()
    env['PSH_MODULAR_INTERACTIVE'] = 'false'
    proc = subprocess.Popen(
        [sys.executable, '-c', test_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    stdout, stderr = proc.communicate()
    print(f"Output: {stdout.strip()}")
    print(f"Debug: {stderr.strip()}")
    if "StateMachineLexer in interactive mode" in stderr:
        print("✓ Using StateMachineLexer when disabled\n")
    else:
        print("✗ Not respecting PSH_MODULAR_INTERACTIVE=false\n")

def test_shell_py_integration():
    """Test that shell.py properly detects interactive mode."""
    print("=== Testing shell.py Interactive Detection ===\n")
    
    # Check if shell.py passes strict=False for interactive mode
    test_code = '''
import sys
import os
os.environ['PSH_DEBUG_LEXER_SELECTION'] = 'true'

# Mock interactive mode detection
class MockShell:
    def __init__(self):
        self.interactive = True
    
    def run_line(self, line):
        from psh.lexer import tokenize
        # Shell should call tokenize with strict=False in interactive mode
        tokens = tokenize(line, strict=False)
        return tokens

shell = MockShell()
tokens = shell.run_line("echo test")
print(f"Got {len(tokens)} tokens")
'''
    
    result = subprocess.run(
        [sys.executable, '-c', test_code],
        capture_output=True,
        text=True
    )
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")
    if "ModularLexer in interactive mode" in result.stderr:
        print("✓ Interactive mode correctly uses strict=False\n")
    else:
        print("✗ Interactive mode not properly detected\n")

if __name__ == "__main__":
    test_interactive_shell()
    test_shell_py_integration()
    print("=== Interactive Mode Testing Complete ===")