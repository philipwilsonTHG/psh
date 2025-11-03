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

    # Ensure subprocesses can import the local psh package when invoked via
    # ``python -m psh`` by propagating the repository root through PYTHONPATH.
    repo_root = os.path.dirname(os.path.abspath(__file__))
    existing = os.environ.get('PYTHONPATH')
    path_entries = [repo_root]
    if existing:
        path_entries.append(existing)
    os.environ['PYTHONPATH'] = os.pathsep.join(path_entries)


def pytest_collection_modifyitems(config, items):
    """Apply xfail marking to tests marked with visitor_xfail."""
    # Visitor executor is now the only executor
    # All tests marked with visitor_xfail should be expected to fail
    for item in items:
        # Check if test has visitor_xfail marker
        visitor_xfail_marker = item.get_closest_marker("visitor_xfail")
        if visitor_xfail_marker:
            reason = visitor_xfail_marker.kwargs.get("reason", "Test fails due to pytest output capture limitations with forked processes")
            item.add_marker(pytest.mark.xfail(reason=reason))


@pytest.fixture
def shell():
    """Create a clean shell instance for testing."""
    # Save original file descriptors
    original_stdin = os.dup(0)
    original_stdout = os.dup(1) 
    original_stderr = os.dup(2)
    
    # Create shell instance - visitor executor is now the only executor
    shell_instance = Shell()
    
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
