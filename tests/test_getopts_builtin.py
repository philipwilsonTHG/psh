"""Test getopts builtin functionality."""

import pytest
from unittest.mock import MagicMock
from io import StringIO

from psh.builtins.positional import GetoptsBuiltin


class TestGetoptsBuiltin:
    """Test cases for getopts builtin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.getopts = GetoptsBuiltin()
        self.shell = MagicMock()
        self.shell.stderr = StringIO()
        self.shell.state = MagicMock()
        # Initialize required variables
        self.shell.state.get_variable = MagicMock(side_effect=self._get_variable)
        self.shell.state.set_variable = MagicMock(side_effect=self._set_variable)
        self.shell.state.unset_variable = MagicMock()
        self.shell.positional_params = []
        self._variables = {'OPTIND': '1', 'OPTERR': '1'}
    
    def _get_variable(self, name, default=None):
        """Mock get_variable method."""
        return self._variables.get(name, default)
    
    def _set_variable(self, name, value):
        """Mock set_variable method."""
        self._variables[name] = value
    
    def test_getopts_basic_option(self):
        """Test parsing a simple option."""
        self.shell.positional_params = ['-a', 'arg1']
        
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == 'a'
        assert self._variables['OPTIND'] == '2'
    
    def test_getopts_option_with_argument(self):
        """Test parsing option that requires an argument."""
        self.shell.positional_params = ['-f', 'filename', 'arg1']
        
        result = self.getopts.execute(['getopts', 'f:', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == 'f'
        assert self._variables['OPTARG'] == 'filename'
        assert self._variables['OPTIND'] == '3'
    
    def test_getopts_clustered_options(self):
        """Test parsing clustered options like -abc."""
        self.shell.positional_params = ['-abc', 'arg1']
        
        # First call gets 'a'
        result = self.getopts.execute(['getopts', 'abc', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'a'
        
        # Second call gets 'b' (remaining -bc)
        result = self.getopts.execute(['getopts', 'abc', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'b'
        
        # Third call gets 'c'
        result = self.getopts.execute(['getopts', 'abc', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'c'
        assert self._variables['OPTIND'] == '2'
    
    def test_getopts_invalid_option(self):
        """Test handling of invalid option."""
        self.shell.positional_params = ['-x', 'arg1']
        
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        
        assert result == 0  # getopts returns 0 even for invalid options
        assert self._variables['opt'] == '?'
        assert self._variables['OPTARG'] == 'x'
        assert "illegal option -- x" in self.shell.stderr.getvalue()
    
    def test_getopts_missing_argument(self):
        """Test handling of missing required argument."""
        self.shell.positional_params = ['-f']  # -f requires argument
        
        result = self.getopts.execute(['getopts', 'f:', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == '?'
        assert "option requires an argument -- f" in self.shell.stderr.getvalue()
    
    def test_getopts_silent_error_mode(self):
        """Test silent error reporting mode with leading colon."""
        self.shell.positional_params = ['-x', 'arg1']
        
        result = self.getopts.execute(['getopts', ':ab', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == '?'
        assert self._variables['OPTARG'] == 'x'
        assert self.shell.stderr.getvalue() == ""  # No error message
    
    def test_getopts_silent_missing_argument(self):
        """Test silent mode with missing argument."""
        self.shell.positional_params = ['-f']
        
        result = self.getopts.execute(['getopts', ':f:', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == ':'  # Colon for missing argument
        assert self._variables['OPTARG'] == 'f'
        assert self.shell.stderr.getvalue() == ""  # No error message
    
    def test_getopts_end_of_options(self):
        """Test behavior when no more options."""
        self.shell.positional_params = ['arg1', 'arg2']
        
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        
        assert result == 1  # End of options
        assert self._variables['opt'] == '?'
    
    def test_getopts_double_dash(self):
        """Test handling of -- to end options."""
        self.shell.positional_params = ['-a', '--', '-b']
        
        # First call gets -a
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'a'
        
        # Second call hits --
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        assert result == 1  # End of options
        assert self._variables['opt'] == '?'
        assert self._variables['OPTIND'] == '3'
    
    def test_getopts_custom_args(self):
        """Test parsing custom arguments instead of positional params."""
        result = self.getopts.execute(
            ['getopts', 'ab:', 'opt', '-b', 'value', 'arg1'], 
            self.shell
        )
        
        assert result == 0
        assert self._variables['opt'] == 'b'
        assert self._variables['OPTARG'] == 'value'
        assert self._variables['OPTIND'] == '3'
    
    def test_getopts_opterr_disabled(self):
        """Test OPTERR=0 disables error messages."""
        self._variables['OPTERR'] = '0'
        self.shell.positional_params = ['-x']
        
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        
        assert result == 0
        assert self._variables['opt'] == '?'
        assert self.shell.stderr.getvalue() == ""  # No error message
    
    def test_getopts_optind_persistence(self):
        """Test OPTIND persists between calls."""
        self.shell.positional_params = ['-a', '-b', '-c']
        
        # Parse each option in sequence
        for expected_opt in ['a', 'b', 'c']:
            result = self.getopts.execute(['getopts', 'abc', 'opt'], self.shell)
            assert result == 0
            assert self._variables['opt'] == expected_opt
        
        # Next call should fail (no more options)
        result = self.getopts.execute(['getopts', 'abc', 'opt'], self.shell)
        assert result == 1
    
    def test_getopts_reset_optind(self):
        """Test resetting OPTIND to restart parsing."""
        self.shell.positional_params = ['-a', '-b']
        
        # Parse first option
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'a'
        
        # Reset OPTIND
        self._variables['OPTIND'] = '1'
        
        # Parse from beginning again
        result = self.getopts.execute(['getopts', 'ab', 'opt'], self.shell)
        assert result == 0
        assert self._variables['opt'] == 'a'
    
    def test_getopts_insufficient_args(self):
        """Test getopts with insufficient arguments."""
        result = self.getopts.execute(['getopts', 'ab'], self.shell)
        
        assert result == 2
        assert "usage: getopts optstring name" in self.shell.stderr.getvalue()
    
    def test_getopts_help_text(self):
        """Test getopts help property."""
        help_text = self.getopts.help
        assert "getopts optstring name" in help_text
        assert "OPTIND" in help_text
        assert "OPTARG" in help_text
        assert "OPTERR" in help_text