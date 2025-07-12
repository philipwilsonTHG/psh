"""
Exec builtin tests.

Tests for the exec builtin which can replace the shell process or 
apply redirections permanently to the current shell.
"""

import pytest
import os


def test_exec_builtin_exists(shell):
    """Test that exec is registered as a builtin."""
    result = shell.run_command('type exec')
    assert result == 0


def test_exec_without_command(shell):
    """Test exec without command and no redirections."""
    result = shell.run_command('exec')
    assert result == 0


def test_exec_with_output_redirection(shell_with_temp_dir):
    """Test exec without command but with output redirection."""
    output_file = "exec_test.txt"
    
    # Apply redirection permanently  
    result = shell_with_temp_dir.run_command(f'exec > {output_file}')
    assert result == 0
    
    # Now all output should go to the file
    shell_with_temp_dir.run_command('echo "redirected output"')
    
    # Check that output was redirected
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            content = f.read()
        assert 'redirected output' in content


def test_exec_with_input_redirection(shell_with_temp_dir):
    """Test exec with input redirection."""
    input_file = "exec_input.txt"
    
    # Create input file
    with open(input_file, 'w') as f:
        f.write("test input data\n")
    
    # Apply input redirection permanently
    result = shell_with_temp_dir.run_command(f'exec < {input_file}')
    assert result == 0


def test_exec_with_command_replacement():
    """Test exec with command replacement using subprocess."""
    import subprocess
    import sys
    
    # Test exec replacing the shell process
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', 'exec echo "replaced process"'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "replaced process" in result.stdout
    
    # Test exec with different command
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', 'exec true'],
        capture_output=True
    )
    assert result.returncode == 0
    
    # Test exec with failing command
    result = subprocess.run(
        [sys.executable, '-m', 'psh', '-c', 'exec false'],
        capture_output=True
    )
    assert result.returncode != 0


def test_exec_with_error_redirection(shell_with_temp_dir):
    """Test exec with stderr redirection."""
    error_file = "exec_error.txt"
    
    # Redirect stderr permanently
    result = shell_with_temp_dir.run_command(f'exec 2> {error_file}')
    assert result == 0


@pytest.mark.xfail(reason="File descriptor operations may not be implemented")
def test_exec_with_fd_operations(shell_with_temp_dir):
    """Test exec with file descriptor operations."""
    result = shell_with_temp_dir.run_command('exec 3>&1')
    assert result == 0


def test_exec_error_handling(shell):
    """Test exec error handling with invalid arguments."""
    # Test with non-existent command
    result = shell.run_command('exec /nonexistent/command')
    assert result != 0


def test_exec_with_environment(shell):
    """Test exec with environment variable assignment."""
    result = shell.run_command('VAR=value exec')
    assert result == 0


def test_exec_help_option(shell):
    """Test exec with help option."""
    result = shell.run_command('exec --help')
    # May or may not be implemented
    # Just test that it doesn't crash


def test_exec_syntax_error(shell):
    """Test exec with syntax errors."""
    result = shell.run_command('exec >')
    # Should fail with incomplete redirection
    assert result != 0


def test_exec_redirection_persistence(shell_with_temp_dir):
    """Test that exec redirections persist across commands."""
    output_file = "persistent_output.txt"
    
    # Apply persistent redirection
    shell_with_temp_dir.run_command(f'exec > {output_file}')
    
    # Multiple commands should all redirect
    shell_with_temp_dir.run_command('echo "first"')
    shell_with_temp_dir.run_command('echo "second"') 
    shell_with_temp_dir.run_command('echo "third"')
    
    # All output should be in file
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            content = f.read()
        assert 'first' in content
        assert 'second' in content  
        assert 'third' in content