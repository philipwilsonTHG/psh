"""Test eval builtin functionality."""
import pytest
import sys
from psh.shell import Shell


class TestEval:
    """Test suite for eval builtin."""
    
    def test_eval_basic(self, shell):
        """Test basic eval functionality."""
        # Simple echo
        assert shell.run_command('eval "echo hello"') == 0
        assert shell.run_command('eval echo world') == 0
        
        # Multiple arguments concatenated
        assert shell.run_command('eval echo "arg1" "arg2" "arg3"') == 0
    
    def test_eval_empty(self, shell):
        """Test eval with empty arguments."""
        # Empty eval returns 0
        assert shell.run_command('eval') == 0
        assert shell.run_command('eval ""') == 0
        assert shell.run_command('eval "   "') == 0
    
    def test_eval_variable_assignment(self, shell):
        """Test variable assignment in eval."""
        # Simple assignment
        shell.run_command('eval "x=10"')
        assert shell.state.get_variable('x') == '10'
        
        # Assignment with spaces
        shell.run_command('eval "y=\\"test value\\""')
        assert shell.state.get_variable('y') == 'test value'
        
        # Multiple assignments
        shell.run_command('eval "a=1; b=2"')
        assert shell.state.get_variable('a') == '1'
        assert shell.state.get_variable('b') == '2'
    
    def test_eval_variable_expansion(self, shell):
        """Test variable expansion in eval."""
        # Set a variable
        shell.run_command('var="echo expanded"')
        
        # Eval with variable
        assert shell.run_command('eval $var') == 0
        assert shell.run_command('eval "$var with more"') == 0
    
    def test_eval_multiple_commands(self, shell, capsys):
        """Test multiple commands in eval."""
        shell.run_command('eval "echo first; echo second"')
        captured = capsys.readouterr()
        assert "first\n" in captured.out
        assert "second\n" in captured.out
    
    def test_eval_exit_status(self, shell):
        """Test eval exit status."""
        # Successful command
        assert shell.run_command('eval "true"') == 0
        
        # Failed command
        assert shell.run_command('eval "false"') == 1
        
        # Last command determines exit status
        assert shell.run_command('eval "false; true"') == 0
        assert shell.run_command('eval "true; false"') == 1
        
        # Test with command that sets exit code without using exit builtin
        assert shell.run_command('eval "sh -c \\"exit 5\\""') == 5
    
    def test_eval_command_substitution(self, shell):
        """Test command substitution in eval."""
        # Basic command substitution
        shell.run_command('eval "x=$(echo 42)"')
        assert shell.state.get_variable('x') == '42'
        
        # Command substitution in echo
        shell.run_command('eval "echo Today is $(date +%A 2>/dev/null)"')
        assert shell.last_exit_code == 0
    
    def test_eval_function_definition(self, shell, capsys):
        """Test function definition in eval."""
        # Define function in eval
        shell.run_command('eval "greet() { echo Hello \\$1; }"')
        
        # Function should be available
        shell.run_command('greet World')
        captured = capsys.readouterr()
        assert "Hello World\n" in captured.out
    
    def test_eval_control_structures(self, shell, capsys):
        """Test control structures in eval."""
        # If statement
        shell.run_command('eval "if [ 1 -eq 1 ]; then echo True; fi"')
        captured = capsys.readouterr()
        assert "True\n" in captured.out
        
        # For loop
        shell.run_command('eval "for i in 1 2 3; do echo Number: \\$i; done"')
        captured = capsys.readouterr()
        assert "Number: 1\n" in captured.out
        assert "Number: 2\n" in captured.out
        assert "Number: 3\n" in captured.out
    
    def test_eval_pipeline(self, shell):
        """Test pipelines in eval."""
        # Just test that pipeline syntax works - exit code indicates success
        assert shell.run_command('eval "echo test | cat"') == 0
        assert shell.run_command('eval "echo line2 | grep line2"') == 0
        assert shell.run_command('eval "echo line1 | grep line2"') == 1  # No match
    
    def test_eval_redirection(self, shell):
        """Test I/O redirection in eval."""
        import tempfile
        import os
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            # Redirect output to file
            shell.run_command(f'eval "echo redirected > {temp_file}"')
            
            # Read back
            with open(temp_file, 'r') as f:
                content = f.read()
            assert content.strip() == "redirected"
        finally:
            os.unlink(temp_file)
    
    def test_eval_nested(self, shell, capsys):
        """Test nested eval."""
        # Simple nested eval
        shell.run_command('eval "eval \\"echo nested\\""')
        captured = capsys.readouterr()
        assert "nested\n" in captured.out
        
        # Double nested using single quotes to avoid complex escaping
        shell.run_command("eval 'eval \"eval \\\"echo double\\\"\"'")
        captured = capsys.readouterr() 
        assert "double\n" in captured.out
    
    def test_eval_quotes_and_escapes(self, shell, capsys):
        """Test quote and escape handling in eval."""
        # Single quotes in eval
        shell.run_command("eval 'echo \"double quotes\"'")
        captured = capsys.readouterr()
        assert "double quotes\n" in captured.out
        
        # Double quotes in eval
        shell.run_command('eval "echo \'single quotes\'"')
        captured = capsys.readouterr()
        assert "single quotes\n" in captured.out
        
        # Variable in double quotes
        shell.run_command('USER=testuser')
        shell.run_command('eval "echo \\"User: $USER\\""')
        captured = capsys.readouterr()
        assert "User: testuser\n" in captured.out
    
    def test_eval_syntax_error(self, shell, capsys):
        """Test eval with syntax errors."""
        # Invalid syntax - missing condition  
        result = shell.run_command('eval "if ; then echo bad; fi"')
        assert result != 0
        
        # Bad command 
        result = shell.run_command('eval "nosuchcommand"')
        assert result == 127  # Command not found
        
        # Unmatched parenthesis
        result = shell.run_command('eval "( echo unclosed"')
        assert result != 0
    
    def test_eval_with_aliases(self, shell, capsys):
        """Test alias expansion in eval."""
        # Define an alias
        shell.run_command('alias ll="ls -l"')
        
        # Eval should expand aliases
        shell.run_command('eval "ll /dev/null 2>/dev/null"')
        # Just check it doesn't fail - output varies by system
        assert shell.last_exit_code == 0
    
    def test_eval_preserves_context(self, shell):
        """Test that eval preserves shell context."""
        # Set variable before eval
        shell.run_command('before=yes')
        
        # Eval modifies and adds variables
        shell.run_command('eval "before=no; during=eval"')
        
        # Check both are preserved
        assert shell.state.get_variable('before') == 'no'
        assert shell.state.get_variable('during') == 'eval'
    
    def test_eval_special_variables(self, shell):
        """Test special variables in eval."""
        # $? should work
        shell.run_command('false')
        shell.run_command('eval "echo Exit: $?"')
        assert shell.last_exit_code == 0
        
        # $$ should work
        shell.run_command('eval "echo PID: $$"')
        assert shell.last_exit_code == 0
        
        # $# with positional parameters
        shell.run_command('set -- a b c')
        shell.run_command('eval "echo Count: $#"')
        assert shell.last_exit_code == 0