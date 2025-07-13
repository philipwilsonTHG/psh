"""
Unit tests for tilde expansion in PSH.

Tests cover:
- Basic home directory expansion (~)
- User home directory expansion (~user)
- Tilde in various positions
- Multiple tildes
- Tilde with paths
- Quoted tildes (no expansion)
- Special cases
"""

import pytest
import os
import pwd


class TestBasicTildeExpansion:
    """Test basic tilde expansion."""
    
    def test_simple_tilde(self, shell, capsys):
        """Test ~ expands to home directory."""
        shell.run_command('echo ~')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    def test_tilde_with_slash(self, shell, capsys):
        """Test ~/ expands correctly."""
        shell.run_command('echo ~/')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home + '/'
    
    def test_tilde_with_path(self, shell, capsys):
        """Test ~/path expansion."""
        shell.run_command('echo ~/Documents')
        captured = capsys.readouterr()
        expected = os.path.expanduser('~/Documents')
        assert captured.out.strip() == expected
    
    def test_tilde_in_variable(self, shell, capsys):
        """Test tilde expansion in variable assignment."""
        shell.run_command('DIR=~')
        shell.run_command('echo "$DIR"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home    
    def test_tilde_when_pwd_unset(self, shell, capsys):
        """Test ~+ when PWD is unset."""
        shell.run_command('unset PWD')
        shell.run_command('echo ~+')
        captured = capsys.readouterr()
        # Should still work (fallback to getcwd)
        assert len(captured.out.strip()) > 0