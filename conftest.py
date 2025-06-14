"""Global pytest configuration for psh tests."""
import pytest
import sys
import os
from psh.shell import Shell


@pytest.fixture
def shell():
    """Create a clean shell instance for testing."""
    # Save original file descriptors
    original_stdin = os.dup(0)
    original_stdout = os.dup(1) 
    original_stderr = os.dup(2)
    
    # Create shell instance - respect PSH_USE_VISITOR_EXECUTOR env var
    use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
    shell_instance = Shell(use_visitor_executor=use_visitor)
    
    try:
        yield shell_instance
    finally:
        # Ensure file descriptors are restored
        try:
            os.dup2(original_stdin, 0)
            os.dup2(original_stdout, 1)
            os.dup2(original_stderr, 2)
        except OSError:
            # File descriptors might already be closed
            pass
        finally:
            # Close the duplicated descriptors
            try:
                os.close(original_stdin)
                os.close(original_stdout)
                os.close(original_stderr)
            except OSError:
                pass