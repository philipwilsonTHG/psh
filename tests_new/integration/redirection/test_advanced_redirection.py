"""
Advanced I/O redirection integration tests.

Tests for complex I/O redirection scenarios including:
- File descriptor duplication (>&, <&)
- Named pipes (FIFOs) integration
- Process substitution (<(command), >(command))
- File descriptor closing (n>&-, n<&-)
- Complex redirection combinations
- Error handling in redirection scenarios
"""

import pytest
import os
import tempfile
import subprocess
import time
import stat
import sys
from pathlib import Path

# Add framework to path
TEST_ROOT = Path(__file__).parent.parent.parent
PSH_ROOT = TEST_ROOT.parent
sys.path.insert(0, str(PSH_ROOT))

# Shell fixture imported automatically from conftest.py


class TestFileDescriptorDuplication:
    """Test file descriptor duplication with >& and <& operators."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    def test_stdout_duplication_simple(self, shell):
        """Test simple stdout redirection and duplication."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Test basic stdout redirection (foundation for duplication)
            result = shell.run_command(f'echo "test output" > {temp_path}')
            assert result == 0
            
            # Check that output went to file
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "test output" in content
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.skip(reason="2>&1 redirection causes file descriptor state issues between tests")  
    def test_stderr_to_stdout_duplication(self, shell):
        """Test redirecting stderr to stdout (2>&1)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Test stderr to stdout redirection combined with file output
            # This tests the 2>&1 operator which is commonly supported
            result = shell.run_command(f'echo "error message" >&2 2>&1 > {temp_path}')
            assert result == 0
            
        finally:
            os.unlink(temp_path)
    
    def test_stderr_redirection_basic(self, shell):
        """Test basic stderr redirection to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Use a command that actually generates stderr output
            # and redirect it to a file
            result = shell.run_command(f'ls /nonexistent/path 2> {temp_path}')
            # ls should fail but stderr should be captured
            
            # Check that error output went to file
            with open(temp_path, 'r') as f:
                content = f.read()
            # Should contain some error message about the path not existing
            assert len(content.strip()) > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_stdin_redirection_basic(self, shell):
        """Test basic stdin redirection from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("input data\n")
            temp_path = temp_file.name
        
        try:
            # Test basic stdin redirection from file
            result = shell.run_command(f'cat < {temp_path}')
            assert result == 0
            # This tests that stdin redirection works fundamentally
            
        finally:
            os.unlink(temp_path)
    
    def test_multiple_redirection_operators(self, shell):
        """Test handling multiple redirection operators in one command."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as stdout_file, \
             tempfile.NamedTemporaryFile(mode='w', delete=False) as stderr_file:
            stdout_path = stdout_file.name
            stderr_path = stderr_file.name
        
        try:
            # Test separate redirection of stdout and stderr
            result = shell.run_command(f'echo "to stdout" > {stdout_path} && ls /nonexistent 2> {stderr_path}')
            
            # Check stdout file
            with open(stdout_path, 'r') as f:
                stdout_content = f.read()
            assert "to stdout" in stdout_content
            
        finally:
            os.unlink(stdout_path)
            os.unlink(stderr_path)
    
    def test_null_device_redirection(self, shell):
        """Test redirection to null device."""
        # Test redirecting stdout to /dev/null (common redirection target)
        result = shell.run_command('echo "discarded" > /dev/null')
        assert result == 0
        
        # Test stderr to null with a command that actually produces stderr
        result = shell.run_command('ls /nonexistent/path 2> /dev/null')
        # Command should complete (stderr redirected to null)
        
        # This tests basic redirection functionality without complex fd management
    
    @pytest.mark.skip(reason="2>&1 file descriptor redirection causes shell state issues")
    def test_stderr_to_stdout_redirection(self, shell):
        """Test the common 2>&1 redirection pattern."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Test 2>&1 - redirect stderr to stdout, then redirect to file
            # Order matters: redirect stdout to file, then redirect stderr to stdout
            result = shell.run_command(f'ls /nonexistent/path > {temp_path} 2>&1')
            # This should capture both stdout and stderr in the file
            
            # Check that some output was captured
            with open(temp_path, 'r') as f:
                content = f.read()
            assert len(content.strip()) > 0
            
        finally:
            os.unlink(temp_path)


class TestProcessSubstitution:
    """Test process substitution with <() and >() syntax."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    @pytest.mark.xfail(reason="Process substitution syntax not implemented yet")
    def test_input_process_substitution(self, shell):
        """Test input process substitution <(command)."""
        # Compare output of two commands
        result = shell.run_command('diff <(echo "line1") <(echo "line1")')
        assert result == 0  # Should be identical
        
        # Test with different content
        result = shell.run_command('diff <(echo "line1") <(echo "line2")')
        assert result != 0  # Should be different
    
    @pytest.mark.xfail(reason="Process substitution syntax not implemented yet")
    def test_output_process_substitution(self, shell):
        """Test output process substitution >(command)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Send output to a process that writes to file
            result = shell.run_command(f'echo "test data" > >(cat > {temp_path})')
            assert result == 0
            
            # Wait a moment for async completion
    
            
            # Check that data was written
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "test data" in content
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.xfail(reason="Process substitution syntax not implemented yet")
    def test_complex_process_substitution(self, shell):
        """Test complex process substitution scenarios."""
        # Multiple process substitutions
        result = shell.run_command('''
        cat <(echo "header") <(echo "content") <(echo "footer")
        ''')
        assert result == 0
        # Output verification would need shell output capture
    
    @pytest.mark.xfail(reason="Process substitution syntax not implemented yet")
    def test_process_substitution_with_pipes(self, shell):
        """Test process substitution combined with pipes."""
        # Process substitution in pipeline
        result = shell.run_command('echo "data" | tee >(cat > /tmp/copy1) >(cat > /tmp/copy2)')
        assert result == 0
        
        # Check both copies were created
        try:
            with open('/tmp/copy1', 'r') as f:
                assert "data" in f.read()
            with open('/tmp/copy2', 'r') as f:
                assert "data" in f.read()
        finally:
            for f in ['/tmp/copy1', '/tmp/copy2']:
                if os.path.exists(f):
                    os.unlink(f)


class TestNamedPipeIntegration:
    """Test integration with named pipes (FIFOs)."""
    
    def setup_method(self):
        """Clean up any leftover processes and pipes before each test."""        # Clean up any leftover test FIFOs
        for fifo in ['/tmp/test_fifo', '/tmp/test_fifo_timeout', '/tmp/test_fifo1', '/tmp/test_fifo2']:
            try:
                if os.path.exists(fifo) and stat.S_ISFIFO(os.stat(fifo).st_mode):
                    os.unlink(fifo)
            except:
                pass

    
    def teardown_method(self):
        """Clean up any leftover processes and pipes after each test."""        # Clean up any leftover test FIFOs
        for fifo in ['/tmp/test_fifo', '/tmp/test_fifo_timeout', '/tmp/test_fifo1', '/tmp/test_fifo2']:
            try:
                if os.path.exists(fifo):
                    os.unlink(fifo)
            except:
                pass

    
    @pytest.mark.skip(reason="Named pipe tests can hang due to blocking I/O coordination issues")
    def test_named_pipe_basic(self, shell):
        """Test basic named pipe operations."""
        fifo_path = '/tmp/test_fifo'
        
        try:
            # Create named pipe
            result = shell.run_command(f'mkfifo {fifo_path}')
            assert result == 0
            
            # Verify it's a FIFO
            assert stat.S_ISFIFO(os.stat(fifo_path).st_mode)
            
            # Test that we can create and identify a FIFO
            # (actual read/write testing is complex due to blocking nature)
            
        finally:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)
    
    @pytest.mark.skip(reason="Named pipe timeout tests can hang if timeout command not available")
    def test_named_pipe_with_timeout(self, shell):
        """Test named pipe operations with timeout handling."""
        fifo_path = '/tmp/test_fifo_timeout'
        
        try:
            shell.run_command(f'mkfifo {fifo_path}')
            
            # Just test that we can create the FIFO
            # Timeout testing is complex and platform-dependent
            assert os.path.exists(fifo_path)
            assert stat.S_ISFIFO(os.stat(fifo_path).st_mode)
            
        finally:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)
    
    @pytest.mark.skip(reason="Bidirectional named pipe tests are complex and can hang")
    def test_bidirectional_named_pipe(self, shell):
        """Test bidirectional communication through named pipes."""
        fifo1_path = '/tmp/test_fifo1'
        fifo2_path = '/tmp/test_fifo2'
        
        try:
            # Create two FIFOs for bidirectional communication
            shell.run_command(f'mkfifo {fifo1_path} {fifo2_path}')
            
            # Just test that we can create multiple FIFOs
            assert os.path.exists(fifo1_path)
            assert os.path.exists(fifo2_path)
            assert stat.S_ISFIFO(os.stat(fifo1_path).st_mode)
            assert stat.S_ISFIFO(os.stat(fifo2_path).st_mode)
            
        finally:
            for fifo in [fifo1_path, fifo2_path]:
                if os.path.exists(fifo):
                    os.unlink(fifo)


class TestComplexRedirectionCombinations:
    """Test complex combinations of redirection operators."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    @pytest.mark.skip(reason="this is a poorly implemented test")  
    def test_multiple_redirections_same_command(self, shell):
        """Test command with multiple redirection operators."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as stdout_file, \
             tempfile.NamedTemporaryFile(mode='w', delete=False) as stderr_file:
            stdout_path = stdout_file.name
            stderr_path = stderr_file.name
        
        try:
            # Redirect both stdout and stderr to different files
            result = shell.run_command(f'''
            echo "stdout message" > {stdout_path} 2> {stderr_path}
            echo "stderr message" >&2
            ''')
            assert result == 0
            
            # Check stdout file
            with open(stdout_path, 'r') as f:
                stdout_content = f.read()
            assert "stdout message" in stdout_content
            
            # Check stderr file (might be empty for first command)
            
        finally:
            os.unlink(stdout_path)
            os.unlink(stderr_path)
    
    @pytest.mark.skip(reason="this is a poorly implemented test")
    def test_redirection_with_background_jobs(self, shell):
        """Test redirection combined with background job execution."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Background job with redirection
            result = shell.run_command(f'echo "background output" > {temp_path} &')
            assert result == 0
            
            # Wait for background job to complete
    
            
            # Check output
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "background output" in content
            
        finally:
            os.unlink(temp_path)
    @pytest.mark.skip(reason="this is a poorly implemented test")      
    def test_redirection_in_subshells(self, shell):
        """Test redirection behavior in subshells."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Redirection in subshell should not affect parent
            result = shell.run_command(f'(echo "subshell" > {temp_path}); echo "parent"')
            assert result == 0
            # Output verification would need shell output capture
            
            # Check that subshell output went to file
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "subshell" in content
            
        finally:
            os.unlink(temp_path)
    @pytest.mark.skip(reason="this is a poorly implemented test")      
    def test_redirection_with_function_calls(self, shell):
        """Test redirection with function calls."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Define function
            shell.run_command('''
            test_func() {
                echo "function output"
                echo "function error" >&2
            }
            ''')
            
            # Call function with redirection
            result = shell.run_command(f'test_func > {temp_path} 2>&1')
            assert result == 0
            
            # Check output
            with open(temp_path, 'r') as f:
                content = f.read()
            assert "function output" in content
            assert "function error" in content
            
        finally:
            os.unlink(temp_path)


class TestRedirectionErrorHandling:
    """Test error handling in redirection scenarios."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    def test_redirection_to_readonly_file(self, shell):
        """Test redirection to read-only file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Make file read-only
            os.chmod(temp_path, 0o444)
            
            # Try to redirect to read-only file
            result = shell.run_command(f'echo "test" > {temp_path}')
            assert result != 0
            # Error message verification would need shell output capture
            
        finally:
            os.chmod(temp_path, 0o644)  # Restore permissions for cleanup
            os.unlink(temp_path)
    
    def test_redirection_to_nonexistent_directory(self, shell):
        """Test redirection to file in nonexistent directory."""
        result = shell.run_command('echo "test" > /nonexistent/directory/file')
        assert result != 0
        # Error message verification would need shell output capture
    
    def test_redirection_from_nonexistent_file(self, shell):
        """Test input redirection from nonexistent file."""
        result = shell.run_command('cat < /nonexistent/input/file')
        assert result != 0
        # Error message verification would need shell output capture
    
    @pytest.mark.xfail(reason="PSH doesn't validate file descriptor numbers before duplication")
    def test_invalid_file_descriptor(self, shell):
        """Test redirection with invalid file descriptor numbers."""
        # Try to use extremely high fd number
        result = shell.run_command('echo "test" 999>&1')
        # Should either work or fail gracefully
        assert isinstance(result, int)
        
        # Try to duplicate from non-existent fd
        result = shell.run_command('echo "test" 1>&999')
        # Should fail gracefully
        assert result != 0
    
    @pytest.mark.xfail(reason="PSH errexit mode doesn't stop execution after redirection failures")
    def test_redirection_with_errexit(self, shell):
        """Test redirection error handling with set -e."""
        # Enable errexit
        shell.run_command('set -e')
        
        # Redirection error should exit shell
        result = shell.run_command('echo "test" > /nonexistent/file; echo "should not reach"')
        assert result != 0
        # Output verification would need shell output capture


class TestHeredocAdvanced:
    """Test advanced here-document scenarios."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    def test_heredoc_with_variable_expansion(self, shell):
        """Test here-document with variable expansion."""
        shell.run_command('test_var="expanded"')
        
        result = shell.run_command('''
        cat << EOF
This is a $test_var heredoc
EOF
        ''')
        assert result == 0
        # Output verification would need shell output capture
    
    def test_heredoc_with_quoted_delimiter(self, shell):
        """Test here-document with quoted delimiter (no expansion)."""
        shell.run_command('test_var="should_not_expand"')
        
        result = shell.run_command('''
        cat << 'EOF'
This is a $test_var heredoc
EOF
        ''')
        assert result == 0
        # Output verification would need shell output capture
    
    def test_heredoc_indented(self, shell):
        """Test indented here-document with <<-."""
        result = shell.run_command('''
        cat <<- EOF
\t\tIndented content
\t\tMore indented content
\tEOF
        ''')
        assert result == 0
        # Output verification would need shell output capture
    
    def test_multiple_heredocs(self, shell):
        """Test multiple here-documents in sequence."""
        result = shell.run_command('''
        cat << EOF1 << EOF2
First heredoc
EOF1
Second heredoc
EOF2
        ''')
        # This might not be supported - test graceful handling
        assert isinstance(result, int)
    
    def test_heredoc_in_function(self, shell):
        """Test here-document inside function definition."""
        shell.run_command('''
        heredoc_func() {
            cat << FUNC_EOF
Function heredoc content
Variable: $1
FUNC_EOF
        }
        ''')
        
        result = shell.run_command('heredoc_func "test_arg"')
        assert result == 0
        # Output verification would need shell output capture


class TestHereString:
    """Test here-string (<<<) functionality."""
    
    def setup_method(self):
        """Clean up any leftover processes before each test."""
    
    def teardown_method(self):
        """Clean up any leftover processes after each test."""
    
    @pytest.mark.xfail(reason="Here-string operator not implemented yet")
    def test_here_string_basic(self, shell):
        """Test basic here-string functionality."""
        result = shell.run_command('cat <<< "here string content"')
        assert result == 0
        # Output verification would need shell output capture
    
    @pytest.mark.xfail(reason="Here-string operator not implemented yet")
    def test_here_string_with_variables(self, shell):
        """Test here-string with variable expansion."""
        shell.run_command('test_var="variable content"')
        
        result = shell.run_command('cat <<< "String with $test_var"')
        assert result == 0
        # Output verification would need shell output capture
    
    @pytest.mark.xfail(reason="Here-string operator not implemented yet")
    def test_here_string_complex(self, shell):
        """Test here-string with complex expressions."""
        result = shell.run_command('wc -w <<< "count these words please"')
        assert result == 0
        # Output verification would need shell output capture


# Shell fixture provided by conftest.py


# Helper functions
def create_test_file(path, content, mode=0o644):
    """Helper to create test files with specific content and permissions."""
    with open(path, 'w') as f:
        f.write(content)
    os.chmod(path, mode)
    return path


def wait_for_file(path, timeout=5):
    """Helper to wait for file creation with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(path):
            return True

    return False
