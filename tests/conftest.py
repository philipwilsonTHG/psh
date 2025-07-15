"""
Pytest configuration for the new PSH test suite.

This provides fixtures and configuration specific to the organized test structure,
avoiding conflicts with the main test suite's conftest.py.
"""

import pytest
import os
import sys
from pathlib import Path
from io import StringIO

# Add PSH to path
PSH_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PSH_ROOT))

from psh.shell import Shell


@pytest.fixture
def shell():
    """Create a fresh shell instance for testing.
    
    This fixture creates a new Shell instance with clean state for each test.
    Unlike the main test suite, this doesn't capture output automatically.
    """
    shell = Shell()
    # Reset to clean state if method exists
    if hasattr(shell, 'reset_state'):
        shell.reset_state()
    return shell


@pytest.fixture
def clean_shell():
    """Create a shell instance with completely fresh environment.
    
    This fixture creates a shell with minimal environment setup,
    useful for testing core functionality without interference.
    """
    shell = Shell()
    if hasattr(shell, 'reset_state'):
        shell.reset_state()
    # Clear environment variables except essentials
    essential_vars = {'PATH', 'HOME', 'USER', 'SHELL'}
    for var in list(shell.state.variables.keys()):
        if var not in essential_vars:
            del shell.state.variables[var]
    return shell


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files.
    
    This fixture creates a temporary directory that is automatically
    cleaned up after the test completes.
    """
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp(prefix='psh_test_')
    original_cwd = os.getcwd()
    
    yield temp_dir
    
    # Cleanup
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def shell_with_temp_dir(shell, temp_dir):
    """Shell instance with a temporary working directory.
    
    This fixture provides a shell instance that operates in a temporary
    directory without changing the global Python working directory.
    This ensures thread safety for parallel test execution.
    """
    # Store original PWD
    original_pwd = shell.state.variables.get('PWD', os.getcwd())
    
    # Set shell's working directory without changing global cwd
    shell.state.variables['PWD'] = temp_dir
    
    yield shell
    
    # Restore original PWD
    shell.state.variables['PWD'] = original_pwd


@pytest.fixture
def isolated_shell_with_temp_dir(temp_dir):
    """Shell instance isolated from pytest's stream capture for redirection tests.
    
    This fixture creates a completely fresh shell instance that doesn't
    interfere with pytest's I/O capture, suitable for testing redirections.
    """
    from psh.shell import Shell
    import sys
    import os
    
    # Store original working directory and change to temp directory FIRST
    original_cwd = os.getcwd()
    original_pwd = os.environ.get('PWD', original_cwd)
    os.chdir(temp_dir)
    os.environ['PWD'] = temp_dir
    
    # Create a completely fresh shell instance (now in temp directory)
    shell = Shell()
    
    # Store original file descriptors to ensure proper cleanup
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    yield shell
    
    # Ensure streams are restored (defensive cleanup)
    sys.stdin = original_stdin
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    
    # Restore original working directory and PWD environment
    os.chdir(original_cwd)
    os.environ['PWD'] = original_pwd
    
    # Reset shell state to prevent leakage
    if hasattr(shell, 'reset_state'):
        shell.reset_state()


class MockStdout:
    """Mock stdout that captures output for testing."""
    
    def __init__(self):
        self.content = StringIO()
        
    def write(self, text):
        self.content.write(text)
        
    def flush(self):
        pass
        
    def getvalue(self):
        return self.content.getvalue()


class MockStderr:
    """Mock stderr that captures error output for testing."""
    
    def __init__(self):
        self.content = StringIO()
        
    def write(self, text):
        self.content.write(text)
        
    def flush(self):
        pass
        
    def getvalue(self):
        return self.content.getvalue()


@pytest.fixture
def captured_shell():
    """Shell with output capture for testing.
    
    This fixture provides a shell instance where stdout and stderr
    are captured properly, working around the executor's tendency
    to reset shell.stdout to sys.stdout.
    
    The approach: capture at the sys.stdout/stderr level during
    command execution, which is more reliable than trying to 
    intercept at the shell level.
    """
    # Create shell with captured I/O
    shell = Shell()
    
    # Store original sys streams
    original_sys_stdout = sys.stdout
    original_sys_stderr = sys.stderr
    
    # Create capture buffers
    captured_stdout = StringIO()
    captured_stderr = StringIO()
    
    # Store original run_command method
    original_run_command = shell.run_command
    
    def capturing_run_command(command_string, add_to_history=True):
        """Run command with output capture."""
        # Replace sys streams during execution
        sys.stdout = captured_stdout
        sys.stderr = captured_stderr
        
        try:
            result = original_run_command(command_string, add_to_history)
        finally:
            # Always restore
            sys.stdout = original_sys_stdout
            sys.stderr = original_sys_stderr
        
        return result
    
    # Replace run_command
    shell.run_command = capturing_run_command
    
    # Add helper methods
    shell.get_stdout = lambda: captured_stdout.getvalue()
    shell.get_stderr = lambda: captured_stderr.getvalue()
    shell.clear_output = lambda: (
        captured_stdout.truncate(0),
        captured_stdout.seek(0),
        captured_stderr.truncate(0),
        captured_stderr.seek(0)
    )
    
    yield shell
    
    # Cleanup
    sys.stdout = original_sys_stdout
    sys.stderr = original_sys_stderr


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests.
    
    This fixture automatically runs before each test to ensure
    a clean environment state.
    """
    # Store original environment
    original_cwd = os.getcwd()
    
    yield
    
    # Restore original state
    os.chdir(original_cwd)


@pytest.fixture
def isolated_subprocess_env():
    """Provide an isolated environment for subprocess tests.
    
    This fixture is specifically designed for tests that spawn
    PSH as a subprocess to ensure proper isolation in parallel execution.
    """
    import tempfile
    import subprocess
    
    # Create a unique temp directory for this test
    temp_dir = tempfile.mkdtemp(prefix=f'psh_test_{os.getpid()}_')
    
    # Create clean environment
    env = {
        'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
        'HOME': os.environ.get('HOME', '/tmp'),
        'USER': os.environ.get('USER', 'test'),
        'SHELL': os.environ.get('SHELL', '/bin/sh'),
        'TMPDIR': temp_dir,
        'TEMP': temp_dir,
        'TMP': temp_dir,
        'PYTHONPATH': str(PSH_ROOT),
        'PYTHONUNBUFFERED': '1',
    }
    
    yield {'env': env, 'cwd': temp_dir}
    
    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


# Test markers for categorizing tests
pytest_configure_node_id_parts = ["suite", "category", "component"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test isolated components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test component interactions"
    )
    config.addinivalue_line(
        "markers", "system: System tests that test end-to-end functionality"
    )
    config.addinivalue_line(
        "markers", "conformance: Tests that verify bash compatibility"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "interactive: Tests that require interactive shell features"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 1 second to run"
    )
    config.addinivalue_line(
        "markers", "serial: Tests that must run serially (no parallel execution)"
    )
    config.addinivalue_line(
        "markers", "isolated: Tests that need extra isolation"
    )
    config.addinivalue_line(
        "markers", "flaky: Tests that are known to be flaky in parallel execution"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    
    
    # Tests that need serial execution to avoid race conditions
    serial_tests = [
        "test_file_not_found_redirection",
        "test_permission_denied_redirection",
    ]
    
    # Mark tests that need special handling
    
    for item in items:
        # Add markers based on test file location
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "system/" in str(item.fspath):
            item.add_marker(pytest.mark.system)
        elif "conformance/" in str(item.fspath):
            item.add_marker(pytest.mark.conformance)
        elif "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            
        # Mark interactive tests
        if "interactive/" in str(item.fspath):
            item.add_marker(pytest.mark.interactive)
        
        # Mark tests that need serial execution
        if any(test_name in item.name for test_name in serial_tests):
            item.add_marker(pytest.mark.serial)
            item.add_marker(pytest.mark.isolated)
            
        # Mark error recovery tests as needing isolation
        if "test_error_recovery" in str(item.fspath):
            item.add_marker(pytest.mark.isolated)


# Skip interactive tests by default unless explicitly requested
def pytest_runtest_setup(item):
    """Skip interactive tests unless explicitly requested."""
    if item.get_closest_marker("interactive"):
        if not item.config.getoption("--run-interactive", default=False):
            pytest.skip("Interactive tests skipped (use --run-interactive to run)")
    
    # Clean up any lingering PSH processes before each test
    # This helps with isolation when running tests in parallel
    import subprocess
    try:
        subprocess.run(['pkill', '-f', f'python.*psh.*{os.getpid()}'], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
    
    # Handle serial tests in parallel execution
    if item.get_closest_marker("serial"):
        if hasattr(item.config, "workerinput"):
            # In parallel mode, only run on worker gw0
            worker_id = item.config.workerinput.get("workerid", "master")
            if worker_id != "gw0" and worker_id != "master":
                pytest.skip(f"Serial test skipped on worker {worker_id}")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-interactive",
        action="store_true",
        default=False,
        help="Run interactive tests (requires pexpect and terminal)"
    )
    parser.addoption(
        "--run-slow",
        action="store_true", 
        default=False,
        help="Run slow tests (performance benchmarks)"
    )
    parser.addoption(
        "--strict-isolation",
        action="store_true",
        default=False,
        help="Run with strict test isolation (slower but more reliable)"
    )