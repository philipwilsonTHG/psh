import pytest
import os
import subprocess
from io import StringIO
from unittest.mock import patch, MagicMock
from simple_shell import Shell


class TestExitStatus:
    def setup_method(self):
        self.shell = Shell()
    
    def test_initial_exit_status(self):
        """Test that initial exit status is 0"""
        assert self.shell.last_exit_code == 0
    
    def test_successful_command_exit_status(self):
        """Test that successful commands set exit status to 0"""
        with patch('sys.stdout', new=StringIO()):
            self.shell.run_command("echo hello")
            assert self.shell.last_exit_code == 0
    
    def test_failed_command_exit_status(self):
        """Test that failed commands set appropriate exit status"""
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("nonexistentcommand")
            assert self.shell.last_exit_code == 127
    
    def test_builtin_command_exit_status(self):
        """Test exit status for built-in commands"""
        # Successful built-in
        self.shell.run_command("pwd")
        assert self.shell.last_exit_code == 0
        
        # Failed built-in (cd to non-existent directory)
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("cd /nonexistent/directory")
            assert self.shell.last_exit_code == 1
    
    def test_exit_status_variable(self):
        """Test $? variable expansion"""
        # Set exit status to 0
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo hello")
            assert self.shell.last_exit_code == 0
            
            # Check $? expands to 0
            mock_stdout.truncate(0)
            mock_stdout.seek(0)
            self.shell.run_command("echo $?")
            assert mock_stdout.getvalue().strip() == "0"
        
        # Set exit status to non-zero
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("nonexistentcommand")
            assert self.shell.last_exit_code == 127
        
        # Check $? expands to 127
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $?")
            assert mock_stdout.getvalue().strip() == "127"
    
    def test_multiple_commands_exit_status(self):
        """Test exit status with multiple commands"""
        with patch('sys.stdout', new=StringIO()):
            with patch('sys.stderr', new=StringIO()):
                # First command succeeds, second fails
                self.shell.run_command("echo hello; nonexistentcommand")
                assert self.shell.last_exit_code == 127
                
                # Both commands succeed
                self.shell.run_command("echo first; echo second")
                assert self.shell.last_exit_code == 0
    
    def test_parse_error_exit_status(self):
        """Test exit status when parse errors occur"""
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("echo hello >")
            assert self.shell.last_exit_code == 1
    
    def test_exit_status_prompt_display(self):
        """Test that non-zero exit status appears in prompt"""
        # Set non-zero exit status
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("nonexistentcommand")
        
        # Simulate getting the prompt
        if self.shell.last_exit_code != 0:
            prompt = f"[{self.shell.last_exit_code}] {os.getcwd()}$ "
        else:
            prompt = f"{os.getcwd()}$ "
        
        assert "[127]" in prompt
        
        # Reset to zero exit status
        with patch('sys.stdout', new=StringIO()):
            self.shell.run_command("echo hello")
        
        if self.shell.last_exit_code != 0:
            prompt = f"[{self.shell.last_exit_code}] {os.getcwd()}$ "
        else:
            prompt = f"{os.getcwd()}$ "
        
        assert "[" not in prompt
    
    def test_external_command_exit_status(self):
        """Test exit status from external commands"""
        with patch.object(subprocess, 'Popen') as mock_popen:
            # Simulate successful external command
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            self.shell.run_command("ls")
            assert self.shell.last_exit_code == 0
            
            # Simulate failed external command
            mock_process.wait.return_value = 2
            mock_process.returncode = 2
            
            self.shell.run_command("ls")
            assert self.shell.last_exit_code == 2
    
    def test_exit_status_preserved_across_empty_commands(self):
        """Test that empty commands don't reset exit status"""
        # Set non-zero exit status
        with patch('sys.stderr', new=StringIO()):
            self.shell.run_command("nonexistentcommand")
            assert self.shell.last_exit_code == 127
        
        # Run empty command
        self.shell.run_command("")
        assert self.shell.last_exit_code == 127  # Should remain unchanged
        
        self.shell.run_command("   ")
        assert self.shell.last_exit_code == 127  # Should still remain unchanged