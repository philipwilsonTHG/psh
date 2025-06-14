"""Test typeset builtin functionality."""

import pytest
from unittest.mock import patch
from psh.shell import Shell
from psh.ast_nodes import FunctionDef


class TestTypesetBuiltin:
    """Test the typeset builtin command."""
    
    def test_typeset_without_args_lists_variables(self, shell):
        """Test that typeset without arguments lists all variables."""
        # Set some variables
        shell.run_command("VAR1=value1")
        shell.run_command("VAR2=value2")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            shell.run_command("typeset")
        
        result = ''.join(output)
        assert "VAR1=value1" in result
        assert "VAR2=value2" in result
    
    def test_typeset_f_lists_all_functions(self, shell):
        """Test that typeset -f lists all function definitions."""
        # Define some functions
        shell.run_command("func1() { echo hello; }")
        shell.run_command("func2() { echo world; return 42; }")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -f")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "func1 ()" in result
        assert "echo hello" in result
        assert "func2 ()" in result
        assert "echo world" in result
        assert "return 42" in result
    
    def test_typeset_F_lists_function_names_only(self, shell):
        """Test that typeset -F lists only function names."""
        # Define some functions
        shell.run_command("func1() { echo hello; }")
        shell.run_command("func2() { echo world; }")
        shell.run_command("func3() { echo test; }")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -F")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "declare -f func1\n" in result
        assert "declare -f func2\n" in result
        assert "declare -f func3\n" in result
        # Should not contain function bodies
        assert "echo" not in result
        assert "{" not in result
    
    def test_typeset_f_specific_function(self, shell):
        """Test that typeset -f funcname shows specific function."""
        # Define a function
        shell.run_command("myfunc() { echo 'Hello World'; return 0; }")
        
        # Capture output for existing function
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -f myfunc")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "myfunc ()" in result
        assert "echo 'Hello World'" in result
        assert "return 0" in result
    
    def test_typeset_f_nonexistent_function(self, shell):
        """Test that typeset -f nonexistent returns error."""
        # Capture error output
        output = []
        errors = []
        with patch('sys.stdout.write') as mock_write:
            with patch('sys.stderr.write') as mock_err:
                mock_write.side_effect = lambda x: output.append(x)
                mock_err.side_effect = lambda x: errors.append(x)
                exit_code = shell.run_command("typeset -f nonexistent")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "nonexistent: not found" in error_msg
    
    def test_typeset_F_specific_function(self, shell):
        """Test that typeset -F funcname shows specific function name."""
        # Define a function
        shell.run_command("myfunc() { echo test; }")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -F myfunc")
        
        result = ''.join(output)
        assert exit_code == 0
        assert result.strip() == "declare -f myfunc"
    
    def test_typeset_F_multiple_functions(self, shell):
        """Test that typeset -F can list multiple specific functions."""
        # Define functions
        shell.run_command("func1() { echo 1; }")
        shell.run_command("func2() { echo 2; }")
        shell.run_command("func3() { echo 3; }")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -F func1 func3")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "declare -f func1\n" in result
        assert "declare -f func3\n" in result
        assert "func2" not in result
    
    def test_typeset_f_with_complex_function(self, shell):
        """Test typeset -f with a complex function definition."""
        # Define a complex function
        shell.run_command("""
        complex_func() {
            local var="test"
            if [ "$1" = "hello" ]; then
                echo "Hello, $2!"
            else
                echo "Goodbye!"
            fi
            for i in 1 2 3; do
                echo "Number: $i"
            done
            return 0
        }
        """)
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -f complex_func")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "complex_func ()" in result
        # Check for local declaration (quotes may or may not be preserved)
        assert "local var" in result and ("test" in result or "'test'" in result or '"test"' in result)
        assert "if [" in result or "if     [" in result  # Allow for varying spacing
        assert "for i in 1 2 3" in result
    
    def test_typeset_and_declare_are_identical(self, shell):
        """Test that typeset and declare produce identical output."""
        # Define a function
        shell.run_command("testfunc() { echo 'Testing'; }")
        
        # Get typeset output
        typeset_output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: typeset_output.append(x)
            shell.run_command("typeset -f testfunc")
        
        # Get declare output
        declare_output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: declare_output.append(x)
            shell.run_command("declare -f testfunc")
        
        # They should be identical
        assert ''.join(typeset_output) == ''.join(declare_output)
    
    def test_typeset_F_and_declare_F_are_identical(self, shell):
        """Test that typeset -F and declare -F produce identical output."""
        # Define functions
        shell.run_command("func1() { echo 1; }")
        shell.run_command("func2() { echo 2; }")
        
        # Get typeset -F output
        typeset_output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: typeset_output.append(x)
            shell.run_command("typeset -F")
        
        # Get declare -F output
        declare_output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: declare_output.append(x)
            shell.run_command("declare -F")
        
        # They should be identical
        assert ''.join(typeset_output) == ''.join(declare_output)
    
    def test_typeset_f_empty_function(self, shell):
        """Test typeset -f with an empty function."""
        # Define an empty function
        shell.run_command("empty_func() { :; }")
        
        # Capture output
        output = []
        with patch('sys.stdout.write') as mock_write:
            mock_write.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("typeset -f empty_func")
        
        result = ''.join(output)
        assert exit_code == 0
        assert "empty_func ()" in result
        assert ":" in result  # The colon command
    
    def test_typeset_help(self, shell):
        """Test typeset help message."""
        # PSH doesn't have a help builtin yet, but the builtin has a help property
        from psh.builtins.function_support import TypesetBuiltin
        builtin = TypesetBuiltin()
        help_text = builtin.help
        
        assert "typeset:" in help_text
        assert "alias for declare" in help_text
        assert "Korn shell" in help_text


@pytest.fixture
def shell():
    """Create a shell instance for testing."""
    # Respect PSH_USE_VISITOR_EXECUTOR env var
    import os
    use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
    return Shell(use_visitor_executor=use_visitor)