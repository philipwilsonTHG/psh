"""Tests for tilde expansion functionality."""
import os
import pwd
import pytest
from unittest.mock import patch
from psh.shell import Shell


class TestTildeExpansion:
    """Test tilde expansion in various contexts."""
    
    def setup_method(self):
        """Set up test environment."""
        self.shell = Shell()
        self.original_home = os.environ.get('HOME', '/home/user')
        
    def test_basic_tilde_expansion(self, capsys):
        """Test that ~ expands to HOME directory."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            self.shell.run_command('echo ~')
            captured = capsys.readouterr()
            assert captured.out.strip() == '/home/testuser'
    
    def test_tilde_with_path(self, capsys):
        """Test that ~/path expands correctly."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            self.shell.run_command('echo ~/Documents')
            captured = capsys.readouterr()
            assert captured.out.strip() == '/home/testuser/Documents'
    
    def test_tilde_user_expansion(self, capsys):
        """Test that ~username expands to user's home directory."""
        # Get current user for testing
        current_user = pwd.getpwuid(os.getuid())
        username = current_user.pw_name
        home_dir = current_user.pw_dir
        
        self.shell.run_command(f'echo ~{username}')
        captured = capsys.readouterr()
        assert captured.out.strip() == home_dir
    
    def test_tilde_user_with_path(self, capsys):
        """Test that ~username/path expands correctly."""
        # Get current user for testing
        current_user = pwd.getpwuid(os.getuid())
        username = current_user.pw_name
        home_dir = current_user.pw_dir
        
        self.shell.run_command(f'echo ~{username}/Documents')
        captured = capsys.readouterr()
        assert captured.out.strip() == f'{home_dir}/Documents'
    
    def test_tilde_invalid_user(self, capsys):
        """Test that ~invaliduser remains unexpanded."""
        self.shell.run_command('echo ~nonexistentuser12345')
        captured = capsys.readouterr()
        assert captured.out.strip() == '~nonexistentuser12345'
    
    def test_quoted_tilde_not_expanded(self, capsys):
        """Test that quoted tildes are not expanded."""
        # Single quotes
        self.shell.run_command("echo '~'")
        captured = capsys.readouterr()
        assert captured.out.strip() == '~'
        
        # Double quotes
        self.shell.run_command('echo "~"')
        captured = capsys.readouterr()
        assert captured.out.strip() == '~'
    
    def test_tilde_in_middle_not_expanded(self, capsys):
        """Test that tilde in middle of word is not expanded."""
        self.shell.run_command('echo foo~bar')
        captured = capsys.readouterr()
        assert captured.out.strip() == 'foo~bar'
    
    @pytest.mark.visitor_xfail(reason="Visitor executor needs proper tilde expansion in redirection targets")
    def test_tilde_with_redirection(self):
        """Test tilde expansion in redirections."""
        with patch.dict(os.environ, {'HOME': '/tmp'}):
            test_file = '/tmp/tilde_test.txt'
            try:
                self.shell.run_command('echo "test content" > ~/tilde_test.txt')
                assert os.path.exists(test_file)
                with open(test_file, 'r') as f:
                    assert f.read().strip() == 'test content'
            finally:
                if os.path.exists(test_file):
                    os.unlink(test_file)
    
    def test_tilde_no_home_env(self, capsys):
        """Test tilde expansion when HOME is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove HOME from environment
            if 'HOME' in os.environ:
                del os.environ['HOME']
            
            # Should expand to pwd.getpwuid's home directory
            current_user = pwd.getpwuid(os.getuid())
            expected_home = current_user.pw_dir
            
            self.shell.run_command('echo ~')
            captured = capsys.readouterr()
            assert captured.out.strip() == expected_home
    
    def test_multiple_tildes_in_arguments(self, capsys):
        """Test multiple arguments with tildes."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            self.shell.run_command('echo ~ ~/Documents ~/Downloads')
            captured = capsys.readouterr()
            assert captured.out.strip() == '/home/testuser /home/testuser/Documents /home/testuser/Downloads'
    
    def test_tilde_in_variable_assignment(self):
        """Test tilde expansion in variable assignments."""
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            self.shell.run_command('MYPATH=~/Documents')
            assert self.shell.variables.get('MYPATH') == '/home/testuser/Documents'
    
    def test_escaped_tilde_not_expanded(self, capsys):
        """Test that escaped tildes are not expanded."""
        # TODO: This test requires tracking escaped characters through the pipeline
        # Currently, the tokenizer removes backslashes, so we can't distinguish
        # between ~ and \~ at execution time. This would require modifying
        # the tokenizer to mark escaped tokens or preserve escape information.
        pytest.skip("Escaped tilde handling requires architectural changes")