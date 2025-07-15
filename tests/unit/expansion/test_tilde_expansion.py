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


class TestUserTildeExpansion:
    """Test tilde expansion with usernames."""
    
    def test_tilde_user_expansion(self, shell, capsys):
        """Test ~username expands to user's home directory."""
        # Get current user for testing
        current_user = pwd.getpwuid(os.getuid())
        username = current_user.pw_name
        home_dir = current_user.pw_dir
        
        shell.run_command(f'echo ~{username}')
        captured = capsys.readouterr()
        assert captured.out.strip() == home_dir
    
    def test_tilde_user_with_path(self, shell, capsys):
        """Test ~username/path expands correctly."""
        current_user = pwd.getpwuid(os.getuid())
        username = current_user.pw_name
        home_dir = current_user.pw_dir
        
        shell.run_command(f'echo ~{username}/Documents')
        captured = capsys.readouterr()
        assert captured.out.strip() == f"{home_dir}/Documents"
    
    def test_tilde_invalid_user(self, shell, capsys):
        """Test ~invaliduser handles gracefully."""
        shell.run_command('echo ~nonexistentuser123')
        captured = capsys.readouterr()
        # Should either leave unexpanded or handle gracefully
        assert "~nonexistentuser123" in captured.out


class TestTildeEdgeCases:
    """Test edge cases for tilde expansion."""
    
    def test_quoted_tilde_not_expanded(self, shell, capsys):
        """Test quoted tilde is not expanded."""
        shell.run_command("echo '~'")
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
        
        shell.run_command('echo "~"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
    
    def test_tilde_in_middle_not_expanded(self, shell, capsys):
        """Test tilde in middle of string is not expanded."""
        shell.run_command('echo foo~bar')
        captured = capsys.readouterr()
        assert captured.out.strip() == "foo~bar"
    
    def test_escaped_tilde_not_expanded(self, shell, capsys):
        """Test escaped tilde is not expanded."""
        shell.run_command(r'echo \~')
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
    
    def test_multiple_tildes_in_arguments(self, shell, capsys):
        """Test multiple tildes in one command."""
        shell.run_command('echo ~ ~')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == f"{home} {home}"
    
    def test_tilde_no_home_env(self, shell, capsys):
        """Test tilde expansion when HOME is unset."""
        shell.run_command('unset HOME')
        shell.run_command('echo ~')
        captured = capsys.readouterr()
        # Should handle gracefully - either error or fallback
        output = captured.out.strip()
        assert output == "~" or "/" in output  # Either unexpanded or some path