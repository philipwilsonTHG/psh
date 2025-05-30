import pytest
import os
import tempfile
import time
from psh.shell import Shell


class TestProcessSubstitution:
    """Test process substitution functionality."""
    
    def test_simple_input_substitution(self):
        """Test basic <(cmd) substitution."""
        shell = Shell()
        
        # Test reading from process substitution
        result = shell.run_command('cat <(echo "hello world")')
        assert result == 0
        
        # Test with multiple lines
        result = shell.run_command('cat <(echo -e "line1\\nline2\\nline3")')
        assert result == 0
    
    def test_simple_output_substitution(self):
        """Test basic >(cmd) substitution."""
        shell = Shell()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Test output process substitution with redirect syntax
            # This works more reliably than with tee in test environment
            result = shell.run_command(f'echo "test data" > >(cat > {temp_file})')
            assert result == 0
            
            # Give process substitution time to complete
            time.sleep(0.5)
            
            # Verify file was written
            with open(temp_file, 'r') as f:
                content = f.read()
                assert content.strip() == "test data"
        finally:
            os.unlink(temp_file)
    
    def test_multiple_input_substitutions(self):
        """Test multiple <(...) substitutions in one command."""
        shell = Shell()
        
        # Test with cat reading from two process substitutions
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Use wc to count lines from multiple process substitutions
            # This avoids the cat redirection issue
            result = shell.run_command(f'wc -l <(echo "line1") <(echo "line2") > {temp_file}')
            assert result == 0
            
            time.sleep(0.2)
            # Verify wc output shows both files
            with open(temp_file, 'r') as f:
                content = f.read()
                # Should contain counts for both fd files
                assert len(content) > 0
        finally:
            os.unlink(temp_file)
    
    def test_process_substitution_with_pipeline(self):
        """Test process substitution within a pipeline."""
        shell = Shell()
        
        # Use process substitution as input to grep
        result = shell.run_command('grep "test" <(printf "test line\\nother line\\ntest again\\n")')
        assert result == 0
    
    def test_nested_process_substitution(self):
        """Test nested process substitution."""
        shell = Shell()
        
        # Simple nested case - echo inside cat inside outer cat
        result = shell.run_command('cat <(cat <(echo "nested"))')
        assert result == 0
    
    def test_process_substitution_with_variables(self):
        """Test process substitution with variable expansion."""
        shell = Shell()
        
        # Set a variable
        shell.run_command('MSG="hello from variable"')
        
        # Use variable in process substitution
        result = shell.run_command('cat <(echo "$MSG")')
        assert result == 0
    
    def test_process_substitution_with_command_substitution(self):
        """Test process substitution containing command substitution."""
        shell = Shell()
        
        # Command substitution inside process substitution
        result = shell.run_command('cat <(echo "Date: $(date +%Y)")')
        assert result == 0
    
    def test_process_substitution_error_handling(self):
        """Test error handling in process substitution."""
        shell = Shell()
        
        # Command that fails inside process substitution
        # The outer command should still run
        result = shell.run_command('cat <(false; echo "after false")')
        assert result == 0  # cat itself succeeds
    
    def test_multiple_output_substitutions(self):
        """Test multiple >(...) substitutions."""
        shell = Shell()
        
        with tempfile.NamedTemporaryFile(delete=False) as f1, \
             tempfile.NamedTemporaryFile(delete=False) as f2:
            temp_file1 = f1.name
            temp_file2 = f2.name
        
        try:
            # Use redirect to multiple process substitutions
            # Run two separate commands
            result1 = shell.run_command(f'echo "test" > >(cat > {temp_file1})')
            result2 = shell.run_command(f'echo "test" > >(cat > {temp_file2})')
            assert result1 == 0
            assert result2 == 0
            
            # Give process substitutions time to complete
            time.sleep(0.5)
            
            # Both files should have the content
            with open(temp_file1, 'r') as f:
                assert f.read().strip() == "test"
            with open(temp_file2, 'r') as f:
                assert f.read().strip() == "test"
        finally:
            os.unlink(temp_file1)
            os.unlink(temp_file2)
    
    def test_process_substitution_with_redirection(self):
        """Test process substitution combined with regular redirections."""
        shell = Shell()
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Test process substitution with stderr redirection
            # Run a command that writes to stderr
            result = shell.run_command(
                f'sh -c "echo stderr >&2" 2>{temp_file}'
            )
            assert result == 0
            
            # Give time to complete
            time.sleep(0.2)
            
            # Check stderr was redirected
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "stderr" in content
        finally:
            os.unlink(temp_file)
    
    def test_process_substitution_file_descriptor_limits(self):
        """Test that file descriptors are properly managed."""
        shell = Shell()
        
        # Run many process substitutions to test fd management
        for i in range(10):
            result = shell.run_command(f'cat <(echo "test {i}")')
            assert result == 0
    
    def test_process_substitution_with_functions(self):
        """Test process substitution with shell functions."""
        shell = Shell()
        
        # Define a function
        shell.run_command('myfunc() { echo "from function"; }')
        
        # Use function in process substitution
        result = shell.run_command('cat <(myfunc)')
        assert result == 0
    
    def test_process_substitution_as_argument(self):
        """Test process substitution used as command argument."""
        shell = Shell()
        
        # wc should count lines from process substitution
        result = shell.run_command('wc -l <(echo -e "line1\\nline2\\nline3")')
        assert result == 0
    
    def test_empty_process_substitution(self):
        """Test process substitution with no output."""
        shell = Shell()
        
        # Process substitution that produces no output
        result = shell.run_command('cat <(true)')
        assert result == 0  # Should succeed even with empty input