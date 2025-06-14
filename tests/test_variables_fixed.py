"""Test variables with fixed output capture."""

import pytest
import os
from psh.shell import Shell
from .compat import get_capture


class TestVariablesFixed:
    """Test variable functionality with proper output capture."""
    
    def test_parameter_expansion_default(self, shell, capsys):
        """Test ${var:-default} expansion"""
        capture = get_capture(shell, capsys)
        
        # Unset variable uses default
        shell.run_command('echo ${UNSET:-default}')
        captured = capture.readouterr()
        assert captured.out.strip() == "default"
        
        # Empty variable uses default
        shell.run_command('EMPTY=')
        shell.run_command('echo ${EMPTY:-default}')
        captured = capture.readouterr()
        assert captured.out.strip() == "default"
        
        # Set variable uses its value
        shell.run_command('SET=value')
        shell.run_command('echo ${SET:-default}')
        captured = capture.readouterr()
        assert captured.out.strip() == "value"
    
    def test_simple_echo(self, shell, capsys):
        """Test simple echo command."""
        capture = get_capture(shell, capsys)
        
        shell.run_command('echo hello world')
        captured = capture.readouterr()
        assert captured.out == "hello world\n"