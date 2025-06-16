"""Tests for the CompletionManager component."""
import pytest
import os
import tempfile
import readline
from unittest.mock import patch, MagicMock
from psh.shell import Shell
from psh.interactive.completion_manager import CompletionManager


class TestCompletionManager:
    """Test the CompletionManager functionality."""
    
    def test_initialization(self):
        """Test that CompletionManager initializes correctly."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        assert cm.shell == shell
        assert cm.state == shell.state
        assert cm.completion_engine is not None
        assert cm.current_matches == []
        assert cm.current_text == ""
    
    def test_setup_readline(self):
        """Test readline configuration."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        # Mock readline functions
        with patch('readline.set_completer') as mock_set_completer, \
             patch('readline.parse_and_bind') as mock_parse_and_bind, \
             patch('readline.set_completer_delims') as mock_set_delims:
            
            cm.setup_readline()
            
            # Verify readline was configured
            mock_set_completer.assert_called_once_with(cm._readline_completer)
            mock_parse_and_bind.assert_called_once_with('tab: complete')
            mock_set_delims.assert_called_once_with(' \t\n;|&<>')
    
    def test_get_completions(self):
        """Test getting completions."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            open(os.path.join(tmpdir, 'test1.txt'), 'w').close()
            open(os.path.join(tmpdir, 'test2.txt'), 'w').close()
            open(os.path.join(tmpdir, 'other.txt'), 'w').close()
            
            os.chdir(tmpdir)
            
            # Get completions for 'test'
            completions = cm.get_completions('test', 'test', 4)
            
            assert 'test1.txt' in completions
            assert 'test2.txt' in completions
            assert 'other.txt' not in completions
    
    def test_complete_variable(self):
        """Test variable name completion."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        # Add some variables
        shell.state.set_variable('TEST_VAR1', 'value1')
        shell.state.set_variable('TEST_VAR2', 'value2')
        shell.state.set_variable('OTHER_VAR', 'other')
        shell.state.env['TEST_ENV'] = 'env_value'
        
        # Complete variable names
        completions = cm.complete_variable('$TEST')
        
        assert '$TEST_VAR1' in completions
        assert '$TEST_VAR2' in completions
        assert '$TEST_ENV' in completions
        assert '$OTHER_VAR' not in completions
    
    def test_readline_completer(self):
        """Test the readline completer function."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        # Mock readline functions and completion engine
        with patch('readline.get_line_buffer', return_value='test'), \
             patch('readline.get_endidx', return_value=4), \
             patch.object(cm, 'get_completions', return_value=['test1', 'test2', 'test3']):
            
            # First call (state=0) should populate matches
            result = cm._readline_completer('test', 0)
            assert result == 'test1'
            assert cm.current_matches == ['test1', 'test2', 'test3']
            assert cm.current_text == 'test'
            
            # Subsequent calls should return next matches
            assert cm._readline_completer('test', 1) == 'test2'
            assert cm._readline_completer('test', 2) == 'test3'
            
            # Out of matches should return None
            assert cm._readline_completer('test', 3) is None
    
    def test_execute_method(self):
        """Test the execute method delegates to get_completions."""
        shell = Shell()
        cm = CompletionManager(shell)
        
        with patch.object(cm, 'get_completions', return_value=['comp1', 'comp2']) as mock_get:
            result = cm.execute('test', 'test line', 5)
            
            mock_get.assert_called_once_with('test', 'test line', 5)
            assert result == ['comp1', 'comp2']
    
    def test_integration_with_interactive_manager(self):
        """Test that CompletionManager integrates with InteractiveManager."""
        shell = Shell()
        # Test that CompletionManager can be created and used by shell
        cm = CompletionManager(shell)
        
        # Test that it properly inherits from InteractiveComponent
        from psh.interactive.base import InteractiveComponent
        assert isinstance(cm, InteractiveComponent)
        
        # Test that it has the required methods
        assert hasattr(cm, 'execute')
        assert hasattr(cm, 'setup_readline')
        assert hasattr(cm, 'get_completions')
        
        # Test that execute method works
        with patch.object(cm.completion_engine, 'get_completions', return_value=['test1', 'test2']):
            result = cm.execute('test', 'test', 4)
            assert result == ['test1', 'test2']