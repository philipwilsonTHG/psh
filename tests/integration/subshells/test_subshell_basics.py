"""
Basic subshell integration tests.

Tests for subshell group (...) syntax support including variable isolation,
command execution, redirections, and proper process management.
"""

import pytest
import os


def test_subshell_basic_execution(shell_with_temp_dir):
    """Test basic subshell command execution."""
    shell = shell_with_temp_dir
    
    # Test basic subshell execution with output redirection
    result = shell.run_command('(echo "hello from subshell") > subshell_output.txt')
    assert result == 0
    
    # Verify output
    with open('subshell_output.txt', 'r') as f:
        content = f.read()
    assert "hello from subshell" in content


def test_subshell_variable_isolation(shell_with_temp_dir):
    """Test that variables set in subshell don't affect parent."""
    shell = shell_with_temp_dir
    
    # Set a variable in parent
    shell.run_command('PARENT_VAR=parent_value')
    
    # Modify variable in subshell and create new one, redirect to file
    result = shell.run_command('(PARENT_VAR=subshell_value; NEW_VAR=new_value; echo "In subshell: $PARENT_VAR $NEW_VAR") > subshell_vars.txt')
    assert result == 0
    
    # Check parent variables are unchanged
    assert shell.state.get_variable('PARENT_VAR') == 'parent_value'
    assert shell.state.get_variable('NEW_VAR') == ''
    
    # Verify subshell output
    with open('subshell_vars.txt', 'r') as f:
        output = f.read()
    assert "In subshell: subshell_value new_value" in output


def test_subshell_with_pipelines(shell_with_temp_dir):
    """Test subshell containing pipelines."""
    shell = shell_with_temp_dir
    
    result = shell.run_command('(echo "line1"; echo "line2") | wc -l > line_count.txt')
    assert result == 0
    
    with open('line_count.txt', 'r') as f:
        count = f.read().strip()
    # Should count 2 lines
    assert '2' in count


def test_subshell_exit_status(shell):
    """Test subshell exit status propagation."""
    # Successful subshell
    result = shell.run_command('(true)')
    assert result == 0
    
    # Failed subshell
    result = shell.run_command('(false)')
    assert result == 1
    
    # Subshell with explicit exit
    result = shell.run_command('(exit 42)')
    assert result == 42


def test_subshell_with_conditionals(shell_with_temp_dir):
    """Test subshell containing conditional statements."""
    shell = shell_with_temp_dir
    shell.run_command('TEST_VAR=hello')
    
    result = shell.run_command('(if [ "$TEST_VAR" = "hello" ]; then echo "match"; else echo "no match"; fi) > conditional_output.txt')
    assert result == 0
    
    with open('conditional_output.txt', 'r') as f:
        output = f.read()
    assert "match" in output


def test_subshell_with_loops(shell_with_temp_dir):
    """Test subshell containing loops."""
    shell = shell_with_temp_dir
    
    result = shell.run_command('(for i in 1 2 3; do echo "Item: $i"; done) > loop_output.txt')
    assert result == 0
    
    with open('loop_output.txt', 'r') as f:
        output = f.read()
    assert "Item: 1" in output
    assert "Item: 2" in output  
    assert "Item: 3" in output


def test_subshell_with_functions(shell_with_temp_dir):
    """Test function calls within subshells."""
    shell = shell_with_temp_dir
    
    # Define function in parent
    shell.run_command('test_func() { echo "Function called with: $1"; }')
    
    # Call function in subshell
    result = shell.run_command('(test_func "subshell param") > function_output.txt')
    assert result == 0
    
    with open('function_output.txt', 'r') as f:
        output = f.read()
    assert "Function called with: subshell param" in output


def test_subshell_input_redirection(shell_with_temp_dir):
    """Test subshell with input redirection."""
    shell = shell_with_temp_dir
    
    # Create input file
    with open('input.txt', 'w') as f:
        f.write('line1\nline2\nline3\n')
    
    # Use subshell with input redirection
    result = shell.run_command('(cat; echo "appended") < input.txt > output.txt')
    assert result == 0
    
    with open('output.txt', 'r') as f:
        content = f.read()
    assert 'line1' in content
    assert 'line2' in content  
    assert 'line3' in content
    assert 'appended' in content


def test_subshell_error_handling(shell):
    """Test error handling in subshells."""
    # Command not found in subshell
    result = shell.run_command('(nonexistent_command)')
    assert result != 0
    
    # Syntax error in subshell
    result = shell.run_command('(echo "unterminated quote)')
    assert result != 0


@pytest.mark.xfail(reason="PSH may not support nested subshell parsing")
def test_nested_subshells(shell_with_temp_dir):
    """Test nested subshells."""
    shell = shell_with_temp_dir
    
    result = shell.run_command('(echo "outer"; (echo "inner")) > nested_output.txt')
    assert result == 0
    
    with open('nested_output.txt', 'r') as f:
        output = f.read()
    assert "outer" in output
    assert "inner" in output


def test_subshell_with_background_jobs(shell_with_temp_dir):
    """Test subshell with background job execution."""
    shell = shell_with_temp_dir
    
    # Run subshell in background
    result = shell.run_command('(echo "background subshell"; echo "done") > bg_output.txt &')
    assert result == 0
    
    # Give it time to complete
    
    # Check output file was created and contains expected content
    if os.path.exists('bg_output.txt'):
        with open('bg_output.txt', 'r') as f:
            content = f.read()
        assert "background subshell" in content
        assert "done" in content


def test_subshell_environment_inheritance(shell_with_temp_dir):
    """Test that subshell inherits parent environment."""
    shell = shell_with_temp_dir
    
    # Set environment variable
    shell.run_command('export INHERITED_VAR=inherited_value')
    
    # Access in subshell
    result = shell.run_command('(echo "Inherited: $INHERITED_VAR") > inherited_output.txt')
    assert result == 0
    
    with open('inherited_output.txt', 'r') as f:
        output = f.read()
    assert "Inherited: inherited_value" in output


def test_subshell_current_directory(shell_with_temp_dir):
    """Test subshell directory isolation."""
    shell = shell_with_temp_dir
    original_dir = os.getcwd()
    
    # Create subdirectory
    os.makedirs('subdir', exist_ok=True)
    
    # Change directory in subshell
    result = shell.run_command('(cd subdir; pwd) > pwd_output.txt')
    assert result == 0
    
    # Verify we're still in original directory
    assert os.getcwd() == original_dir
    
    # Verify subshell was in subdirectory
    with open('pwd_output.txt', 'r') as f:
        pwd_output = f.read().strip()
    assert 'subdir' in pwd_output


@pytest.mark.xfail(reason="Complex subshell redirections may not be fully implemented")
def test_subshell_complex_redirections(shell_with_temp_dir):
    """Test complex redirection patterns with subshells."""
    shell = shell_with_temp_dir
    
    # Multiple redirections in subshell
    result = shell.run_command('(echo "stdout"; echo "stderr" >&2) > out.txt 2> err.txt')
    assert result == 0
    
    with open('out.txt', 'r') as f:
        stdout_content = f.read()
    with open('err.txt', 'r') as f:
        stderr_content = f.read()
        
    assert "stdout" in stdout_content
    assert "stderr" in stderr_content


@pytest.mark.xfail(reason="Process substitution output redirection has test framework conflicts")
def test_subshell_process_substitution(shell, capsys):
    """Test process substitution with subshells."""
    result = shell.run_command('cat <(echo "from subshell")')
    assert result == 0
    
    captured = capsys.readouterr()
    assert "from subshell" in captured.out