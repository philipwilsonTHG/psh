import pytest
import os
import tempfile
import time
from io import StringIO
from unittest.mock import patch, MagicMock
from psh.shell import Shell


class TestPipeline:
    def setup_method(self):
        self.shell = Shell()
        # Create a small history to avoid loading large existing history
        self.shell.history = []
        self.shell.history_file = "/tmp/test_psh_history"
    
    def teardown_method(self):
        # Clean up any temp files
        try:
            os.unlink(self.shell.history_file)
        except:
            pass
    
    def test_simple_pipeline(self):
        """Test basic two-command pipeline"""
        # Since we're using fork/exec, we need to test with real commands
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("hello\nworld\ntest\n")
            temp_file = f.name
        
        try:
            # Run pipeline: cat file | grep world
            output_file = "/tmp/pipeline_test_output.txt"
            self.shell.run_command(f"cat {temp_file} | grep world > {output_file}")
            
            # Check output
            with open(output_file, 'r') as f:
                output = f.read()
            assert output.strip() == "world"
            
            os.unlink(output_file)
        finally:
            os.unlink(temp_file)
    
    def test_three_command_pipeline(self):
        """Test pipeline with three commands"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("banana\napple\ncherry\napricot\n")
            temp_file = f.name
        
        try:
            output_file = "/tmp/pipeline_test_output2.txt"
            # Pipeline: cat file | grep a | sort
            self.shell.run_command(f"cat {temp_file} | grep a | sort > {output_file}")
            
            with open(output_file, 'r') as f:
                lines = f.read().strip().split('\n')
            
            assert lines == ["apple", "apricot", "banana"]
            os.unlink(output_file)
        finally:
            os.unlink(temp_file)
    
    def test_pipeline_exit_status(self):
        """Test that pipeline returns exit status of last command"""
        # Successful pipeline
        exit_code = self.shell.run_command("echo hello | cat")
        assert exit_code == 0
        assert self.shell.last_exit_code == 0
        
        # Pipeline with failed last command
        exit_code = self.shell.run_command("echo hello | nonexistentcommand 2>/dev/null")
        assert exit_code == 127
        assert self.shell.last_exit_code == 127
    
    def test_pipeline_with_builtin(self):
        """Test pipeline with built-in commands"""
        import tempfile
        
        # Create temporary file for output capture
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            output_file = f.name
        
        try:
            # echo is a built-in
            result = self.shell.run_command(f"echo hello world | grep hello > {output_file}")
            assert result == 0
            
            with open(output_file, 'r') as f:
                output = f.read()
            assert output.strip() == "hello world"
        finally:
            os.unlink(output_file)
    
    def test_pipeline_with_redirection(self):
        """Test pipeline with input/output redirection"""
        # Create input file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test1\ntest2\ntest3\n")
            input_file = f.name
        
        output_file = "/tmp/pipeline_redir_test.txt"
        
        try:
            # Pipeline with input redirection on first command
            self.shell.run_command(f"cat < {input_file} | grep 2 > {output_file}")
            
            with open(output_file, 'r') as f:
                output = f.read()
            assert output.strip() == "test2"
            
            os.unlink(output_file)
        finally:
            os.unlink(input_file)
    
    def test_empty_pipeline_handling(self):
        """Test that single command doesn't use pipeline execution"""
        # This should use the simple execution path, not fork
        exit_code = self.shell.run_command("echo hello > /tmp/single_cmd_test.txt")
        assert exit_code == 0
        
        with open("/tmp/single_cmd_test.txt", 'r') as f:
            output = f.read()
        assert output.strip() == "hello"
        
        os.unlink("/tmp/single_cmd_test.txt")
    
    def test_pipeline_preserves_order(self):
        """Test that pipeline preserves command output order"""
        output_file = "/tmp/pipeline_order_test.txt"
        
        # Create a command that outputs multiple lines
        self.shell.run_command(f"echo -e 'line1\\nline2\\nline3' > /tmp/temp_lines.txt")
        self.shell.run_command(f"cat /tmp/temp_lines.txt | cat > {output_file}")
        
        with open(output_file, 'r') as f:
            output = f.read()
        
        # Echo now supports -e for escape sequences
        assert "line1\nline2\nline3" in output
        
        os.unlink(output_file)
        os.unlink("/tmp/temp_lines.txt")
    
    def test_broken_pipe_handling(self):
        """Test handling when pipeline command fails"""
        # Middle command fails - but last command (cat) succeeds
        # In Unix shells, the exit code is from the last command
        exit_code = self.shell.run_command("echo hello | nonexistentcmd 2>/dev/null | cat > /dev/null")
        assert exit_code == 0  # cat succeeds, so exit code is 0
    
    def test_pipeline_environment_inheritance(self):
        """Test that environment variables are passed through pipeline"""
        self.shell.env['TEST_PIPE_VAR'] = 'test_value'
        output_file = "/tmp/pipeline_env_test.txt"
        
        # Use printenv to check environment
        self.shell.run_command(f"printenv TEST_PIPE_VAR | cat > {output_file}")
        
        try:
            with open(output_file, 'r') as f:
                output = f.read()
            assert output.strip() == "test_value"
        finally:
            os.unlink(output_file)
            del self.shell.env['TEST_PIPE_VAR']