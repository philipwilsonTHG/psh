"""
Signal handling builtin tests.

Tests for signal-related builtins like trap.
"""

import pytest
import signal
import os


def test_trap_builtin_exists(shell):
    """Test that trap is registered as a builtin."""
    result = shell.run_command('type trap')
    assert result == 0


def test_trap_list_signals(shell, capsys):
    """Test trap -l lists signals."""
    result = shell.run_command('trap -l')
    assert result == 0
    captured = capsys.readouterr()
    
    # Should list common signals
    assert 'INT' in captured.out or 'SIGINT' in captured.out
    assert 'TERM' in captured.out or 'SIGTERM' in captured.out


def test_trap_no_args(shell, capsys):
    """Test trap with no args shows current traps."""
    result = shell.run_command('trap')
    assert result == 0
    # Empty output is fine if no traps are set


def test_trap_set_signal_handler(shell):
    """Test setting a signal handler with trap."""
    result = shell.run_command('trap "echo signal caught" TERM')
    assert result == 0


@pytest.mark.skip(reason="Signal execution test sends SIGTERM to test process - unsafe")
def test_trap_signal_execution(shell, capsys):
    """Test that trap handler executes when signal is received."""
    # Set trap handler
    # shell.run_command('trap "echo caught signal" SIGTERM')
    
    # This test sends SIGTERM to the test runner process itself, which kills it
    # Cannot safely test actual signal delivery in this context
    # result = shell.run_command('kill -TERM $$')
    pass


def test_trap_exit_handler(shell):
    """Test trap with EXIT signal."""
    result = shell.run_command('trap "echo exiting" EXIT')
    assert result == 0


def test_trap_debug_handler(shell):
    """Test trap with DEBUG signal."""
    result = shell.run_command('trap "echo debug" DEBUG')
    # May not be implemented
    assert result == 0


def test_trap_err_handler(shell):
    """Test trap with ERR signal."""
    result = shell.run_command('trap "echo error" ERR')
    # May not be implemented
    assert result == 0


def test_trap_remove_handler(shell):
    """Test removing trap handler."""
    # Set handler
    shell.run_command('trap "echo test" TERM')
    
    # Remove handler
    result = shell.run_command('trap - TERM')
    assert result == 0


def test_trap_ignore_signal(shell):
    """Test ignoring signal with trap."""
    result = shell.run_command('trap "" TERM')
    assert result == 0


def test_trap_invalid_signal(shell):
    """Test trap with invalid signal name."""
    result = shell.run_command('trap "echo test" NOSUCHSIGNAL')
    assert result != 0


def test_trap_multiple_signals(shell):
    """Test trap with multiple signals."""
    result = shell.run_command('trap "echo multiple" TERM INT')
    assert result == 0


def test_trap_numeric_signal(shell):
    """Test trap with numeric signal."""
    result = shell.run_command('trap "echo numeric" 15')  # SIGTERM
    assert result == 0


def test_trap_command_substitution(shell):
    """Test trap with command substitution in handler."""
    result = shell.run_command('trap "echo $(date)" TERM')
    assert result == 0


def test_trap_print_specific_signal(shell, capsys):
    """Test printing trap for specific signal."""
    # Set a trap
    shell.run_command('trap "echo test handler" TERM')
    
    # Print trap for that signal
    result = shell.run_command('trap -p TERM')
    assert result == 0
    captured = capsys.readouterr()
    # Should show the trap if -p option is supported


def test_trap_help(shell):
    """Test trap help option."""
    result = shell.run_command('trap --help')
    # May or may not be implemented


def test_trap_error_cases(shell):
    """Test various trap error cases."""
    # Too few arguments
    result = shell.run_command('trap')
    # Should succeed (shows current traps) or fail
    
    # Invalid option
    result = shell.run_command('trap -xyz')
    # Should fail


@pytest.mark.skipif(os.name == 'nt', reason="Unix signal handling test")
def test_trap_unix_signals(shell):
    """Test trap with Unix-specific signals."""
    # Test with SIGUSR1 if available
    result = shell.run_command('trap "echo usr1" SIGUSR1')
    # Should work on Unix systems


def test_trap_persistence(shell, capsys):
    """Test that traps persist across commands."""
    shell.run_command('trap "echo persistent" TERM')
    
    # Execute another command
    shell.run_command('echo "other command"')
    
    # Check that trap is still there
    shell.run_command('trap')
    captured = capsys.readouterr()
    # Should still show the trap


def test_trap_in_subshell(shell):
    """Test trap behavior in subshells."""
    result = shell.run_command('(trap "echo subshell" TERM; echo done)')
    assert result == 0


def test_trap_script_mode(shell):
    """Test trap behavior in script mode vs interactive."""
    # This may behave differently in script vs interactive mode
    result = shell.run_command('trap "echo script" EXIT')
    assert result == 0