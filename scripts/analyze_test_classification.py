#!/usr/bin/env python3
"""
Analyze test classification in PSH conformance tests.

Identifies tests that may be misclassified based on their actual behavior.
"""

import subprocess
import sys
import os
import re

# Add PSH to path
PSH_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PSH_ROOT)


def check_single_command(command):
    """Check if a command works in both PSH and bash."""
    # Test in PSH
    psh_result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', command],
        capture_output=True,
        text=True
    )
    
    # Test in bash
    bash_result = subprocess.run(
        ['bash', '-c', command],
        capture_output=True,
        text=True
    )
    
    return {
        'command': command,
        'psh_works': psh_result.returncode == 0,
        'bash_works': bash_result.returncode == 0,
        'psh_output': psh_result.stdout.strip(),
        'bash_output': bash_result.stdout.strip(),
        'outputs_match': psh_result.stdout.strip() == bash_result.stdout.strip()
    }


def analyze_common_misclassifications():
    """Test common commands that might be misclassified."""
    
    test_commands = [
        # Basic expansions
        'echo ${HOME}',
        'echo ${PATH}',
        'echo ${USER}',
        
        # Parameter expansions
        'x=hello; echo ${x}',
        'x=hello; echo ${#x}',
        'x=hello; echo ${x:-default}',
        'x=hello; echo ${x:+set}',
        
        # Command substitution
        'echo $(echo hello)',
        'echo `echo hello`',
        
        # Basic arithmetic
        'echo $((1 + 1))',
        'echo $((10 - 5))',
        
        # Common builtins
        'type echo',
        'type cd',
        'export TEST_VAR=value',
        'env | grep TEST_VAR',
        
        # Job control
        'jobs',
        'echo $!',
        'echo $$',
        
        # Arrays (bash-specific but often tested)
        'arr=(1 2 3); echo ${arr[0]}',
        'declare -a arr',
        
        # Functions
        'f() { echo hello; }; f',
        'function g { echo world; }; g',
    ]
    
    results = []
    for cmd in test_commands:
        try:
            result = check_single_command(cmd)
            results.append(result)
        except Exception as e:
            results.append({
                'command': cmd,
                'error': str(e)
            })
    
    return results


def print_analysis(results):
    """Print analysis of test results."""
    
    print("PSH Test Classification Analysis")
    print("=" * 60)
    print()
    
    # Categorize results
    both_work = []
    only_bash = []
    only_psh = []
    neither = []
    errors = []
    
    for r in results:
        if 'error' in r:
            errors.append(r)
        elif r['psh_works'] and r['bash_works']:
            both_work.append(r)
        elif r['bash_works'] and not r['psh_works']:
            only_bash.append(r)
        elif r['psh_works'] and not r['bash_works']:
            only_psh.append(r)
        else:
            neither.append(r)
    
    # Print categories
    if both_work:
        print(f"Commands that work in BOTH shells ({len(both_work)}):")
        print("-" * 60)
        for r in both_work:
            status = "✓ IDENTICAL" if r['outputs_match'] else "⚠ DIFFERENT OUTPUT"
            print(f"{status}: {r['command']}")
            if not r['outputs_match']:
                print(f"  PSH:  '{r['psh_output']}'")
                print(f"  Bash: '{r['bash_output']}'")
        print()
    
    if only_bash:
        print(f"Commands that work ONLY in bash ({len(only_bash)}):")
        print("-" * 60)
        for r in only_bash:
            print(f"✗ {r['command']}")
        print()
    
    if only_psh:
        print(f"Commands that work ONLY in PSH ({len(only_psh)}):")
        print("-" * 60)
        for r in only_psh:
            print(f"? {r['command']}")
        print()
    
    if neither:
        print(f"Commands that fail in BOTH shells ({len(neither)}):")
        print("-" * 60)
        for r in neither:
            print(f"✗ {r['command']}")
        print()
    
    if errors:
        print(f"Commands with test errors ({len(errors)}):")
        print("-" * 60)
        for r in errors:
            print(f"ERROR: {r['command']} - {r['error']}")
        print()
    
    # Summary
    print("Summary:")
    print("-" * 60)
    total = len(results)
    print(f"Total commands tested: {total}")
    print(f"Work in both shells: {len(both_work)} ({len(both_work)/total*100:.1f}%)")
    print(f"  - Identical output: {sum(1 for r in both_work if r['outputs_match'])}")
    print(f"  - Different output: {sum(1 for r in both_work if not r['outputs_match'])}")
    print(f"Only work in bash: {len(only_bash)} ({len(only_bash)/total*100:.1f}%)")
    print(f"PSH-specific: {len(only_psh)} ({len(only_psh)/total*100:.1f}%)")
    print(f"Fail in both: {len(neither)} ({len(neither)/total*100:.1f}%)")
    print(f"Test errors: {len(errors)} ({len(errors)/total*100:.1f}%)")


if __name__ == '__main__':
    results = analyze_common_misclassifications()
    print_analysis(results)
    
    # Return non-zero if there are potential misclassifications
    misclassified = sum(1 for r in results 
                       if not r.get('error') 
                       and r['psh_works'] 
                       and r['bash_works'] 
                       and r['outputs_match'])
    
    if misclassified > 10:
        print(f"\n⚠️  Found {misclassified} commands that work identically in both shells.")
        print("These might be misclassified as 'not implemented' in conformance tests.")
        sys.exit(1)