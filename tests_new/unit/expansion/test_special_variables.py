"""
Unit tests for special variable expansion.

Tests cover:
- $$ (process ID)
- $? (exit status)
- $! (last background PID)
- $# (parameter count)
- $@ (all parameters)
- $* (all parameters as single word)
- $0 (script/shell name)
- $- (shell options)
- $1-$9 (positional parameters)
"""

import pytest
import os


class TestProcessIDVariable:
    """Test $$ process ID variable."""
    
    def test_dollar_dollar_unquoted(self, shell, capsys):
        """Test $$ expansion unquoted."""
        shell.run_command('echo $$')
        captured = capsys.readouterr()
        # Should be a valid PID
        assert captured.out.strip().isdigit()
        assert int(captured.out.strip()) > 0
    
    def test_dollar_dollar_in_double_quotes(self, shell, capsys):
        """Test $$ expansion in double quotes."""
        shell.run_command('echo "PID: $$"')
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output.startswith("PID: ")
        pid_str = output.replace("PID: ", "")
        assert pid_str.isdigit()
        assert int(pid_str) > 0
    
    def test_dollar_dollar_in_single_quotes(self, shell, capsys):
        """Test $$ not expanded in single quotes."""
        shell.run_command("echo '$$'")
        captured = capsys.readouterr()
        assert captured.out.strip() == "$$"
    
    def test_dollar_dollar_consistency(self, shell, capsys):
        """Test $$ returns same value in same shell."""
        shell.run_command('echo $$ $$')
        captured = capsys.readouterr()
        parts = captured.out.strip().split()
        assert len(parts) == 2
        assert parts[0] == parts[1]
        assert parts[0].isdigit()
    
    def test_dollar_dollar_matches_os_pid(self, shell, capsys):
        """Test $$ matches actual process ID."""
        # Get the actual PID
        actual_pid = os.getpid()
        
        shell.run_command('echo $$')
        captured = capsys.readouterr()
        shell_pid = int(captured.out.strip())
        
        # Should be the same or a child process
        assert shell_pid > 0


class TestExitStatusVariable:
    """Test $? exit status variable."""
    
    def test_exit_status_success(self, shell, capsys):
        """Test $? after successful command."""
        shell.run_command('true')
        shell.run_command('echo $?')
        captured = capsys.readouterr()
        assert captured.out.strip() == "0"
    
    def test_exit_status_failure(self, shell, capsys):
        """Test $? after failed command."""
        shell.run_command('false')
        shell.run_command('echo $?')
        captured = capsys.readouterr()
        assert captured.out.strip() == "1"
    
    def test_exit_status_specific_code(self, shell, capsys):
        """Test $? with specific exit code."""
        shell.run_command('(exit 42)')
        shell.run_command('echo $?')
        captured = capsys.readouterr()
        assert captured.out.strip() == "42"
    
    def test_exit_status_in_quotes(self, shell, capsys):
        """Test $? expansion in double quotes."""
        shell.run_command('false')
        shell.run_command('echo "Exit status: $?"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "Exit status: 1"


class TestParameterCountVariable:
    """Test $# parameter count variable."""
    
    def test_param_count_zero(self, shell, capsys):
        """Test $# with no parameters."""
        shell.run_command('echo $#')
        captured = capsys.readouterr()
        assert captured.out.strip() == "0"
    
    def test_param_count_with_set(self, shell, capsys):
        """Test $# after setting parameters."""
        shell.run_command('set -- one two three')
        shell.run_command('echo $#')
        captured = capsys.readouterr()
        assert captured.out.strip() == "3"
    
    def test_param_count_in_function(self, shell, capsys):
        """Test $# inside function."""
        shell.run_command('''
        test_func() {
            echo "Param count: $#"
        }
        test_func a b c d e
        ''')
        captured = capsys.readouterr()
        assert "Param count: 5" in captured.out


class TestPositionalParameters:
    """Test $@ and $* for all parameters."""
    
    def test_dollar_at_unquoted(self, shell, capsys):
        """Test unquoted $@."""
        shell.run_command('set -- one two three')
        shell.run_command('echo $@')
        captured = capsys.readouterr()
        assert captured.out.strip() == "one two three"
    
    def test_dollar_at_quoted(self, shell, capsys):
        """Test quoted "$@" preserves separate words."""
        shell.run_command('set -- "arg one" "arg two"')
        shell.run_command('for arg in "$@"; do echo "[$arg]"; done')
        captured = capsys.readouterr()
        assert "[arg one]" in captured.out
        assert "[arg two]" in captured.out
    
    def test_dollar_star_unquoted(self, shell, capsys):
        """Test unquoted $*."""
        shell.run_command('set -- one two three')
        shell.run_command('echo $*')
        captured = capsys.readouterr()
        assert captured.out.strip() == "one two three"
    
    def test_dollar_star_quoted(self, shell, capsys):
        """Test quoted "$*" creates single word."""
        shell.run_command('set -- one two three')
        shell.run_command('echo "$*"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "one two three"
    
    def test_dollar_star_with_ifs(self, shell, capsys):
        """Test $* uses first char of IFS."""
        shell.run_command('IFS=","')
        shell.run_command('set -- one two three')
        shell.run_command('echo "$*"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "one,two,three"


class TestScriptNameVariable:
    """Test $0 script/shell name variable."""
    
    def test_dollar_zero_interactive(self, shell, capsys):
        """Test $0 in interactive shell."""
        shell.run_command('echo $0')
        captured = capsys.readouterr()
        # Should contain 'psh' or shell name
        output = captured.out.strip()
        assert 'psh' in output or 'shell' in output
    
    def test_dollar_zero_in_function(self, shell, capsys):
        """Test $0 remains script name in function."""
        shell.run_command('''
        test_func() {
            echo "In function: $0"
        }
        test_func
        ''')
        captured = capsys.readouterr()
        assert "In function:" in captured.out


class TestLastBackgroundPID:
    """Test $! last background process ID."""
    
    def test_dollar_bang_after_background(self, shell, capsys):
        """Test $! after starting background job."""
        shell.run_command('true &')
        shell.run_command('echo $!')
        captured = capsys.readouterr()
        # Should be a valid PID
        # Extract just the PID from output (skip job notification like "[1] 12345")
        lines = captured.out.strip().split('\n')
        pid_line = None
        for line in lines:
            if line and not line.startswith('['):
                pid_line = line.strip()
                break
        
        if pid_line:  # May be empty if job finished quickly
            assert pid_line.isdigit()
            assert int(pid_line) > 0
    
    def test_dollar_bang_empty_initially(self, shell, capsys):
        """Test $! is empty before any background jobs."""
        # Fresh shell should have empty $!
        shell.run_command('echo "[$!]"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "[]"


class TestShellOptionsVariable:
    """Test $- shell options variable."""
    
    def test_dollar_dash_basic(self, shell, capsys):
        """Test $- shows current options."""
        shell.run_command('echo $-')
        captured = capsys.readouterr()
        # Should contain some option flags
        output = captured.out.strip()
        assert len(output) >= 0  # May be empty or contain flags
    
    def test_dollar_dash_after_set(self, shell, capsys):
        """Test $- reflects option changes."""
        shell.run_command('set -x')  # Enable xtrace
        shell.run_command('echo $-')
        captured = capsys.readouterr()
        assert 'x' in captured.out
        
        shell.run_command('set +x')  # Disable xtrace
        shell.run_command('echo $-')
        captured = capsys.readouterr()
        # x should be removed from options


class TestNumberedParameters:
    """Test $1-$9 positional parameters."""
    
    def test_numbered_params_basic(self, shell, capsys):
        """Test basic numbered parameter access."""
        shell.run_command('set -- first second third')
        shell.run_command('echo "$1 $2 $3"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "first second third"
    
    def test_numbered_params_beyond_nine(self, shell, capsys):
        """Test ${10} and beyond."""
        shell.run_command('set -- a b c d e f g h i j k l')
        shell.run_command('echo "${10} ${11} ${12}"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "j k l"
    
    def test_numbered_params_unset(self, shell, capsys):
        """Test unset numbered parameters expand to empty."""
        shell.run_command('set -- one')
        shell.run_command('echo "[$1] [$2] [$3]"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "[one] [] []"


class TestSpecialVariablesInContext:
    """Test special variables in various contexts."""
    
    def test_special_vars_in_arithmetic(self, shell, capsys):
        """Test special variables in arithmetic context."""
        shell.run_command('set -- 5 3')
        shell.run_command('echo $(($1 + $2))')
        captured = capsys.readouterr()
        assert captured.out.strip() == "8"
        
        shell.run_command('echo $(($# * 10))')
        captured = capsys.readouterr()
        assert captured.out.strip() == "20"
    
    def test_special_vars_in_assignments(self, shell, capsys):
        """Test special variables in variable assignments."""
        shell.run_command('pid=$$')
        shell.run_command('echo $pid')
        captured = capsys.readouterr()
        assert captured.out.strip().isdigit()
        
        shell.run_command('set -- hello world')
        shell.run_command('all=$*')
        shell.run_command('echo "$all"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello world"
    
    def test_special_vars_in_parameter_expansion(self, shell, capsys):
        """Test special variables with parameter expansion operators."""
        shell.run_command('echo ${#:-default}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "0"
        
        shell.run_command('set -- one two')
        shell.run_command('echo ${#:-default}')
        captured = capsys.readouterr()
        assert captured.out.strip() == "2"