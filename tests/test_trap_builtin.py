"""Tests for the trap builtin - simplified and working."""

import pytest
import signal
import os
import sys
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch
from psh.builtins.signal_handling import TrapBuiltin
from psh.core.trap_manager import TrapManager
from psh.core.state import ShellState


class TestTrapBuiltin:
    """Test trap builtin functionality."""
    
    def setup_method(self):
        """Set up test components."""
        self.trap_builtin = TrapBuiltin()
        
        # Create a mock shell with minimal required attributes
        self.shell = MagicMock()
        self.shell.state = MagicMock()
        self.shell.state.stdout = StringIO()
        self.shell.state.stderr = StringIO()
        self.shell.state.trap_handlers = {}
        self.shell.state._original_signal_handlers = {}
        self.shell.state.is_script_mode = False
        
        # Create a real trap manager for proper testing
        self.shell.trap_manager = TrapManager(self.shell)
    
    def test_trap_list_signals(self):
        """Test trap -l lists signals."""
        result = self.trap_builtin.execute(['trap', '-l'], self.shell)
        output = self.shell.state.stdout.getvalue()
        
        assert result == 0
        assert "SIGINT" in output
        assert "SIGTERM" in output
        assert "EXIT" in output
        assert "DEBUG" in output
        assert "ERR" in output
    
    def test_trap_no_args_shows_empty(self):
        """Test trap with no args shows empty when no traps set."""
        result = self.trap_builtin.execute(['trap'], self.shell)
        output = self.shell.state.stdout.getvalue()
        
        assert result == 0
        assert output.strip() == ""
    
    def test_trap_set_basic(self):
        """Test setting a basic trap."""
        result = self.trap_builtin.execute(['trap', 'echo trapped', 'INT'], self.shell)
        assert result == 0
        
        # Verify the trap was stored
        assert 'INT' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['INT'] == 'echo trapped'
    
    def test_trap_show_specific(self):
        """Test showing specific traps."""
        # Set a trap first
        self.shell.state.trap_handlers['INT'] = 'echo trapped'
        
        result = self.trap_builtin.execute(['trap', '-p', 'INT'], self.shell)
        output = self.shell.state.stdout.getvalue()
        
        assert result == 0
        assert "trap -- 'echo trapped' INT" in output
    
    def test_trap_ignore_signal(self):
        """Test ignoring a signal with empty string."""
        result = self.trap_builtin.execute(['trap', '', 'QUIT'], self.shell)
        assert result == 0
        
        # Verify the trap was set to ignore
        assert 'QUIT' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['QUIT'] == ''
    
    def test_trap_reset(self):
        """Test resetting a trap with -."""
        # Set a trap first
        self.shell.state.trap_handlers['INT'] = 'echo trapped'
        
        # Reset the trap
        result = self.trap_builtin.execute(['trap', '-', 'INT'], self.shell)
        assert result == 0
        
        # Check that trap is gone
        assert 'INT' not in self.shell.state.trap_handlers
    
    def test_trap_multiple_signals(self):
        """Test setting trap for multiple signals."""
        result = self.trap_builtin.execute(['trap', 'echo multi-trap', 'INT', 'TERM', 'HUP'], self.shell)
        assert result == 0
        
        # Check all signals have the trap
        for signal_name in ['INT', 'TERM', 'HUP']:
            assert signal_name in self.shell.state.trap_handlers
            assert self.shell.state.trap_handlers[signal_name] == 'echo multi-trap'
    
    def test_trap_signal_by_number(self):
        """Test setting trap using signal number."""
        result = self.trap_builtin.execute(['trap', 'echo signal 2', '2'], self.shell)
        assert result == 0
        
        # Check the trap is set (should be stored as '2')
        assert '2' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['2'] == 'echo signal 2'
    
    def test_trap_invalid_signal(self):
        """Test error handling for invalid signals."""
        result = self.trap_builtin.execute(['trap', 'echo test', 'INVALID'], self.shell)
        error = self.shell.state.stderr.getvalue()
        
        assert result == 1
        assert "invalid signal specification" in error
    
    def test_trap_show_all(self):
        """Test showing all traps."""
        # Set multiple traps
        self.shell.state.trap_handlers = {
            'INT': 'echo int',
            'TERM': 'echo term',
            'EXIT': 'echo exit'
        }
        
        result = self.trap_builtin.execute(['trap', '-p'], self.shell)
        output = self.shell.state.stdout.getvalue()
        
        assert result == 0
        assert "trap -- 'echo exit' EXIT" in output
        assert "trap -- 'echo int' INT" in output
        assert "trap -- 'echo term' TERM" in output
    
    def test_trap_pseudo_signals(self):
        """Test pseudo-signals (EXIT, DEBUG, ERR)."""
        for signal_name in ['EXIT', 'DEBUG', 'ERR']:
            result = self.trap_builtin.execute(['trap', f'echo {signal_name} trap', signal_name], self.shell)
            assert result == 0
            
            # Verify trap is set
            assert signal_name in self.shell.state.trap_handlers
            assert self.shell.state.trap_handlers[signal_name] == f'echo {signal_name} trap'
    
    def test_trap_usage_error(self):
        """Test usage error with insufficient arguments."""
        result = self.trap_builtin.execute(['trap', 'action'], self.shell)
        error = self.shell.state.stderr.getvalue()
        
        assert result == 2
        assert "usage: trap [action] [condition...]" in error
    
    def test_trap_execution_basic(self):
        """Test basic trap execution functionality."""
        # Set up a mock shell.run_command for trap execution
        self.shell.run_command = MagicMock(return_value=0)
        
        # Set a trap
        result = self.trap_builtin.execute(['trap', 'echo TRAP_EXECUTED', 'INT'], self.shell)
        assert result == 0
        
        # Verify the trap is stored
        assert 'INT' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['INT'] == 'echo TRAP_EXECUTED'
        
        # Test manual trap execution
        self.shell.trap_manager.execute_trap('INT')
        
        # Verify run_command was called with the trap action
        self.shell.run_command.assert_called_with('echo TRAP_EXECUTED', add_to_history=False)


class TestTrapManager:
    """Test TrapManager functionality independently."""
    
    def setup_method(self):
        """Set up test components."""
        self.shell = MagicMock()
        self.shell.state = MagicMock()
        self.shell.state.trap_handlers = {}
        self.shell.state._original_signal_handlers = {}
        self.shell.state.stderr = StringIO()
        self.shell.state.last_exit_code = 0
        
        self.trap_manager = TrapManager(self.shell)
    
    def test_signal_mapping(self):
        """Test signal name to number mapping."""
        assert 'INT' in self.trap_manager.signal_map
        assert self.trap_manager.signal_map['INT'] == signal.SIGINT
        assert 'EXIT' in self.trap_manager.signal_map
        assert self.trap_manager.signal_map['EXIT'] == 'EXIT'
    
    def test_set_trap_basic(self):
        """Test basic trap setting."""
        result = self.trap_manager.set_trap('echo test', ['INT'])
        assert result == 0
        assert 'INT' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['INT'] == 'echo test'
    
    def test_set_trap_ignore(self):
        """Test setting trap to ignore."""
        result = self.trap_manager.set_trap('', ['QUIT'])
        assert result == 0
        assert 'QUIT' in self.shell.state.trap_handlers
        assert self.shell.state.trap_handlers['QUIT'] == ''
    
    def test_set_trap_reset(self):
        """Test resetting trap."""
        # First set a trap
        self.shell.state.trap_handlers['INT'] = 'echo test'
        
        # Then reset it
        result = self.trap_manager.set_trap('-', ['INT'])
        assert result == 0
        assert 'INT' not in self.shell.state.trap_handlers
    
    def test_show_traps_empty(self):
        """Test showing traps when none are set."""
        result = self.trap_manager.show_traps()
        assert result == ""
    
    def test_show_traps_with_content(self):
        """Test showing traps with content."""
        self.shell.state.trap_handlers = {
            'INT': 'echo int trap',
            'EXIT': 'cleanup'
        }
        
        result = self.trap_manager.show_traps()
        assert "trap -- 'cleanup' EXIT" in result
        assert "trap -- 'echo int trap' INT" in result
    
    def test_execute_trap(self):
        """Test trap execution."""
        # Set up mock
        self.shell.run_command = MagicMock(return_value=0)
        self.shell.state.trap_handlers['INT'] = 'echo test trap'
        
        # Execute trap
        self.trap_manager.execute_trap('INT')
        
        # Verify command was executed
        self.shell.run_command.assert_called_with('echo test trap', add_to_history=False)


if __name__ == '__main__':
    pytest.main([__file__])