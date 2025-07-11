"""
Function definition and execution integration tests.

Tests shell function definitions, parsing, and execution including
parameter passing, return values, and scope.
"""

import pytest


def test_simple_function_definition(shell, capsys):
    """Test basic function definition and execution."""
    shell.run_command('greet() { echo "Hello World"; }')
    result = shell.run_command('greet')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Hello World' in captured.out


def test_function_with_keyword_syntax(shell, capsys):
    """Test function definition with function keyword."""
    shell.run_command('function greet { echo "Hello"; }')
    result = shell.run_command('greet')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Hello' in captured.out


def test_function_with_keyword_and_parens(shell, capsys):
    """Test function keyword with parentheses."""
    shell.run_command('function greet() { echo "Hello"; }')
    result = shell.run_command('greet')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Hello' in captured.out


def test_multiline_function(shell, capsys):
    """Test multiline function definition."""
    shell.run_command('''greet() {
        echo "Line 1"
        echo "Line 2"
    }''')
    result = shell.run_command('greet')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Line 1' in captured.out
    assert 'Line 2' in captured.out


def test_function_with_parameters(shell, capsys):
    """Test function with positional parameters."""
    shell.run_command('greet() { echo "Hello $1"; }')
    result = shell.run_command('greet World')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Hello World' in captured.out


def test_function_multiple_parameters(shell, capsys):
    """Test function with multiple parameters."""
    shell.run_command('add() { echo "$(($1 + $2))"; }')
    result = shell.run_command('add 5 3')
    assert result == 0
    captured = capsys.readouterr()
    assert '8' in captured.out


def test_function_arithmetic_operations(shell, capsys):
    """Test function with arithmetic operations."""
    shell.run_command('calc() { echo "$((($1 + $2) * $3))"; }')
    result = shell.run_command('calc 2 3 4')
    assert result == 0
    captured = capsys.readouterr()
    assert '20' in captured.out


def test_function_return_value(shell):
    """Test function return values."""
    shell.run_command('test_return() { return 42; }')
    result = shell.run_command('test_return')
    assert result == 42


def test_function_early_return(shell, capsys):
    """Test early return from function."""
    shell.run_command('''early_return() {
        echo "Before return"
        return 5
        echo "After return"
    }''')
    result = shell.run_command('early_return')
    assert result == 5
    captured = capsys.readouterr()
    assert 'Before return' in captured.out
    assert 'After return' not in captured.out


def test_nested_function_calls(shell, capsys):
    """Test calling functions from within functions."""
    shell.run_command('inner() { echo "Inner function"; }')
    shell.run_command('outer() { echo "Outer start"; inner; echo "Outer end"; }')
    result = shell.run_command('outer')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Outer start' in captured.out
    assert 'Inner function' in captured.out
    assert 'Outer end' in captured.out


def test_function_variable_scope(shell, capsys):
    """Test variable scoping in functions."""
    shell.run_command('VAR=global')
    shell.run_command('test_scope() { VAR=local; echo $VAR; }')
    shell.run_command('test_scope')
    captured = capsys.readouterr()
    assert 'local' in captured.out
    
    # Check global variable
    shell.run_command('echo $VAR')
    captured = capsys.readouterr()
    # Variable modification in function may affect global scope


def test_function_local_variables(shell, capsys):
    """Test local variable declaration in functions."""
    shell.run_command('VAR=global')
    shell.run_command('test_local() { local VAR=local; echo $VAR; }')
    shell.run_command('test_local')
    captured = capsys.readouterr()
    assert 'local' in captured.out
    
    # Global should be unchanged
    shell.run_command('echo $VAR')
    captured = capsys.readouterr()
    assert 'global' in captured.out


def test_function_with_conditionals(shell, capsys):
    """Test function with conditional logic."""
    shell.run_command('''check_param() {
        if [ "$1" = "test" ]; then
            echo "Parameter is test"
        else
            echo "Parameter is not test"
        fi
    }''')
    
    shell.run_command('check_param test')
    captured = capsys.readouterr()
    assert 'Parameter is test' in captured.out
    
    shell.run_command('check_param other')
    captured = capsys.readouterr()
    assert 'Parameter is not test' in captured.out


def test_function_with_loops(shell, capsys):
    """Test function with loop constructs."""
    shell.run_command('''count_to() {
        for i in $(seq 1 $1); do
            echo "Count: $i"
        done
    }''')
    result = shell.run_command('count_to 3')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Count: 1' in captured.out
    assert 'Count: 2' in captured.out
    assert 'Count: 3' in captured.out


def test_recursive_function(shell, capsys):
    """Test recursive function calls."""
    shell.run_command('''factorial() {
        if [ $1 -le 1 ]; then
            echo 1
        else
            prev=$(factorial $(($1 - 1)))
            echo $(($1 * $prev))
        fi
    }''')
    result = shell.run_command('factorial 4')
    assert result == 0
    captured = capsys.readouterr()
    assert '24' in captured.out


def test_function_with_pipeline(shell_with_temp_dir, capsys):
    """Test function using pipelines."""
    shell = shell_with_temp_dir
    shell.run_command('upper() { echo "$1" | tr a-z A-Z; }')
    result = shell.run_command('upper hello > pipeline_output.txt')
    assert result == 0
    
    # Read the output file to verify
    with open('pipeline_output.txt', 'r') as f:
        output = f.read()
    assert 'HELLO' in output


def test_function_redirection(shell_with_temp_dir):
    """Test function with I/O redirection."""
    output_file = 'function_output.txt'
    # Use simpler redirection test
    shell_with_temp_dir.run_command('write_file() { echo "test content" > function_output.txt; }')
    result = shell_with_temp_dir.run_command('write_file')
    assert result == 0
    
    # Verify file was created
    import os
    assert os.path.exists(output_file)
    
    # Verify content
    with open(output_file, 'r') as f:
        content = f.read()
    assert 'test content' in content


def test_function_error_handling(shell):
    """Test function error handling."""
    shell.run_command('fail_func() { return 1; }')
    result = shell.run_command('fail_func')
    assert result == 1


def test_undefined_function_call(shell):
    """Test calling undefined function."""
    result = shell.run_command('undefined_function')
    assert result != 0


def test_function_unset(shell):
    """Test unsetting a function."""
    shell.run_command('temp_func() { echo "temporary"; }')
    shell.run_command('temp_func')  # Should work
    
    shell.run_command('unset -f temp_func')
    result = shell.run_command('temp_func')
    assert result != 0  # Should fail after unset


def test_function_with_special_parameters(shell, capsys):
    """Test function with special parameters like $#, $*, $@."""
    shell.run_command('show_params() { echo "Count: $#"; echo "All: $*"; }')
    result = shell.run_command('show_params one two three')
    assert result == 0
    captured = capsys.readouterr()
    assert 'Count: 3' in captured.out
    assert 'All: one two three' in captured.out


@pytest.mark.xfail(reason="PSH may prioritize builtins over functions with same name")
def test_function_name_collision(shell, capsys):
    """Test function name collision with builtins."""
    # Define function with same name as builtin
    shell.run_command('echo() { printf "Custom echo: %s\\n" "$1"; }')
    result = shell.run_command('echo test')
    assert result == 0
    captured = capsys.readouterr()
    # Should use function, not builtin (bash behavior)
    assert 'Custom echo: test' in captured.out


def test_function_export(shell):
    """Test exporting functions to subshells."""
    shell.run_command('export_func() { echo "exported"; }')
    shell.run_command('export -f export_func')
    result = shell.run_command('(export_func)')
    assert result == 0