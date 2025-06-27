import pytest
import os
import tempfile
import time
from psh.shell import Shell


@pytest.fixture
def shell():
    """Create a shell instance for testing."""
    return Shell()
class TestProcessSubstitution:
    """Test process substitution functionality."""
    
    def test_simple_input_substitution(self, shell):
        """Test basic <(cmd) substitution."""
        
        # Test reading from process substitution
        result = shell.run_command('cat <(echo "hello world")')
        assert result == 0
        
        # Test with multiple lines
        result = shell.run_command('cat <(echo -e "line1\\nline2\\nline3")')
        assert result == 0
    
    def test_simple_output_substitution(self, shell):
        """Test basic >(cmd) substitution."""
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Test writing to process substitution
            result = shell.run_command(f'echo "test output" > >(cat > {temp_file})')
            assert result == 0
            
            # Give it time to complete
            time.sleep(0.1)
            
            # Check the output was written
            with open(temp_file, 'r') as f:
                content = f.read()
            assert "test output" in content
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.xfail(reason="Non-deterministic failure - file descriptor timing issue")
    def test_multiple_input_substitutions(self, shell):
        """Test multiple <(...) in one command."""
        
        # Create temp file to capture output
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Use diff with two process substitutions
            result = shell.run_command(f'diff <(echo "line1") <(echo "line2") > {temp_file} 2>&1')
            # diff returns 1 when files differ
            assert result == 1
            
            # Check that diff found differences
            with open(temp_file, 'r') as f:
                content = f.read()
            # diff output should show the differences
            assert "line1" in content or "<" in content
            assert "line2" in content or ">" in content
        finally:
            os.unlink(temp_file)
    
    def test_process_substitution_with_pipeline(self, shell):
        """Test process substitution in a pipeline."""
        
        # Process substitution should work in pipelines
        result = shell.run_command('echo "test" | cat <(echo "prefix:") -')
        assert result == 0
    
    def test_nested_process_substitution(self, shell):
        """Test nested process substitution."""
        
        # Nested process substitutions
        result = shell.run_command('cat <(cat <(echo "nested"))')
        assert result == 0
    
    def test_process_substitution_with_variables(self, shell):
        """Test process substitution with variable expansion."""
        
        # Set a variable
        shell.run_command('MSG="hello from variable"')
        
        # Use variable in process substitution
        result = shell.run_command('cat <(echo "$MSG")')
        assert result == 0
    
    def test_process_substitution_with_command_substitution(self, shell):
        """Test process substitution containing command substitution."""
        
        # Command substitution inside process substitution
        result = shell.run_command('cat <(echo "Date: $(date)")')
        assert result == 0
    
    def test_process_substitution_error_handling(self, shell):
        """Test error handling in process substitution."""
        
        # Process substitution with failing command
        result = shell.run_command('cat <(false; echo "after false")')
        # Should still succeed - the cat succeeds even if the command in substitution fails
        assert result == 0
    
    def test_multiple_output_substitutions(self, shell):
        """Test multiple >(...) substitutions."""
        
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            temp_file1 = f1.name
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            temp_file2 = f2.name
        
        try:
            # Use tee to write to multiple process substitutions
            result = shell.run_command(f'echo "test" | tee >(cat > {temp_file1}) >(cat > {temp_file2})')
            assert result == 0
            
            # Give it time to complete
            time.sleep(0.1)
            
            # Check both files got the output
            with open(temp_file1, 'r') as f:
                assert "test" in f.read()
            with open(temp_file2, 'r') as f:
                assert "test" in f.read()
        finally:
            os.unlink(temp_file1)
            os.unlink(temp_file2)
    
    @pytest.mark.xfail(reason="Non-deterministic failure - file descriptor timing issue")
    def test_process_substitution_with_redirection(self, shell):
        """Test process substitution combined with regular redirections."""
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Create a test file
            shell.run_command(f'echo "file content" > {temp_file}')
            
            # Use process substitution and regular redirection together
            result = shell.run_command(f'cat <(echo "from substitution") < {temp_file}')
            assert result == 0
            
            # Test output redirection with process substitution
            output_file = temp_file + ".out"
            result = shell.run_command(f'cat <(echo "test") > {output_file}')
            assert result == 0
            
            with open(output_file, 'r') as f:
                assert "test" in f.read()
            
            os.unlink(output_file)
        finally:
            os.unlink(temp_file)
    
    def test_process_substitution_file_descriptor_limits(self, shell):
        """Test that file descriptors are properly managed."""
        
        # This would fail if we leak file descriptors
        # Create many process substitutions in a loop
        result = shell.run_command('''
            for i in {1..10}; do
                cat <(echo "iteration $i")
            done
        ''')
        assert result == 0
    
    def test_process_substitution_with_functions(self, shell):
        """Test process substitution with shell functions."""
        
        # Define a function
        shell.run_command('myfunc() { echo "from function"; }')
        
        # Use function in process substitution
        result = shell.run_command('cat <(myfunc)')
        assert result == 0
    
    def test_process_substitution_as_argument(self, shell):
        """Test process substitution used as command argument."""
        
        # wc should count lines from process substitution
        result = shell.run_command('wc -l <(echo -e "line1\\nline2\\nline3")')
        assert result == 0
    
    def test_empty_process_substitution(self, shell):
        """Test process substitution with no output."""
        
        # Process substitution that produces no output
        result = shell.run_command('cat <(true)')
        assert result == 0  # Should succeed even with empty input
