"""Test that pushd preserves logical paths (symlinks)."""

import pytest
import os
import tempfile


def test_pushd_preserves_logical_path(captured_shell, temp_dir):
    """Test that pushd preserves logical paths like /tmp instead of resolving to physical paths."""
    # Create a symlink in our temp directory
    symlink_path = os.path.join(temp_dir, 'mylink')
    target_dir = os.path.join(temp_dir, 'target')
    os.mkdir(target_dir)
    os.symlink(target_dir, symlink_path)
    
    # Change to temp_dir first
    captured_shell.run_command(f'cd {temp_dir}')
    captured_shell.clear_output()
    
    # Now pushd to the symlink
    result = captured_shell.run_command(f'pushd {symlink_path}')
    assert result == 0
    
    output = captured_shell.get_stdout().strip()
    dirs = output.split()
    
    # First directory should be the symlink path, not the resolved path
    assert dirs[0] == symlink_path
    assert dirs[1] == temp_dir
    
    # Verify we're actually in the target directory
    captured_shell.clear_output()
    result = captured_shell.run_command('pwd -P')  # Physical path
    assert result == 0
    assert target_dir in captured_shell.get_stdout()


def test_pushd_tmp_directory(captured_shell):
    """Test pushd /tmp preserves the /tmp path instead of resolving to /private/tmp on macOS."""
    # This test is specifically for the conformance issue
    # On macOS, /tmp is a symlink to /private/tmp
    
    # Get initial directory from PWD to match what pushd uses
    captured_shell.run_command('echo $PWD > /tmp/initial_pwd.txt')
    with open('/tmp/initial_pwd.txt', 'r') as f:
        initial_pwd = f.read().strip()
    os.unlink('/tmp/initial_pwd.txt')
    
    # Now test pushd /tmp
    result = captured_shell.run_command('pushd /tmp')
    assert result == 0
    
    output = captured_shell.get_stdout().strip()
    dirs = output.split()
    
    # First directory should be /tmp, not /private/tmp
    assert dirs[0] == '/tmp'
    
    # The initial directory should be preserved as provided
    # It might be shown with ~ abbreviation
    assert initial_pwd in dirs[1] or dirs[1].startswith('~')


def test_pushd_updates_pwd_logically(captured_shell):
    """Test that pushd updates PWD to the logical path."""
    # Start in a known location
    captured_shell.run_command('cd /')
    captured_shell.clear_output()
    
    # pushd to /tmp
    captured_shell.run_command('pushd /tmp')
    captured_shell.clear_output()
    
    # Check that PWD is the logical path
    result = captured_shell.run_command('echo $PWD')
    assert result == 0
    assert captured_shell.get_stdout().strip() == '/tmp'
    
    # But pwd -P shows physical path (on macOS)
    captured_shell.clear_output()
    result = captured_shell.run_command('pwd -P 2>/dev/null || pwd')
    assert result == 0
    pwd_output = captured_shell.get_stdout().strip()
    # On macOS it would be /private/tmp, on Linux it would be /tmp
    assert pwd_output in ['/tmp', '/private/tmp']


def test_dirs_shows_logical_paths(captured_shell):
    """Test that dirs command shows logical paths."""
    # Clear any existing directory stack
    captured_shell.run_command('dirs -c')
    captured_shell.clear_output()
    
    # Push some directories including /tmp
    captured_shell.run_command('pushd /tmp')
    captured_shell.run_command('pushd /usr')
    captured_shell.clear_output()
    
    # Check dirs output
    result = captured_shell.run_command('dirs')
    assert result == 0
    
    output = captured_shell.get_stdout().strip()
    dirs = output.split()
    
    # Should show logical paths
    assert dirs[0] == '/usr'
    assert dirs[1] == '/tmp'
    # dirs[2] would be the original directory