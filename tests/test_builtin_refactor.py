"""Tests for the refactored builtin system."""

import pytest
import os
import sys
from psh.shell import Shell
from psh.builtins import registry


class TestBuiltinRefactor:
    """Test the new builtin system."""
    
    def test_registry_has_builtins(self):
        """Test that builtins are registered."""
        # Check that expected builtins are registered
        assert registry.has('echo')
        assert registry.has('pwd')
        assert registry.has('cd')
        assert registry.has('exit')
        assert registry.has('true')
        assert registry.has('false')
        assert registry.has(':')
    
    def test_builtin_names(self):
        """Test getting all builtin names."""
        names = registry.names()
        assert 'echo' in names
        assert 'pwd' in names
        assert 'cd' in names
        assert ':' in names
        # Should not include aliases in names()
        assert '[' not in names  # This would be an alias for test when migrated
    
    def test_echo_builtin(self, capsys):
        """Test echo builtin through new system."""
        shell = Shell()
        exit_code = shell.run_command("echo Hello World")
        captured = capsys.readouterr()
        assert captured.out == "Hello World\n"
        assert exit_code == 0
    
    def test_pwd_builtin(self, capsys):
        """Test pwd builtin through new system."""
        shell = Shell()
        cwd = os.getcwd()
        exit_code = shell.run_command("pwd")
        captured = capsys.readouterr()
        assert captured.out.strip() == cwd
        assert exit_code == 0
    
    def test_cd_builtin(self, capsys):
        """Test cd builtin through new system."""
        shell = Shell()
        original_dir = os.getcwd()
        
        try:
            # Change to /tmp (handle macOS symlink)
            exit_code = shell.run_command("cd /tmp")
            assert exit_code == 0
            # On macOS, /tmp is a symlink to /private/tmp
            assert os.getcwd() in ["/tmp", "/private/tmp"]
            
            # Test cd with no args (should go to HOME)
            home = os.environ.get('HOME', '/')
            exit_code = shell.run_command("cd")
            assert exit_code == 0
            assert os.getcwd() == home
            
        finally:
            os.chdir(original_dir)
    
    def test_true_false_builtins(self):
        """Test true and false builtins."""
        shell = Shell()
        
        # Test true
        exit_code = shell.run_command("true")
        assert exit_code == 0
        
        # Test false
        exit_code = shell.run_command("false")
        assert exit_code == 1
    
    def test_colon_builtin(self):
        """Test colon (:) builtin."""
        shell = Shell()
        
        # Colon should do nothing and return 0
        exit_code = shell.run_command(": this is ignored")
        assert exit_code == 0
        
        # Should work with variable expansion side effects
        shell.run_command("x=1")
        exit_code = shell.run_command(": ${x:=2}")  # Won't change x since it's set
        assert exit_code == 0
        assert shell.variables['x'] == '1'
    
    def test_builtin_with_redirection(self, tmp_path):
        """Test that builtins work with redirection."""
        shell = Shell()
        output_file = tmp_path / "output.txt"
        
        # Test echo with redirection
        exit_code = shell.run_command(f"echo Hello > {output_file}")
        assert exit_code == 0
        
        content = output_file.read_text()
        assert content == "Hello\n"
        
        # Test pwd with redirection
        pwd_file = tmp_path / "pwd.txt"
        exit_code = shell.run_command(f"pwd > {pwd_file}")
        assert exit_code == 0
        
        content = pwd_file.read_text().strip()
        assert content == os.getcwd()
    
    @pytest.mark.skip(reason="Pipeline with builtin output capture issue")
    def test_builtin_in_pipeline(self, tmp_path):
        """Test builtins in pipelines."""
        shell = Shell()
        
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Test echo in a simple pipeline
        output_file = tmp_path / "output.txt"
        exit_code = shell.run_command(f"echo hello world | wc -w > {output_file}")
        assert exit_code == 0
        
        # Check the output - should be 2 words
        count = output_file.read_text().strip()
        assert "2" in count
    
    def test_builtin_help(self):
        """Test that builtins have help text."""
        echo_builtin = registry.get('echo')
        assert echo_builtin is not None
        assert 'echo' in echo_builtin.help
        
        pwd_builtin = registry.get('pwd')
        assert pwd_builtin is not None
        assert 'pwd' in pwd_builtin.help
        
        colon_builtin = registry.get(':')
        assert colon_builtin is not None
        assert 'Null command' in colon_builtin.help