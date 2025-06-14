"""Global pytest configuration for psh tests."""
import pytest
import sys
import os
from psh.shell import Shell


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "visitor_xfail(reason): mark test as expected to fail when using visitor executor"
    )


def pytest_collection_modifyitems(config, items):
    """Apply xfail marking to tests marked with visitor_xfail when using visitor executor."""
    # Check if visitor executor is being used
    use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
    
    # Also check if visitor executor is the default (would need to import Shell to check)
    # For now, we'll just use the environment variable
    
    if use_visitor:
        for item in items:
            # Check if test has visitor_xfail marker
            visitor_xfail_marker = item.get_closest_marker("visitor_xfail")
            if visitor_xfail_marker:
                reason = visitor_xfail_marker.kwargs.get("reason", "Test fails with visitor executor due to pytest output capture limitations")
                item.add_marker(pytest.mark.xfail(reason=f"Visitor executor: {reason}"))


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