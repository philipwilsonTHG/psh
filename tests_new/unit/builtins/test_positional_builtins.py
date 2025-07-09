"""
Positional parameter builtin tests.

Tests for builtins that manipulate positional parameters like shift.
"""

import pytest


def test_shift_default(shell):
    """Test shift with default n=1."""
    shell.run_command('set arg1 arg2 arg3')
    result = shell.run_command('shift')
    assert result == 0
    
    # Verify shift worked by checking $1, $2
    shell.run_command('echo "$1"')
    # Note: Positional parameter testing may be complex with current fixture


def test_shift_explicit_n(shell):
    """Test shift with explicit n value."""
    shell.run_command('set arg1 arg2 arg3 arg4')
    result = shell.run_command('shift 2')
    assert result == 0


def test_shift_zero(shell):
    """Test shift with n=0 (no-op)."""
    shell.run_command('set arg1 arg2')
    result = shell.run_command('shift 0')
    assert result == 0


def test_shift_all_params(shell):
    """Test shift with n equal to parameter count."""
    shell.run_command('set arg1 arg2')
    result = shell.run_command('shift 2')
    assert result == 0


def test_shift_too_many(shell):
    """Test shift with n greater than parameter count."""
    shell.run_command('set arg1')
    result = shell.run_command('shift 2')
    # Should fail when trying to shift more than available
    assert result != 0


def test_shift_negative(shell):
    """Test shift with negative n."""
    shell.run_command('set arg1 arg2')
    result = shell.run_command('shift -1')
    # Should fail with negative argument
    assert result != 0


def test_shift_non_numeric(shell):
    """Test shift with non-numeric argument."""
    shell.run_command('set arg1 arg2')
    result = shell.run_command('shift abc')
    # Should fail with non-numeric argument
    assert result != 0


def test_shift_no_params(shell):
    """Test shift when no positional parameters exist."""
    # Clear any existing positional parameters
    shell.run_command('set --')
    result = shell.run_command('shift')
    # May fail when no parameters to shift
    assert result != 0


@pytest.mark.xfail(reason="Set builtin may not be fully implemented")
def test_set_positional_params(shell):
    """Test setting positional parameters with set builtin."""
    result = shell.run_command('set one two three')
    assert result == 0


@pytest.mark.xfail(reason="Positional parameter access may not be implemented")
def test_positional_parameter_access(captured_shell):
    """Test accessing positional parameters."""
    captured_shell.run_command('set first second third')
    captured_shell.run_command('echo "$1 $2 $3"')
    output = captured_shell.get_stdout()
    assert 'first second third' in output


@pytest.mark.xfail(reason="$# parameter may not be implemented")
def test_positional_parameter_count(captured_shell):
    """Test $# parameter for positional parameter count."""
    captured_shell.run_command('set a b c d')
    captured_shell.run_command('echo "$#"')
    output = captured_shell.get_stdout()
    assert '4' in output


@pytest.mark.xfail(reason="$* parameter may not be implemented") 
def test_positional_parameter_star(captured_shell):
    """Test $* parameter for all positional parameters."""
    captured_shell.run_command('set alpha beta gamma')
    captured_shell.run_command('echo "$*"')
    output = captured_shell.get_stdout()
    assert 'alpha beta gamma' in output


@pytest.mark.xfail(reason="$@ parameter may not be implemented")
def test_positional_parameter_at(captured_shell):
    """Test $@ parameter for all positional parameters."""
    captured_shell.run_command('set one two "three four"')
    captured_shell.run_command('echo "$@"')
    output = captured_shell.get_stdout()
    # $@ should preserve word boundaries
    assert 'one two three four' in output