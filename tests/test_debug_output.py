"""Debug test to understand output capture issues."""

import pytest
import sys
import os
from io import StringIO
from psh.shell import Shell


def test_debug_legacy_executor():
    """Debug output with legacy executor."""
    print("\n=== LEGACY EXECUTOR DEBUG ===")
    
    # Create shell with legacy executor
    shell = Shell()
    # Check stdout
    print(f"shell.stdout: {shell.stdout}")
    print(f"shell.state.stdout: {shell.state.stdout}")
    print(f"sys.stdout: {sys.stdout}")
    
    # Run echo command
    shell.run_command('echo test')
    

def test_debug_visitor_executor():
    """Debug output with visitor executor."""
    print("\n=== VISITOR EXECUTOR DEBUG ===")
    
    # Create shell with visitor executor
    shell = Shell()
    # Check stdout
    print(f"shell.stdout: {shell.stdout}")
    print(f"shell.state.stdout: {shell.state.stdout}")
    print(f"sys.stdout: {sys.stdout}")
    
    # Run echo command
    shell.run_command('echo test')


def test_debug_with_capture():
    """Debug with manual capture."""
    print("\n=== MANUAL CAPTURE DEBUG ===")
    
    # Save original
    orig_stdout = sys.stdout
    
    # Create capture
    capture = StringIO()
    sys.stdout = capture
    
    # Create shell
    shell = Shell()
    shell.stdout = capture
    shell.state.stdout = capture
    
    print(f"Before echo - capture value: '{capture.getvalue()}'")
    
    # Run echo
    shell.run_command('echo test')
    
    # Restore and check
    sys.stdout = orig_stdout
    captured = capture.getvalue()
    print(f"After echo - captured: '{captured}'")
    
    assert 'test' in captured