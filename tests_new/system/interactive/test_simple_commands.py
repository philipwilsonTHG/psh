"""
Simple interactive command tests for PSH.

These tests verify basic command execution in an interactive shell.
"""

import pytest
import sys
from pathlib import Path

# Remove blanket skip - let individual tests decide if they work

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TEST_ROOT))

import pytest
try:
    import pexpect
    from framework.interactive import InteractivePSHTest
except ImportError:
    # Framework not available, create dummy base class
    class InteractivePSHTest:
        pass


class TestSimpleInteractiveCommands(InteractivePSHTest):
    """Test simple command execution interactively."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for simple command tests")
    
    def test_echo_command(self):
        """Test basic echo command."""
        self.spawn_shell()
        
        # Send echo command
        self.send_line("echo hello world")
        
        # Expect the output
        self.expect("hello world")
        self.expect_prompt()
    
    def test_multiple_commands(self):
        """Test executing multiple commands."""
        self.spawn_shell()
        
        # First command
        self.send_line("echo first")
        self.expect("first")
        self.expect_prompt()
        
        # Second command
        self.send_line("echo second")
        self.expect("second")
        self.expect_prompt()
    
    def test_command_with_quotes(self):
        """Test command with quoted strings."""
        self.spawn_shell()
        
        self.send_line('echo "hello world"')
        self.expect("hello world")
        self.expect_prompt()
        
        self.send_line("echo 'single quotes'")
        self.expect("single quotes")
        self.expect_prompt()
    
    def test_variable_assignment(self):
        """Test variable assignment and usage."""
        self.spawn_shell()
        
        # Set variable
        self.send_line("TEST_VAR=hello")
        self.expect_prompt()
        
        # Use variable
        self.send_line("echo $TEST_VAR")
        self.expect("hello")
        self.expect_prompt()
    
    def test_pipe_command(self):
        """Test simple pipeline."""
        self.spawn_shell()
        
        self.send_line("echo hello world | grep world")
        self.expect("hello world")
        self.expect_prompt()
    
    def test_exit_command(self):
        """Test exit command."""
        self.spawn_shell()
        
        # Send exit
        self.send_line("exit")
        
        # Should get EOF
        self.shell.expect(pexpect.EOF)
        assert not self.shell.isalive()


class TestInteractiveErrors(InteractivePSHTest):
    """Test error handling in interactive mode."""
    
    # Override inherited method that has incorrect signature
    def test_interactive_sequence(self):
        """Override to prevent fixture error."""
        pytest.skip("Not applicable for error tests")
    
    def test_command_not_found(self):
        """Test command not found error."""
        self.spawn_shell()
        
        self.send_line("nonexistentcommand")
        self.expect("command not found")
        self.expect_prompt()
    
    def test_syntax_error(self):
        """Test syntax error handling."""
        self.spawn_shell()
        
        # Unclosed quote
        self.send_line('echo "unclosed')
        # Should get continuation prompt
        self.expect_continuation_prompt()
        
        # Complete the quote
        self.send_line('quote"')
        self.expect("unclosed")
        self.expect("quote")
        self.expect_prompt()