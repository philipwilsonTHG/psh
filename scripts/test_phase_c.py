#!/usr/bin/env python3
"""Test Phase C: ModularLexer as default."""

import os
import sys
import subprocess

def test_default_lexer():
    """Test that ModularLexer is used by default."""
    print("=== Testing Phase C: ModularLexer as Default ===\n")
    
    # Clear any existing environment variables
    env = os.environ.copy()
    for var in ['PSH_USE_MODULAR_LEXER', 'PSH_USE_LEGACY_LEXER', 'PSH_MODULAR_INTERACTIVE']:
        env.pop(var, None)
    
    test_cases = [
        # (description, env_vars, expected_lexer)
        ("Default (no env vars)", {}, "ModularLexer"),
        ("With PSH_USE_LEGACY_LEXER=true", {"PSH_USE_LEGACY_LEXER": "true"}, "StateMachineLexer"),
        ("With PSH_USE_MODULAR_LEXER=false", {"PSH_USE_MODULAR_LEXER": "false"}, "StateMachineLexer"),
        ("Both legacy=true and modular=false", {"PSH_USE_LEGACY_LEXER": "true", "PSH_USE_MODULAR_LEXER": "false"}, "StateMachineLexer"),
    ]
    
    for desc, env_vars, expected in test_cases:
        print(f"Test: {desc}")
        test_env = env.copy()
        test_env.update(env_vars)
        
        # Test with Python API
        result = subprocess.run(
            [sys.executable, '-c', '''
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath("scripts/test_phase_c.py"))))

from psh.lexer import tokenize
from psh.lexer.modular_lexer import ModularLexer
from psh.lexer.core import StateMachineLexer

# Patch to detect which lexer is used
used_lexer = None
original_modular_init = ModularLexer.__init__
original_state_init = StateMachineLexer.__init__

def patched_modular_init(self, *args, **kwargs):
    global used_lexer
    used_lexer = "ModularLexer"
    return original_modular_init(self, *args, **kwargs)

def patched_state_init(self, *args, **kwargs):
    global used_lexer
    used_lexer = "StateMachineLexer"
    return original_state_init(self, *args, **kwargs)

ModularLexer.__init__ = patched_modular_init
StateMachineLexer.__init__ = patched_state_init

# Test tokenization
tokens = tokenize("echo hello")
print(f"Used: {used_lexer}")
'''],
            env=test_env,
            capture_output=True,
            text=True
        )
        
        if expected in result.stdout:
            print(f"  ✓ Correctly using {expected}")
        else:
            print(f"  ✗ Expected {expected}, but got: {result.stdout.strip()}")
        
        if result.stderr:
            print(f"  Error: {result.stderr}")
        print()

def test_with_psh_command():
    """Test ModularLexer usage with actual psh commands."""
    print("=== Testing with PSH Commands ===\n")
    
    # Test command that previously had issues
    test_commands = [
        'echo "hello world"',
        'for i in a b c; do echo $i; done',
        'echo ${HOME}',
        'if true; then echo yes; fi',
    ]
    
    env = os.environ.copy()
    # Clear legacy variables
    env.pop('PSH_USE_MODULAR_LEXER', None)
    env.pop('PSH_USE_LEGACY_LEXER', None)
    
    print("Running with default (ModularLexer):")
    for cmd in test_commands:
        result = subprocess.run(
            [sys.executable, '-m', 'psh', '-c', cmd],
            env=env,
            capture_output=True,
            text=True
        )
        print(f"  Command: {cmd}")
        print(f"  Output: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
    
    print("\nRunning with legacy lexer:")
    env['PSH_USE_LEGACY_LEXER'] = 'true'
    for cmd in test_commands:
        result = subprocess.run(
            [sys.executable, '-m', 'psh', '-c', cmd],
            env=env,
            capture_output=True,
            text=True
        )
        print(f"  Command: {cmd}")
        print(f"  Output: {result.stdout.strip()}")
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")

if __name__ == "__main__":
    test_default_lexer()
    test_with_psh_command()
    print("\n=== Phase C Testing Complete ===")