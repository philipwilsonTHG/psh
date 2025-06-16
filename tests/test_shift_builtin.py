"""Test shift builtin functionality."""

import pytest
from unittest.mock import MagicMock
from io import StringIO

from psh.builtins.positional import ShiftBuiltin


class TestShiftBuiltin:
    """Test cases for shift builtin."""
    
    def test_shift_default(self):
        """Test shift with default n=1."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2', 'arg3']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift'], shell)
        
        assert result == 0
        assert shell.positional_params == ['arg2', 'arg3']
    
    def test_shift_explicit_n(self):
        """Test shift with explicit n value."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2', 'arg3', 'arg4']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', '2'], shell)
        
        assert result == 0
        assert shell.positional_params == ['arg3', 'arg4']
    
    def test_shift_zero(self):
        """Test shift with n=0 (no-op)."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', '0'], shell)
        
        assert result == 0
        assert shell.positional_params == ['arg1', 'arg2']
    
    def test_shift_all_params(self):
        """Test shift with n equal to parameter count."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2', 'arg3']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', '3'], shell)
        
        assert result == 0
        assert shell.positional_params == []
    
    def test_shift_too_many(self):
        """Test shift with n greater than parameter count."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', '5'], shell)
        
        assert result == 1  # Failure
        assert shell.positional_params == ['arg1', 'arg2']  # Unchanged
    
    def test_shift_negative(self):
        """Test shift with negative n."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', '-1'], shell)
        
        assert result == 1  # Failure
        assert shell.positional_params == ['arg1', 'arg2']  # Unchanged
        error = shell.stderr.getvalue()
        assert "must be non-negative" in error
    
    def test_shift_non_numeric(self):
        """Test shift with non-numeric argument."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2']
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift', 'abc'], shell)
        
        assert result == 1  # Failure
        assert shell.positional_params == ['arg1', 'arg2']  # Unchanged
        error = shell.stderr.getvalue()
        assert "numeric argument required" in error
    
    def test_shift_empty_params(self):
        """Test shift with no positional parameters."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = []
        shell.stderr = StringIO()
        
        result = shift_builtin.execute(['shift'], shell)
        
        assert result == 1  # Failure when n > $#
        assert shell.positional_params == []
    
    def test_shift_multiple_args_ignored(self):
        """Test that extra arguments to shift are ignored."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2', 'arg3']
        shell.stderr = StringIO()
        
        # Extra arguments should be ignored
        result = shift_builtin.execute(['shift', '1', 'extra', 'args'], shell)
        
        assert result == 0
        assert shell.positional_params == ['arg2', 'arg3']
    
    def test_shift_preserves_special_params(self):
        """Test that shift only affects positional parameters."""
        shift_builtin = ShiftBuiltin()
        shell = MagicMock()
        shell.positional_params = ['arg1', 'arg2', 'arg3']
        shell.stderr = StringIO()
        shell.variables = {'HOME': '/home/user', 'PATH': '/usr/bin'}
        
        result = shift_builtin.execute(['shift'], shell)
        
        assert result == 0
        assert shell.positional_params == ['arg2', 'arg3']
        # Other variables should be unchanged
        assert shell.variables['HOME'] == '/home/user'
        assert shell.variables['PATH'] == '/usr/bin'