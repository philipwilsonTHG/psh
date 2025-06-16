"""Test command builtin functionality."""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from io import StringIO

from psh.builtins.command_builtin import CommandBuiltin


class TestCommandBuiltin:
    """Test cases for command builtin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.command = CommandBuiltin()
        self.shell = MagicMock()
        self.shell.stdout = StringIO()
        self.shell.stderr = StringIO()
        self.shell.env = {'PATH': '/usr/bin:/bin'}
        # Create proper mock builtins
        echo_builtin = MagicMock()
        echo_builtin.execute = MagicMock(return_value=0)
        pwd_builtin = MagicMock()
        pwd_builtin.execute = MagicMock(return_value=0)
        
        self.shell.builtin_registry = {
            'echo': echo_builtin,
            'pwd': pwd_builtin,
        }
    
    def test_command_execute_builtin(self):
        """Test executing a builtin with command."""
        result = self.command.execute(['command', 'echo', 'hello'], self.shell)
        
        assert result == 0
        self.shell.builtin_registry['echo'].execute.assert_called_once_with(
            ['echo', 'hello'], self.shell
        )
    
    def test_command_bypass_function(self):
        """Test that command bypasses functions (simulated by builtin check)."""
        # When a function exists, command should still execute the builtin
        result = self.command.execute(['command', 'pwd'], self.shell)
        
        assert result == 0
        self.shell.builtin_registry['pwd'].execute.assert_called_once()
    
    @patch('os.fork')
    @patch('os.execv')
    @patch('os.waitpid')
    def test_command_execute_external(self, mock_waitpid, mock_execv, mock_fork):
        """Test executing an external command."""
        # Setup mocks
        mock_fork.return_value = 123  # Parent process
        mock_waitpid.return_value = (123, 0)  # Normal exit
        
        # Create a mock executable
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            result = self.command.execute(['command', 'ls', '-l'], self.shell)
        
        assert result == 0
        mock_fork.assert_called_once()
        mock_waitpid.assert_called_once_with(123, 0)
    
    def test_command_not_found(self):
        """Test command not found error."""
        result = self.command.execute(['command', 'nonexistent_command'], self.shell)
        
        assert result == 127
        assert "command not found" in self.shell.stderr.getvalue()
    
    def test_command_v_option_builtin(self):
        """Test -v option with builtin."""
        result = self.command.execute(['command', '-v', 'echo'], self.shell)
        
        assert result == 0
        assert self.shell.stdout.getvalue().strip() == 'echo'
    
    def test_command_V_option_builtin(self):
        """Test -V option with builtin."""
        result = self.command.execute(['command', '-V', 'echo'], self.shell)
        
        assert result == 0
        assert "echo is a shell builtin" in self.shell.stdout.getvalue()
    
    def test_command_v_option_external(self):
        """Test -v option with external command."""
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            result = self.command.execute(['command', '-v', 'ls'], self.shell)
        
        assert result == 0
        assert '/bin/ls' in self.shell.stdout.getvalue()
    
    def test_command_V_option_external(self):
        """Test -V option with external command."""
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            result = self.command.execute(['command', '-V', 'ls'], self.shell)
        
        assert result == 0
        output = self.shell.stdout.getvalue()
        assert "ls is " in output and "/ls" in output
    
    def test_command_v_not_found(self):
        """Test -v option with non-existent command."""
        result = self.command.execute(['command', '-v', 'nonexistent'], self.shell)
        
        assert result == 1
        assert self.shell.stdout.getvalue() == ''
    
    def test_command_p_option(self):
        """Test -p option uses default PATH."""
        # Set a custom PATH that doesn't include standard directories
        self.shell.env['PATH'] = '/custom/path'
        
        with patch('os.path.isfile') as mock_isfile, \
             patch('os.access', return_value=True), \
             patch('os.fork', return_value=123), \
             patch('os.waitpid', return_value=(123, 0)):
            
            # Make it so ls is only found in /bin
            def isfile_side_effect(path):
                return path == '/bin/ls' or path == '/usr/bin/ls'
            mock_isfile.side_effect = isfile_side_effect
            
            result = self.command.execute(['command', '-p', 'ls'], self.shell)
            
            # PATH should have been temporarily changed
            # After execution, it should be restored
            assert self.shell.env['PATH'] == '/custom/path'
            assert result == 0
    
    def test_command_invalid_option(self):
        """Test invalid option handling."""
        result = self.command.execute(['command', '-x', 'echo'], self.shell)
        
        assert result == 2
        assert "invalid option: -x" in self.shell.stderr.getvalue()
    
    def test_command_no_args(self):
        """Test command with no command specified."""
        result = self.command.execute(['command'], self.shell)
        
        assert result == 2
        assert "usage: command" in self.shell.stderr.getvalue()
    
    def test_command_double_dash(self):
        """Test -- stops option processing."""
        result = self.command.execute(['command', '--', '-v'], self.shell)
        
        assert result == 127  # -v treated as command name, not option
        assert "command not found" in self.shell.stderr.getvalue()
    
    def test_command_combined_options(self):
        """Test that options can be combined."""
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            # -p and -v together
            result = self.command.execute(['command', '-p', '-v', 'ls'], self.shell)
            
            assert result == 0
            # Should show path from default PATH
            output = self.shell.stdout.getvalue()
            assert '/bin/ls' in output or '/usr/bin/ls' in output
    
    @patch('os.fork')
    @patch('os.WIFEXITED')
    @patch('os.WEXITSTATUS')
    @patch('os.waitpid')
    def test_command_exit_status_propagation(self, mock_waitpid, mock_exitstatus, 
                                           mock_ifexited, mock_fork):
        """Test that exit status is properly propagated."""
        mock_fork.return_value = 123
        mock_waitpid.return_value = (123, 42)
        mock_ifexited.return_value = True
        mock_exitstatus.return_value = 42
        
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True):
            result = self.command.execute(['command', 'false'], self.shell)
        
        assert result == 42
    
    def test_command_absolute_path(self):
        """Test executing command with absolute path."""
        with patch('os.path.isfile', return_value=True), \
             patch('os.access', return_value=True), \
             patch('os.fork', return_value=123), \
             patch('os.waitpid', return_value=(123, 0)):
            
            result = self.command.execute(['command', '/usr/bin/ls'], self.shell)
            
            assert result == 0