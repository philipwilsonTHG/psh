"""
Test visitor executor functionality.

This test was originally for compatibility between legacy and visitor executors.
Now it tests the visitor executor behavior.
"""

import pytest
import os
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse


class TestExecutorCompatibility:
    """Test visitor executor functionality."""
    
    def run_command(self, command):
        """Run command and capture output."""
        # Create shell
        shell = Shell()
        
        # Capture output
        stdout = StringIO()
        stderr = StringIO()
        
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Parse command once
            tokens = tokenize(command)
            ast = parse(tokens)
            
            # Execute
            exit_code = shell.execute(ast)
        
        return {
            'exit_code': exit_code,
            'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue(),
            'variables': dict(shell.state.variables),
            'last_exit_code': shell.state.last_exit_code
        }
    
    def test_simple_echo(self):
        """Test simple echo command."""
        result = self.run_command("echo hello")
        assert result['exit_code'] == 0
        assert result['stdout'] == "hello\n"
        assert result['stderr'] == ""
    
    def test_variable_assignment(self):
        """Test variable assignment."""
        result = self.run_command("x=42; echo $x")
        assert result['exit_code'] == 0
        assert result['stdout'] == "42\n"
        assert result['variables']['x'] == '42'
    
    def test_command_substitution(self):
        """Test command substitution."""
        result = self.run_command("result=$(echo test); echo $result")
        assert result['exit_code'] == 0
        assert result['stdout'] == "test\n"
        assert result['variables']['result'] == 'test'
    
    def test_pipeline(self):
        """Test pipeline execution."""
        result = self.run_command("echo hello | cat")
        assert result['exit_code'] == 0
        assert result['stdout'] == "hello\n"
    
    @pytest.mark.xfail(reason="StringIO doesn't capture direct fd writes from external commands")
    def test_stderr_redirection(self):
        """Test stderr redirection."""
        # This command redirects stderr to stdout, so ls error goes to stdout
        result = self.run_command("ls /nonexistent 2>&1")
        assert result['exit_code'] != 0  # ls should fail
        assert "/nonexistent" in result['stdout']  # Error message in stdout
        assert result['stderr'] == ""  # Nothing in stderr
    
    def test_exit_status(self):
        """Test exit status tracking."""
        result = self.run_command("false; echo $?")
        assert result['stdout'] == "1\n"
        assert result['last_exit_code'] == 0  # echo succeeded
    
    def test_function_definition(self):
        """Test function definition and execution."""
        result = self.run_command("greet() { echo Hello $1; }; greet World")
        assert result['exit_code'] == 0
        assert result['stdout'] == "Hello World\n"