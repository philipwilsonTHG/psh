"""
Tests for the CommandExecutor module.
"""

import pytest
from psh.shell import Shell
from psh.executor import CommandExecutor, ExecutionContext
from psh.ast_nodes import SimpleCommand


class TestCommandExecutor:
    """Test the CommandExecutor functionality."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        return Shell(norc=True)
    
    @pytest.fixture
    def executor(self, shell):
        """Create a command executor."""
        return CommandExecutor(shell)
    
    @pytest.fixture
    def context(self):
        """Create an execution context."""
        return ExecutionContext()
    
    def test_simple_echo(self, executor, context, shell):
        """Test simple echo command."""
        # Create a simple command node
        cmd = SimpleCommand(args=['echo', 'hello'])
        
        # Execute the command
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
    
    def test_variable_assignment(self, executor, context, shell):
        """Test pure variable assignment."""
        # Create assignment command
        cmd = SimpleCommand(args=['VAR=value'])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
        assert shell.state.get_variable('VAR') == 'value'
    
    def test_command_with_assignment(self, executor, context, shell):
        """Test command with variable assignment."""
        # Create command with assignment
        cmd = SimpleCommand(args=['VAR=test', 'echo', 'hello'])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
        # Variable should not persist after command (unless exported)
        # Check that VAR is not in the environment (not exported)
        import os
        assert 'VAR' not in os.environ
    
    def test_builtin_execution(self, executor, context, shell):
        """Test builtin command execution."""
        # Create cd command
        cmd = SimpleCommand(args=['cd', '/tmp'])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
    
    def test_external_command(self, executor, context, shell):
        """Test external command execution."""
        # Create ls command
        cmd = SimpleCommand(args=['ls', '-la'])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
    
    def test_command_not_found(self, executor, context, shell):
        """Test command not found error."""
        # Create non-existent command
        cmd = SimpleCommand(args=['nonexistentcommand123'])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 127  # Command not found
    
    def test_empty_command(self, executor, context, shell):
        """Test empty command execution."""
        # Create empty command
        cmd = SimpleCommand(args=[])
        
        # Execute
        exit_status = executor.execute(cmd, context)
        
        assert exit_status == 0
    
    def test_xtrace_option(self, shell, capsys):
        """Test xtrace option prints commands."""
        # Use the same approach as test_shell_options.py
        shell.run_command("set -x")
        shell.run_command("echo test")
        
        # Check stderr for trace output
        captured = capsys.readouterr()
        assert 'test\n' in captured.out
        assert '+ echo test\n' in captured.err