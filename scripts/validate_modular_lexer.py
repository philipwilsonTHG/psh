#!/usr/bin/env python3
"""Validate ModularLexer in common PSH scenarios."""

import os
import sys
import subprocess
from pathlib import Path

# Enable ModularLexer
os.environ['PSH_USE_MODULAR_LEXER'] = 'true'

# Test scenarios
TEST_SCENARIOS = [
    # Basic commands
    ("Basic echo", "echo hello world"),
    ("Echo with quotes", 'echo "Hello World"'),
    ("Echo with variable", "VAR=test; echo $VAR"),
    
    # Control structures
    ("Simple if", "if true; then echo yes; fi"),
    ("For loop", "for i in 1 2 3; do echo $i; done"),
    ("While loop", "x=0; while [ $x -lt 3 ]; do echo $x; x=$((x+1)); done"),
    
    # Double brackets
    ("Double bracket test", "[[ 1 -eq 1 ]] && echo equal"),
    ("String comparison", '[[ "abc" == "abc" ]] && echo match'),
    
    # Pipelines
    ("Simple pipeline", "echo hello | cat"),
    ("Multi-stage pipeline", "echo hello world | grep world | wc -w"),
    
    # Redirections
    ("Output redirect", "echo test > /tmp/psh_test.txt; cat /tmp/psh_test.txt; rm /tmp/psh_test.txt"),
    ("Append redirect", "echo line1 > /tmp/psh_test.txt; echo line2 >> /tmp/psh_test.txt; cat /tmp/psh_test.txt; rm /tmp/psh_test.txt"),
    
    # Variable expansions
    ("Parameter expansion", 'VAR=hello; echo "${VAR} world"'),
    ("Default value", 'echo "${UNDEFINED:-default}"'),
    ("String length", 'VAR=hello; echo ${#VAR}'),
    
    # Command substitution
    ("Command substitution", "echo Current dir: $(pwd)"),
    ("Nested substitution", 'echo "Files: $(ls | wc -l)"'),
    
    # Functions
    ("Function definition", "greet() { echo Hello $1; }; greet World"),
    
    # Arrays (if supported)
    ("Array creation", "arr=(one two three); echo ${arr[1]}"),
]

def run_test(name, command):
    """Run a single test scenario."""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Command: {command}")
    print("-" * 60)
    
    try:
        # Run command using psh
        result = subprocess.run(
            [sys.executable, '-m', 'psh', '-c', command],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ Success (exit code: {result.returncode})")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
        else:
            print(f"❌ Failed (exit code: {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
                
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout after 5 seconds")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Run all validation tests."""
    print("PSH ModularLexer Validation Suite")
    print("=" * 60)
    print(f"ModularLexer enabled: {os.environ.get('PSH_USE_MODULAR_LEXER', 'false')}")
    
    passed = 0
    failed = 0
    
    for name, command in TEST_SCENARIOS:
        if run_test(name, command):
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Total tests: {len(TEST_SCENARIOS)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  Success rate: {passed/len(TEST_SCENARIOS)*100:.1f}%")
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()