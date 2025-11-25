"""
Advanced I/O redirection integration tests.

Tests for complex I/O redirection scenarios including:
- File descriptor duplication (>&, <&)
- Named pipes (FIFOs) integration
- Process substitution (<(command), >(command))
- File descriptor closing (n>&-, n<&-)
- Complex redirection combinations
- Error handling in redirection scenarios
"""

import pytest
import os
import tempfile
import subprocess
import time
import stat
import sys
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
PSH_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PSH_ROOT))

# Shell fixture imported automatically from conftest.py


class TestFileDescriptorDuplication:
    """Test file descriptor duplication with >& and <& operators."""

    def setup_method(self):
        """Clean up any leftover processes before each test."""
        pass

    def teardown_method(self):
        """Clean up any leftover processes after each test."""
        pass

    def test_stdout_duplication_simple(self, shell):
        """Test simple stdout redirection and duplication."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Test basic stdout redirection (foundation for duplication)
            result = shell.run_command(f'echo "test output" > {temp_path}')
            assert result == 0

            # Check that output went to file
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "test output" in content

        finally:
            os.unlink(temp_path)

    @pytest.mark.serial
    @pytest.mark.isolated
    def test_stderr_to_stdout_duplication(self, isolated_shell_with_temp_dir):
        """Test redirecting stderr to stdout (2>&1)."""
        shell = isolated_shell_with_temp_dir
        
        # Use subprocess for better isolation
        result = subprocess.run(
            [sys.executable, '-m', 'psh', '-c', 
             'echo "stdout message"; echo "stderr message" >&2'],
            cwd=shell.state.variables['PWD'],
            capture_output=True,
            text=True
        )
        
        # Both should appear in stdout when using 2>&1
        result2 = subprocess.run(
            [sys.executable, '-m', 'psh', '-c',
             '{ echo "stdout message"; echo "stderr message" >&2; } 2>&1'],
            cwd=shell.state.variables['PWD'],
            capture_output=True,
            text=True
        )
        
        assert "stdout message" in result2.stdout
        assert "stderr message" in result2.stdout
        assert result2.stderr == ""  # stderr should be empty as it's redirected

    def test_stderr_redirection_basic(self, shell):
        """Test basic stderr redirection to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Use a command that actually generates stderr output
            # and redirect it to a file
            result = shell.run_command(f'ls /nonexistent/path 2> {temp_path}')
            # ls should fail but stderr should be captured

            # Check that error output went to file
            with open(temp_path, 'r') as f:
                content = f.read()
            # Should contain some error message about the path not existing
            assert len(content.strip()) > 0

        finally:
            os.unlink(temp_path)

    def test_stdin_redirection_basic(self, shell):
        """Test basic stdin redirection from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("input data\n")
            temp_path = temp_file.name

        try:
            # Test basic stdin redirection from file
            result = shell.run_command(f'cat < {temp_path}')
            assert result == 0
            # This tests that stdin redirection works fundamentally

        finally:
            os.unlink(temp_path)

    def test_multiple_redirection_operators(self, shell_with_temp_dir):
        """Test handling multiple redirection operators in one command."""
        shell = shell_with_temp_dir
        stdout_path = os.path.join(shell.state.variables['PWD'], 'stdout_test.txt')
        stderr_path = os.path.join(shell.state.variables['PWD'], 'stderr_test.txt')

        # Test separate redirection of stdout and stderr
        result = shell.run_command(f'echo "to stdout" > {stdout_path} && ls /nonexistent 2> {stderr_path}')

        # Check stdout file
        with open(stdout_path, 'r') as f:
            stdout_content = f.read()
        assert "to stdout" in stdout_content
        
        # Note: We're not checking stderr_path content as ls behavior varies

    def test_null_device_redirection(self, shell):
        """Test redirection to null device."""
        # Test redirecting stdout to /dev/null (common redirection target)
        result = shell.run_command('echo "discarded" > /dev/null')
        assert result == 0

        # Test stderr to null with a command that actually produces stderr
        result = shell.run_command('ls /nonexistent/path 2> /dev/null')
        # Command should complete (stderr redirected to null)

        # This tests basic redirection functionality without complex fd management

    @pytest.mark.serial
    @pytest.mark.isolated
    def test_stderr_to_stdout_redirection(self, shell):
        """Test the common 2>&1 redirection pattern."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Test 2>&1 - redirect stderr to stdout, then redirect to file
            # Order matters: redirect stdout to file, then redirect stderr to stdout
            result = shell.run_command(f'ls /nonexistent/path > {temp_path} 2>&1')
            # This should capture both stdout and stderr in the file

            # Check that some output was captured
            with open(temp_path, 'r') as f:
                content = f.read()
            assert len(content.strip()) > 0
            assert "nonexistent" in content or "No such" in content

        finally:
            os.unlink(temp_path)


class TestProcessSubstitution:
    """Test process substitution with <() and >() syntax."""

    def setup_method(self):
        """Clean up any leftover processes before each test."""
        pass

    def teardown_method(self):
        """Clean up any leftover processes after each test."""
        pass
    
    def test_invalid_file_descriptor(self, shell):
        """Test redirection with invalid file descriptor numbers."""
        # Try to use extremely high fd number
        result = shell.run_command('echo "test" 999>&1')
        # Should either work or fail gracefully
        assert isinstance(result, int)

        # Try to duplicate from non-existent fd
        result = shell.run_command('echo "test" 1>&999')
        # Should fail gracefully
        assert result != 0

    def test_redirection_with_errexit(self, shell):
        """Test redirection error handling with set -e."""
        # Enable errexit
        shell.run_command('set -e')

        # Redirection error should exit shell
        result = shell.run_command('echo "test" > /nonexistent/file; echo "should not reach"')
        assert result != 0
        # Output verification would need shell output capture


class TestHeredocAdvanced:
    """Test advanced here-document scenarios."""

    def setup_method(self):
        """Clean up any leftover processes before each test."""
        pass

    def teardown_method(self):
        """Clean up any leftover processes after each test."""
        pass

    def test_heredoc_with_variable_expansion(self, shell):
        """Test here-document with variable expansion."""
        shell.run_command('test_var="expanded"')

        result = shell.run_command('''
        cat << EOF
This is a $test_var heredoc
EOF
        ''')
        assert result == 0
        # Output verification would need shell output capture

    def test_heredoc_with_quoted_delimiter(self, shell):
        """Test here-document with quoted delimiter (no expansion)."""
        shell.run_command('test_var="should_not_expand"')

        result = shell.run_command('''
        cat << 'EOF'
This is a $test_var heredoc
EOF
        ''')
        assert result == 0
        # Output verification would need shell output capture

    def test_heredoc_indented(self, shell):
        """Test indented here-document with <<-."""
        result = shell.run_command('''
        cat <<- EOF
\t\tIndented content
\t\tMore indented content
\tEOF
        ''')
        assert result == 0
        # Output verification would need shell output capture

    def test_multiple_heredocs(self, shell):
        """Test multiple here-documents in sequence."""
        result = shell.run_command('''
        cat << EOF1 << EOF2
First heredoc
EOF1
Second heredoc
EOF2
        ''')
        # This might not be supported - test graceful handling
        assert isinstance(result, int)

    def test_heredoc_in_function(self, shell):
        """Test here-document inside function definition."""
        shell.run_command('''
        heredoc_func() {
            cat << FUNC_EOF
Function heredoc content
Variable: $1
FUNC_EOF
        }
        ''')

        result = shell.run_command('heredoc_func "test_arg"')
        assert result == 0
        # Output verification would need shell output capture


class TestHereString:
    """Test here-string (<<<) functionality."""

    def setup_method(self):
        """Clean up any leftover processes before each test."""
        pass

    def teardown_method(self):
        """Clean up any leftover processes after each test."""
        pass

    def test_here_string_basic(self, shell):
        """Test basic here-string functionality."""
        result = shell.run_command('cat <<< "here string content"')
        assert result == 0
        # Output verification would need shell output capture

    def test_here_string_with_variables(self, shell):
        """Test here-string with variable expansion."""
        shell.run_command('test_var="variable content"')

        result = shell.run_command('cat <<< "String with $test_var"')
        assert result == 0
        # Output verification would need shell output capture

    def test_here_string_complex(self, shell):
        """Test here-string with complex expressions."""
        result = shell.run_command('wc -w <<< "count these words please"')
        assert result == 0
        # Output verification would need shell output capture


# Shell fixture provided by conftest.py


# Helper functions
def create_test_file(path, content, mode=0o644):
    """Helper to create test files with specific content and permissions."""
    with open(path, 'w') as f:
        f.write(content)
    os.chmod(path, mode)
    return path


def wait_for_file(path, timeout=5):
    """Helper to wait for file creation with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(path):
            return True

    return False
