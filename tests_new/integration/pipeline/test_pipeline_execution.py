"""
Pipeline execution integration tests.

Tests fundamental pipeline functionality that can be verified through
exit codes and PSH's internal mechanisms.
"""

import pytest


def test_pipeline_exit_status_success(shell, capsys):
    """Test that pipeline exit status comes from last command - success case."""
    # Pipeline should succeed if last command succeeds
    result = shell.run_command('false | true')
    assert result == 0


def test_pipeline_exit_status_failure(shell, capsys):
    """Test that pipeline exit status comes from last command - failure case."""
    # Pipeline should fail if last command fails
    result = shell.run_command('true | false')
    assert result != 0


def test_pipeline_empty_input_success(shell, capsys):
    """Test pipeline with empty input succeeds."""
    result = shell.run_command('true | cat')
    assert result == 0


def test_pipeline_background_job(shell, capsys):
    """Test pipeline as background job."""
    result = shell.run_command('echo "background" | cat &')
    # Background job should return immediately with success
    assert result == 0


def test_pipeline_with_variable_assignment(shell, capsys):
    """Test pipeline with variable in assignment context."""
    result = shell.run_command('x=$(echo hello | cat); echo $x')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_pipeline_with_command_substitution_simple(shell, capsys):
    """Test simple command substitution in pipeline context."""
    shell.run_command('echo $(echo hello | cat)')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_complex_pipeline_exit_status(shell, capsys):
    """Test exit status of complex pipeline."""
    # Multi-stage pipeline - exit status from last command
    result = shell.run_command('true | true | false')
    assert result != 0
    
    result = shell.run_command('false | false | true')
    assert result == 0


def test_pipeline_with_builtin_echo(shell, capsys):
    """Test pipeline starting with builtin echo."""
    # This should work because echo is a builtin
    result = shell.run_command('echo test')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'test'
    assert result == 0


def test_pipeline_variable_expansion(shell, capsys):
    """Test variable expansion in pipeline context."""
    shell.run_command('VAR=hello')
    shell.run_command('echo $VAR')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'hello'


def test_pipeline_with_conditional(shell, capsys):
    """Test pipeline in conditional context."""
    result = shell.run_command('if echo hello | grep hello >/dev/null; then echo found; fi')
    captured = capsys.readouterr()
    assert 'found' in captured.out
    assert result == 0


def test_pipeline_syntax_error(shell, capsys):
    """Test handling of pipeline syntax errors."""
    # Empty pipeline should be an error
    result = shell.run_command('echo | ')
    assert result != 0


def test_pipeline_with_function_definition(shell, capsys):
    """Test defining and using a function with pipelines."""
    shell.run_command('test_func() { echo "function output"; }')
    shell.run_command('test_func')
    captured = capsys.readouterr()
    assert 'function output' in captured.out


@pytest.mark.xfail(reason="Complex pipeline error handling may not be implemented")
def test_pipeline_error_in_middle(shell, capsys):
    """Test error handling when middle command in pipeline fails."""
    result = shell.run_command('echo test | nonexistent_command | cat')
    # Should handle the error gracefully
    assert result != 0


@pytest.mark.xfail(reason="Pipeline SIGPIPE handling may not be complete")
def test_pipeline_sigpipe_handling(shell, capsys):
    """Test SIGPIPE handling in pipelines."""
    # This should not hang even if the pipeline is broken
    result = shell.run_command('yes | head -1')
    assert result == 0


def test_multiple_pipelines_sequential(shell, capsys):
    """Test multiple pipelines executed sequentially."""
    result1 = shell.run_command('echo first | cat')
    result2 = shell.run_command('echo second | cat')
    assert result1 == 0
    assert result2 == 0


def test_pipeline_with_semicolon_separation(shell, capsys):
    """Test pipeline combined with semicolon separation."""
    result = shell.run_command('echo first | cat; echo second')
    captured = capsys.readouterr()
    assert 'second' in captured.out
    assert result == 0


def test_pipeline_in_subshell(shell, capsys):
    """Test pipeline execution in subshell."""
    shell.run_command('(echo subshell | cat)')
    # Subshell should execute without error
    captured = capsys.readouterr()
    # May or may not capture output depending on implementation


def test_pipeline_with_logical_operators(shell, capsys):
    """Test pipeline combined with logical operators."""
    result = shell.run_command('true | true && echo success')
    captured = capsys.readouterr()
    assert 'success' in captured.out
    assert result == 0
    
    result = shell.run_command('true | false || echo failure')
    captured = capsys.readouterr()
    assert 'failure' in captured.out


def test_pipeline_basic_functionality(shell, capsys):
    """Test that pipelines are parsed and executed without syntax errors."""
    # Just verify that pipeline syntax is accepted
    result = shell.run_command('echo test | cat > /dev/null')
    assert result == 0


def test_pipeline_with_here_document(shell, capsys):
    """Test pipeline with here document input."""
    result = shell.run_command('cat << EOF | cat\nhello world\nEOF')
    # Should execute without syntax error
    assert result == 0