import pytest
import os
import tempfile
import subprocess
from io import StringIO
from unittest.mock import patch
from simple_shell import Shell
from tokenizer import tokenize
from parser import parse


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
        self.shell.env['TEST_VAR'] = 'expanded_value'
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $TEST_VAR")
            assert mock_stdout.getvalue() == "expanded_value\n"
    
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
            with patch.object(subprocess, 'Popen') as mock_popen:
                mock_process = mock_popen.return_value
                mock_process.wait.return_value = 0
                mock_process.returncode = 0
                
                self.shell.run_command(f"cat < {infile} > {outfile2}")
                
                # Verify Popen was called with correct stdin
                mock_popen.assert_called_once()
                args, kwargs = mock_popen.call_args
                assert args[0] == ['cat']
                assert kwargs['stdin'].name == infile
                assert kwargs['stdout'].name == outfile2
    
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
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            exit_code = self.shell.run_command("nonexistentcommand arg1 arg2")
            assert exit_code == 127
            assert "command not found" in mock_stderr.getvalue()
    
    def test_parse_error_handling(self):
        """Test handling of parse errors"""
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            # Missing command after pipe
            exit_code = self.shell.run_command("echo hello |")
            assert exit_code == 1
            assert "Parse error" in mock_stderr.getvalue()
    
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
        with patch.object(subprocess, 'Popen') as mock_popen:
            mock_process = mock_popen.return_value
            mock_process.pid = 12345
            
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                self.shell.run_command("sleep 10 &")
                assert "[12345]" in mock_stdout.getvalue()
                
                # Verify process was NOT waited for
                mock_process.wait.assert_not_called()
    
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