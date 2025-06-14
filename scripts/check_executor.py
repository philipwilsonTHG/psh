#!/usr/bin/env python3
"""
Check which executor is being used by PSH.
"""

import os
import sys
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psh.shell import Shell


def check_executor_mode():
    """Check various ways of enabling visitor executor."""
    print("PSH Executor Mode Check")
    print("=" * 60)
    print()
    
    # Test 1: Default mode
    shell = Shell()
    print(f"1. Default mode: {'Visitor' if shell.use_visitor_executor else 'Legacy'} executor")
    
    # Test 2: Command line flag
    shell = Shell(use_visitor_executor=True)
    print(f"2. With --visitor-executor flag: {'Visitor' if shell.use_visitor_executor else 'Legacy'} executor")
    
    # Test 3: Environment variable
    os.environ['PSH_USE_VISITOR_EXECUTOR'] = '1'
    shell = Shell()
    print(f"3. With PSH_USE_VISITOR_EXECUTOR=1: {'Visitor' if shell.use_visitor_executor else 'Legacy'} executor")
    del os.environ['PSH_USE_VISITOR_EXECUTOR']
    
    # Test 4: Shell option (we can't easily test runtime set -o, but we can set initial state)
    shell = Shell()
    shell.state.options['visitor-executor'] = True
    # Note: This won't work as expected because the option is checked during init
    # But we can show how to check the option
    print(f"4. Shell option visitor-executor: {shell.state.options.get('visitor-executor', False)}")
    
    print()
    print("Runtime option test:")
    print("-" * 40)
    
    # Test runtime option setting
    test_script = '''
echo "Initial executor: $(set -o | grep visitor-executor)"
set -o visitor-executor
echo "After set -o: $(set -o | grep visitor-executor)"
set +o visitor-executor  
echo "After set +o: $(set -o | grep visitor-executor)"
'''
    
    result = subprocess.run(
        ['python', '-m', 'psh', '-c', test_script],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"Error running test: {result.stderr}")
    
    print()
    print("Performance comparison:")
    print("-" * 40)
    
    # Simple performance test
    import time
    
    try:
        command = "echo hello > /dev/null"
        iterations = 100
        
        # Test legacy executor
        shell_legacy = Shell(use_visitor_executor=False)
        start = time.time()
        for _ in range(iterations):
            shell_legacy.run_command(command, add_to_history=False)
        legacy_time = time.time() - start
        
        # Test visitor executor
        shell_visitor = Shell(use_visitor_executor=True)
        start = time.time()
        for _ in range(iterations):
            shell_visitor.run_command(command, add_to_history=False)
        visitor_time = time.time() - start
        
        print(f"Legacy executor:  {legacy_time:.3f}s for {iterations} iterations")
        print(f"Visitor executor: {visitor_time:.3f}s for {iterations} iterations")
        print(f"Difference: {((visitor_time - legacy_time) / legacy_time * 100):.1f}%")
    except Exception as e:
        print(f"Error in performance test: {e}")


if __name__ == '__main__':
    check_executor_mode()