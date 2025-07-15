"""
Debug helpers for interactive tests.

These can be imported and used to debug failing tests.
"""

import sys
import time


def debug_spawn(shell):
    """Print debug info about spawned shell."""
    print(f"\n=== DEBUG: Shell spawn info ===")
    print(f"Alive: {shell.isalive()}")
    print(f"PID: {shell.pid}")
    print(f"Timeout: {shell.timeout}")
    
    # Try to read any initial output
    try:
        shell.read_nonblocking(size=1000, timeout=0.1)
    except:
        pass
    
    print(f"Buffer: {repr(shell.buffer)}")
    print(f"Before: {repr(shell.before)}")
    print("=== END DEBUG ===\n")


def debug_expect_failure(shell, pattern, exception):
    """Print debug info when expect fails."""
    print(f"\n=== DEBUG: Expect failure ===")
    print(f"Pattern: {pattern}")
    print(f"Exception: {exception}")
    print(f"Shell alive: {shell.isalive()}")
    
    # Try to read any pending output
    try:
        pending = shell.read_nonblocking(size=1000, timeout=0.1)
        print(f"Pending output: {repr(pending)}")
    except:
        print("No pending output")
    
    print(f"Buffer: {repr(shell.buffer)}")
    print(f"Before: {repr(shell.before)}")
    print("=== END DEBUG ===\n")


def add_debug_to_test(test_func):
    """Decorator to add debugging to a test."""
    def wrapper(self):
        print(f"\n=== Running test: {test_func.__name__} ===")
        try:
            result = test_func(self)
            print(f"=== Test {test_func.__name__} PASSED ===\n")
            return result
        except Exception as e:
            print(f"=== Test {test_func.__name__} FAILED: {e} ===\n")
            if hasattr(self, 'shell'):
                debug_expect_failure(self.shell, "unknown", e)
            raise
    return wrapper