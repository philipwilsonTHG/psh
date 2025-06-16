"""Simple tests for cd - functionality."""

import os
import tempfile
import pytest
from unittest.mock import MagicMock
from io import StringIO

from psh.builtins.navigation import CdBuiltin


class TestCdDashSimple:
    """Simple test cases for cd - functionality."""
    
    def test_cd_dash_basic_functionality(self, tmp_path):
        """Test basic cd - functionality."""
        cd_builtin = CdBuiltin()
        
        # Create test directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        original_cwd = os.getcwd()
        try:
            # Start in dir1
            os.chdir(str(dir1))
            
            # Set up shell with OLDPWD pointing to dir2
            shell = MagicMock()
            shell.env = {'OLDPWD': str(dir2)}
            shell.stderr = StringIO()
            # Remove _expand_tilde to avoid mock issues
            del shell._expand_tilde
            
            # Execute cd -
            result = cd_builtin.execute(['cd', '-'], shell)
            
            # Should succeed
            assert result == 0
            
            # Should change to dir2
            assert os.getcwd() == str(dir2)
            
            # Should update environment
            assert shell.env['OLDPWD'] == str(dir1)
            assert shell.env['PWD'] == str(dir2)
            
        finally:
            os.chdir(original_cwd)
    
    def test_cd_dash_no_oldpwd(self):
        """Test cd - when OLDPWD is not set."""
        cd_builtin = CdBuiltin()
        shell = MagicMock()
        shell.env = {}  # No OLDPWD
        shell.stderr = StringIO()
        
        result = cd_builtin.execute(['cd', '-'], shell)
        
        # Should fail
        assert result == 1
        
        # Should show error message
        error_output = shell.stderr.getvalue()
        assert "OLDPWD not set" in error_output
    
    def test_cd_normal_updates_oldpwd(self, tmp_path):
        """Test that normal cd updates OLDPWD."""
        cd_builtin = CdBuiltin()
        
        # Create test directory
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        
        original_cwd = os.getcwd()
        try:
            shell = MagicMock()
            shell.env = {'PWD': original_cwd}
            shell.stderr = StringIO()
            # Remove _expand_tilde to avoid mock issues
            del shell._expand_tilde
            
            # Change to test directory
            result = cd_builtin.execute(['cd', str(test_dir)], shell)
            
            # Should succeed
            assert result == 0
            
            # Should update OLDPWD to original directory
            assert shell.env['OLDPWD'] == original_cwd
            assert shell.env['PWD'] == str(test_dir)
            
        finally:
            os.chdir(original_cwd)
    
    def test_cd_help_includes_dash(self):
        """Test that cd help mentions the - option."""
        cd_builtin = CdBuiltin()
        
        help_text = cd_builtin.help
        assert "Previous working directory" in help_text
        assert "-" in help_text
    
    def test_cd_dash_switches_back_and_forth(self, tmp_path, capsys):
        """Test cd - multiple times."""
        cd_builtin = CdBuiltin()
        
        # Create test directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        original_cwd = os.getcwd()
        try:
            # Start in dir1
            os.chdir(str(dir1))
            
            shell = MagicMock()
            shell.env = {'OLDPWD': str(dir2), 'PWD': str(dir1)}
            shell.stderr = StringIO()
            # Remove _expand_tilde to avoid mock issues
            del shell._expand_tilde
            
            # First cd - (should go to dir2)
            result1 = cd_builtin.execute(['cd', '-'], shell)
            assert result1 == 0
            assert os.getcwd() == str(dir2)
            assert shell.env['OLDPWD'] == str(dir1)
            
            # Second cd - (should go back to dir1)
            result2 = cd_builtin.execute(['cd', '-'], shell)
            assert result2 == 0
            assert os.getcwd() == str(dir1)
            assert shell.env['OLDPWD'] == str(dir2)
            
            # Check that directories were printed
            captured = capsys.readouterr()
            output_lines = captured.out.strip().split('\n')
            assert str(dir2) in output_lines[0]
            assert str(dir1) in output_lines[1]
            
        finally:
            os.chdir(original_cwd)