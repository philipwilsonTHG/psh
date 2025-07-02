"""Test nested command and process substitution combinations."""
import pytest
from .utils import ShellTestHelper

@pytest.mark.visitor_xfail(reason="Process substitution output capture issues with pytest and forked processes")
class TestNestedSubstitution:
    """Test various combinations of nested command and process substitutions."""
    
    def test_command_sub_with_process_sub_redirect(self, shell):
        """Test command substitution containing process substitution as redirect."""
        # This was the failing case: $(cat < <(echo "test"))
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('echo $(cat < <(echo "test"))')
        assert result['stdout'] == "test\n"
        assert result['exit_code'] == 0
    
    def test_process_sub_with_command_sub(self, shell):
        """Test process substitution containing command substitution."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('cat <(echo $(echo "nested"))')
        assert result['stdout'] == "nested\n"
        assert result['exit_code'] == 0
    
    def test_multiple_nested_command_subs(self, shell):
        """Test multiple levels of command substitution."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('echo $(echo $(echo "deep"))')
        assert result['stdout'] == "deep\n"
        assert result['exit_code'] == 0
    
    def test_process_sub_in_process_sub(self, shell):
        """Test process substitution inside process substitution."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('cat <(cat <(echo "double"))')
        assert result['stdout'] == "double\n"
        assert result['exit_code'] == 0
    
    def test_complex_nesting_with_pipes(self, shell):
        """Test complex nesting with pipes."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('echo $(cat <(echo "hello") | tr a-z A-Z)')
        assert result['stdout'] == "HELLO\n"
        assert result['exit_code'] == 0
    
    def test_command_sub_with_multiple_process_subs(self, shell):
        """Test command substitution with multiple process substitutions."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('echo $(diff <(echo "a") <(echo "b") 2>&1 | head -1)')
        # The exact output depends on diff format, but it should contain something
        assert result['stdout'].strip() != ""
        assert result['exit_code'] == 0
    
    def test_nested_with_variables(self, shell):
        """Test nested substitutions with variable expansion."""
        helper = ShellTestHelper(shell)
        shell.run_command('VAR="test"')
        result = helper.run_and_capture('echo $(cat <(echo "$VAR"))')
        assert result['stdout'] == "test\n"
        assert result['exit_code'] == 0
    
    def test_nested_with_glob_expansion(self, shell):
        """Test nested substitutions with glob expansion."""
        helper = ShellTestHelper(shell)
        # Create test files
        shell.run_command('mkdir -p tmp')
        shell.run_command('echo "content" > tmp/test.txt')
        result = helper.run_and_capture('cd tmp && echo $(cat <(ls *.txt))')
        assert result['stdout'] == "test.txt\n"
        assert result['exit_code'] == 0
        # Cleanup
        shell.run_command('rm -f tmp/test.txt')
    
    def test_nested_error_propagation(self, shell):
        """Test that errors in nested substitutions are handled correctly."""
        helper = ShellTestHelper(shell)
        # Command substitution should capture the error output
        result = helper.run_and_capture('echo "Error: $(cat <(false; echo "failed" >&2) 2>&1)"')
        assert "failed" in result['stdout']
    
    def test_nested_with_heredoc(self, shell):
        """Test nested substitutions with here documents."""
        helper = ShellTestHelper(shell)
        result = helper.run_and_capture('''echo $(cat <(cat << EOF
nested heredoc
EOF
))''')
        assert result['stdout'] == "nested heredoc\n"
        assert result['exit_code'] == 0
    
    def test_absolute_path_in_nested_context(self, shell):
        """Test that absolute paths work in nested contexts."""
        helper = ShellTestHelper(shell)
        # This was also failing with "command not found"
        result = helper.run_and_capture('echo $(/bin/cat < <(echo "test"))')
        assert result['stdout'] == "test\n"
        assert result['exit_code'] == 0
    
    def test_path_inheritance_in_nested_context(self, shell):
        """Test that PATH is correctly inherited in nested contexts."""
        helper = ShellTestHelper(shell)
        # Check that PATH is available
        result = helper.run_and_capture('echo $(cat <(echo $PATH) | head -c 10)')
        assert len(result['stdout'].strip()) >= 10  # Should have at least 10 chars of PATH
        assert result['exit_code'] == 0