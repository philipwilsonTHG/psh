import pytest
import os
import tempfile
import subprocess
from io import StringIO
from unittest.mock import patch
from psh.shell import Shell
from psh.lexer import tokenize
from psh.parser import parse


class TestIntegration:
    def setup_method(self):
        self.shell = Shell()
        self.original_cwd = os.getcwd()
    
    def teardown_method(self):
        os.chdir(self.original_cwd)
    
    def test_command_execution_flow(self):
        """Test the full flow from string to execution"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell.run_command("echo hello world")
            assert exit_code == 0
            assert mock_stdout.getvalue() == "hello world\n"
    
    def test_variable_expansion(self):
        """Test variable expansion in commands"""
        # Save original state
        original_test_var = self.shell.env.get('INTEGRATION_TEST_VAR')
        
        try:
            # Use unique variable name to avoid conflicts
            self.shell.env['INTEGRATION_TEST_VAR'] = 'hello'
            
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                self.shell.run_command("echo $INTEGRATION_TEST_VAR")
                assert mock_stdout.getvalue() == "hello\n"
        finally:
            # Restore original state
            if original_test_var is not None:
                self.shell.env['INTEGRATION_TEST_VAR'] = original_test_var
            else:
                self.shell.env.pop('INTEGRATION_TEST_VAR', None)
    
    def test_multiple_commands(self):
        """Test executing multiple commands separated by semicolons"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo first; echo second; echo third")
            assert mock_stdout.getvalue() == "first\n" + "second\n" + "third\n"
    
    def test_redirections_integration(self):
        """Test file redirections in actual command execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Output redirection
            outfile = os.path.join(tmpdir, "output.txt")
            self.shell.run_command(f"echo hello > {outfile}")
            
            with open(outfile, 'r') as f:
                assert f.read() == "hello\n"
            
            # Append redirection
            self.shell.run_command(f"echo world >> {outfile}")
            
            with open(outfile, 'r') as f:
                assert f.read() == "hello\n" + "world\n"
            
            # Input redirection
            infile = os.path.join(tmpdir, "input.txt")
            with open(infile, 'w') as f:
                f.write("test input\n")
            
            outfile2 = os.path.join(tmpdir, "output2.txt")
            
            # Test redirection functionality directly
            exit_code = self.shell.run_command(f"cat < {infile} > {outfile2}")
            assert exit_code == 0
            
            # Verify output file was created and contains expected content
            assert os.path.exists(outfile2)
            with open(outfile2, 'r') as f:
                content = f.read()
            assert content == "test input\n"
    
    def test_export_and_variable_usage(self):
        """Test exporting variables and using them"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("export MY_VAR=test123")
            self.shell.run_command("echo $MY_VAR")
            assert mock_stdout.getvalue() == "test123\n"
    
    def test_cd_and_pwd(self):
        """Test changing directories and pwd"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("cd /tmp")
            self.shell.run_command("pwd")
            output = mock_stdout.getvalue().strip()
            assert output == '/private/tmp' or output == '/tmp'
    
    def test_source_integration(self):
        """Test sourcing a file with multiple commands"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.psh', delete=False) as f:
            f.write("export VAR1=value1\n")
            f.write("export VAR2=value2\n")
            f.write("echo Sourced successfully\n")
            script_path = f.name
        
        try:
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                self.shell.run_command(f"source {script_path}")
                assert "Sourced successfully\n" in mock_stdout.getvalue()
                assert self.shell.env['VAR1'] == 'value1'
                assert self.shell.env['VAR2'] == 'value2'
        finally:
            os.unlink(script_path)
    
    def test_command_not_found(self):
        """Test handling of non-existent commands"""
        exit_code = self.shell.run_command("nonexistentcommand arg1 arg2")
        assert exit_code == 127  # Command not found exit code
    
    def test_parse_error_handling(self):
        """Test handling of parse errors"""
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            # Missing command after pipe
            exit_code = self.shell.run_command("echo hello |")
            assert exit_code == 1
            assert ("Parse error" in mock_stderr.getvalue() or 
                    "Expected command" in mock_stderr.getvalue())
    
    def test_quoted_arguments_integration(self):
        """Test that quoted arguments preserve spaces"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command('echo "hello   world" \'single   quotes\'')
            assert mock_stdout.getvalue() == "hello   world single   quotes\n"
    
    def test_empty_command(self):
        """Test handling of empty commands"""
        exit_code = self.shell.run_command("")
        assert exit_code == 0
        
        exit_code = self.shell.run_command("   ")
        assert exit_code == 0
    
    def test_background_command_integration(self):
        """Test background command execution"""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell.run_command("sleep 0.1 &")
            assert exit_code == 0
            
            # Check that job output is generated (should contain job ID and PID)
            output = mock_stdout.getvalue()
            assert "[1]" in output  # Job ID
            assert len(output.strip()) > 0  # Some output should be generated
    
    def test_complex_command_integration(self):
        """Test a complex command with multiple features"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input file
            infile = os.path.join(tmpdir, "input.txt")
            with open(infile, 'w') as f:
                f.write("line 1\nline 2\nline 3\n")
            
            # Run complex command
            outfile = os.path.join(tmpdir, "output.txt")
            
            # Test pipeline execution
            self.shell.run_command(f"cat < {infile} | grep line > {outfile}")
            
            # Check the output
            with open(outfile, 'r') as f:
                output = f.read()
            assert "line 1" in output
            assert "line 2" in output
            assert "line 3" in output
    
    def test_colon_command(self):
        """Test the colon (:) null command"""
        # Test basic colon command
        exit_code = self.shell.run_command(":")
        assert exit_code == 0
        
        # Test with arguments (should be ignored)
        exit_code = self.shell.run_command(": arg1 arg2 arg3")
        assert exit_code == 0
        
        # Test in loops as empty body
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell.run_command("for i in 1 2 3; do :; done")
            assert exit_code == 0
            # No output expected
            assert mock_stdout.getvalue() == ""
        
        # Test in while loop as placeholder
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell.run_command("while false; do echo should_not_run; done; :")
            assert exit_code == 0
            # Loop should not execute, just the colon at the end
            assert mock_stdout.getvalue() == ""
        
        # Test in conditional as true command
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell.run_command("if :; then echo yes; else echo no; fi")
            assert exit_code == 0
            assert mock_stdout.getvalue().strip() == "yes"