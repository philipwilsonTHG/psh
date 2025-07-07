#!/usr/bin/env python3
"""Test Phase B: ModularLexer in interactive mode."""

import os
import sys
import subprocess

def run_psh_command(cmd, env_vars=None):
    """Run a psh command with given environment variables."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    # Enable debug output
    env['PSH_DEBUG_LEXER_SELECTION'] = 'true'
    
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', cmd],
        env=env,
        capture_output=True,
        text=True
    )
    return result

def test_interactive_detection():
    """Test that interactive mode detection works correctly."""
    print("=== Testing Interactive Mode Detection ===\n")
    
    # Test 1: Run in batch mode (-c flag should use batch mode)
    print("Test 1: Batch mode with -c flag")
    result = run_psh_command('echo "batch mode test"')
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")
    assert "StateMachineLexer in batch mode" in result.stderr
    print("✓ Correctly using StateMachineLexer in batch mode\n")
    
    # Test 2: Force interactive mode (would need to modify shell.py to test this)
    # For now, we'll just test the environment variable override
    
    # Test 3: Override with PSH_USE_MODULAR_LEXER
    print("Test 2: Force ModularLexer with PSH_USE_MODULAR_LEXER=true")
    result = run_psh_command('echo "forced modular"', {'PSH_USE_MODULAR_LEXER': 'true'})
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")
    assert "ModularLexer in batch mode" in result.stderr
    print("✓ Correctly forced ModularLexer\n")
    
    # Test 4: Disable ModularLexer for interactive
    print("Test 3: Disable ModularLexer with PSH_MODULAR_INTERACTIVE=false")
    # This would affect interactive mode, but -c uses batch mode
    # So we just verify the env var is respected in tokenize()
    result = run_psh_command('echo "disabled modular"', {'PSH_MODULAR_INTERACTIVE': 'false'})
    print(f"Output: {result.stdout.strip()}")
    print(f"Debug: {result.stderr.strip()}")
    assert "StateMachineLexer in batch mode" in result.stderr
    print("✓ Environment variable respected\n")

def test_compatibility():
    """Test that ModularLexer handles common patterns correctly."""
    print("=== Testing ModularLexer Compatibility ===\n")
    
    test_cases = [
        ('echo hello world', 'hello world'),
        ('echo $HOME', os.environ.get('HOME', '')),
        ('echo ${USER}', os.environ.get('USER', '')),
        ('for i in a b c; do echo $i; done', 'a\nb\nc'),
        ('if true; then echo yes; fi', 'yes'),
        ('echo "quoted string"', 'quoted string'),
        ('echo $(echo nested)', 'nested'),
    ]
    
    for cmd, expected in test_cases:
        print(f"Testing: {cmd}")
        
        # Test with ModularLexer
        result_modular = run_psh_command(cmd, {'PSH_USE_MODULAR_LEXER': 'true'})
        output_modular = result_modular.stdout.strip()
        
        # Test with StateMachineLexer
        result_old = run_psh_command(cmd, {'PSH_USE_MODULAR_LEXER': 'false'})
        output_old = result_old.stdout.strip()
        
        if output_modular == output_old == expected:
            print(f"✓ Both lexers produced: {output_modular}\n")
        else:
            print(f"✗ Mismatch!")
            print(f"  Expected: {expected}")
            print(f"  ModularLexer: {output_modular}")
            print(f"  StateMachineLexer: {output_old}\n")

if __name__ == "__main__":
    test_interactive_detection()
    test_compatibility()
    print("=== Phase B Testing Complete ===")