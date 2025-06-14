"""Test enhanced declare builtin functionality."""

import pytest
from unittest.mock import patch
import sys
from io import StringIO

from psh.shell import Shell
from psh.core.variables import Variable, VarAttributes, IndexedArray, AssociativeArray
from psh.core.exceptions import ReadonlyVariableError


class TestDeclareEnhanced:
    """Test the enhanced declare builtin with all new features."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        # Respect PSH_USE_VISITOR_EXECUTOR env var
        import os
        use_visitor = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '').lower() in ('1', 'true', 'yes')
        return Shell(use_visitor_executor=use_visitor)
    
    # Test integer attribute (-i)
    
    def test_declare_integer_basic(self, shell):
        """Test declare -i for integer variables."""
        # Declare integer variable with value
        exit_code = shell.run_command("declare -i num=42")
        assert exit_code == 0
        assert shell.state.get_variable("num") == "42"
        
        # Arithmetic evaluation
        exit_code = shell.run_command("declare -i calc='10 + 5'")
        assert exit_code == 0
        assert shell.state.get_variable("calc") == "15"
        
        # Invalid integer defaults to 0
        exit_code = shell.run_command("declare -i invalid=abc")
        assert exit_code == 0
        assert shell.state.get_variable("invalid") == "0"
    
    def test_declare_integer_arithmetic_operations(self, shell):
        """Test integer attribute with various arithmetic operations."""
        # Complex arithmetic
        exit_code = shell.run_command("declare -i result='(10 + 5) * 2'")
        assert exit_code == 0
        assert shell.state.get_variable("result") == "30"
        
        # Variables in arithmetic
        shell.run_command("X=20")
        shell.run_command("Y=5")
        exit_code = shell.run_command("declare -i calc='X / Y'")
        assert exit_code == 0
        assert shell.state.get_variable("calc") == "4"
    
    # Test lowercase attribute (-l)
    
    def test_declare_lowercase_basic(self, shell):
        """Test declare -l for lowercase conversion."""
        # Direct assignment
        exit_code = shell.run_command("declare -l lower=HELLO")
        assert exit_code == 0
        assert shell.state.get_variable("lower") == "hello"
        
        # Mixed case
        exit_code = shell.run_command("declare -l mixed='HeLLo WoRLd'")
        assert exit_code == 0
        assert shell.state.get_variable("mixed") == "hello world"
    
    def test_declare_lowercase_subsequent_assignments(self, shell):
        """Test that lowercase attribute persists for subsequent assignments."""
        # Declare with lowercase attribute
        shell.run_command("declare -l myvar")
        
        # Subsequent assignments should be lowercase
        shell.run_command("myvar=UPPERCASE")
        assert shell.state.get_variable("myvar") == "uppercase"
        
        shell.run_command("myvar='Mixed Case Text'")
        assert shell.state.get_variable("myvar") == "mixed case text"
    
    # Test uppercase attribute (-u)
    
    def test_declare_uppercase_basic(self, shell):
        """Test declare -u for uppercase conversion."""
        # Direct assignment
        exit_code = shell.run_command("declare -u upper=hello")
        assert exit_code == 0
        assert shell.state.get_variable("upper") == "HELLO"
        
        # Mixed case
        exit_code = shell.run_command("declare -u mixed='HeLLo WoRLd'")
        assert exit_code == 0
        assert shell.state.get_variable("mixed") == "HELLO WORLD"
    
    def test_declare_uppercase_subsequent_assignments(self, shell):
        """Test that uppercase attribute persists for subsequent assignments."""
        # Declare with uppercase attribute
        shell.run_command("declare -u myvar")
        
        # Subsequent assignments should be uppercase
        shell.run_command("myvar=lowercase")
        assert shell.state.get_variable("myvar") == "LOWERCASE"
        
        shell.run_command("myvar='Mixed Case Text'")
        assert shell.state.get_variable("myvar") == "MIXED CASE TEXT"
    
    # Test readonly attribute (-r)
    
    def test_declare_readonly_basic(self, shell):
        """Test declare -r for readonly variables."""
        # Declare readonly variable
        exit_code = shell.run_command("declare -r CONST=immutable")
        assert exit_code == 0
        assert shell.state.get_variable("CONST") == "immutable"
        
        # Try to modify readonly variable
        output = []
        errors = []
        with patch('sys.stdout.write') as mock_out:
            with patch('sys.stderr.write') as mock_err:
                mock_out.side_effect = lambda x: output.append(x)
                mock_err.side_effect = lambda x: errors.append(x)
                exit_code = shell.run_command("CONST=changed")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "readonly variable" in error_msg
    
    def test_declare_readonly_unset_fails(self, shell):
        """Test that readonly variables cannot be unset."""
        # Declare readonly variable
        shell.run_command("declare -r READONLY=value")
        
        # Try to unset
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("unset READONLY")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "readonly variable" in error_msg.lower()
    
    # Test export attribute (-x)
    
    def test_declare_export_basic(self, shell):
        """Test declare -x for exporting variables."""
        # Declare and export
        exit_code = shell.run_command("declare -x EXPORTED=value")
        assert exit_code == 0
        assert shell.state.get_variable("EXPORTED") == "value"
        assert shell.state.env.get("EXPORTED") == "value"
        
        # Export existing variable
        shell.run_command("NOTEXPORTED=test")
        assert "NOTEXPORTED" not in shell.state.env
        
        exit_code = shell.run_command("declare -x NOTEXPORTED")
        assert exit_code == 0
        assert shell.state.env.get("NOTEXPORTED") == "test"
    
    # Test indexed arrays (-a)
    
    def test_declare_indexed_array_empty(self, shell):
        """Test declaring empty indexed array."""
        exit_code = shell.run_command("declare -a myarray")
        assert exit_code == 0
        # Empty array should exist but have no elements
        var = shell.state.get_variable("myarray")
        assert var is not None
    
    def test_declare_indexed_array_initialization(self, shell):
        """Test indexed array initialization."""
        # Initialize with values
        exit_code = shell.run_command("declare -a arr=(one two three)")
        assert exit_code == 0
        
        # Check array elements
        shell.run_command("echo ${arr[0]}")  # Should output "one"
        shell.run_command("echo ${arr[1]}")  # Should output "two"
        shell.run_command("echo ${arr[2]}")  # Should output "three"
    
    def test_declare_indexed_array_sparse(self, shell):
        """Test sparse indexed array."""
        # Create sparse array
        shell.run_command("declare -a sparse")
        shell.run_command("sparse[0]=first")
        shell.run_command("sparse[5]=sixth")
        shell.run_command("sparse[10]=eleventh")
        
        # Verify sparse storage
        # Note: Direct array access would need to be implemented in shell
        # For now we just verify the commands execute without error
        assert shell.run_command("echo ${sparse[0]}") == 0
        assert shell.run_command("echo ${sparse[5]}") == 0
        assert shell.run_command("echo ${sparse[10]}") == 0
    
    # Test associative arrays (-A)
    
    def test_declare_associative_array_empty(self, shell):
        """Test declaring empty associative array."""
        exit_code = shell.run_command("declare -A assoc")
        assert exit_code == 0
        # Empty associative array should exist
        var = shell.state.get_variable("assoc")
        assert var is not None
    
    def test_declare_associative_array_initialization(self, shell):
        """Test associative array initialization."""
        # Initialize with key-value pairs
        exit_code = shell.run_command('declare -A map=([key1]=value1 [key2]=value2)')
        assert exit_code == 0
        
        # Verify storage (would need array expansion support in shell)
        assert shell.run_command('echo ${map[key1]}') == 0
        assert shell.run_command('echo ${map[key2]}') == 0
    
    # Test mutually exclusive options
    
    def test_declare_array_types_exclusive(self, shell):
        """Test that -a and -A are mutually exclusive."""
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("declare -a -A invalid")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "cannot use both -a and -A" in error_msg
    
    def test_declare_case_attributes_exclusive(self, shell):
        """Test that -l and -u are effectively exclusive (last wins)."""
        # When both are specified, the last one should win
        shell.run_command("declare -l -u var=hello")
        assert shell.state.get_variable("var") == "HELLO"  # -u was last
        
        shell.run_command("declare -u -l var2=HELLO")
        assert shell.state.get_variable("var2") == "hello"  # -l was last
    
    # Test print functionality (-p)
    
    def test_declare_p_all_variables(self, shell):
        """Test declare -p without arguments lists all variables."""
        # Set up some variables with different attributes
        shell.run_command("declare -i num=42")
        shell.run_command("declare -l lower=HELLO")
        shell.run_command("declare -rx CONST=immutable")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("declare -p")
        
        assert exit_code == 0
        result = ''.join(output)
        
        # Check for expected declarations
        assert 'declare -i num="42"' in result
        assert 'declare -l lower="hello"' in result
        assert 'declare -rx CONST="immutable"' in result
    
    def test_declare_p_specific_variables(self, shell):
        """Test declare -p with specific variable names."""
        # Set up variables
        shell.run_command("declare -u UPPER=test")
        shell.run_command("declare -i COUNT=10")
        shell.run_command("NORMAL=value")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("declare -p UPPER COUNT")
        
        assert exit_code == 0
        result = ''.join(output)
        
        assert 'declare -u UPPER="TEST"' in result
        assert 'declare -i COUNT="10"' in result
        assert 'NORMAL' not in result  # Not requested
    
    def test_declare_p_nonexistent_variable(self, shell):
        """Test declare -p with nonexistent variable."""
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("declare -p NONEXISTENT")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "NONEXISTENT: not found" in error_msg
    
    def test_declare_p_array_output(self, shell):
        """Test declare -p output format for arrays."""
        # Indexed array
        shell.run_command("declare -a idx=(a b c)")
        
        # Associative array
        shell.run_command("declare -A assoc=([x]=1 [y]=2)")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command("declare -p idx assoc")
        
        result = ''.join(output)
        
        # Check array output format
        assert 'declare -a idx=' in result
        assert 'declare -A assoc=' in result
    
    # Test attribute combinations
    
    def test_declare_combined_attributes(self, shell):
        """Test combining multiple attributes."""
        # Integer + export
        exit_code = shell.run_command("declare -ix INTEXP=42")
        assert exit_code == 0
        assert shell.state.get_variable("INTEXP") == "42"
        assert "INTEXP" in shell.state.env
        
        # Lowercase + export + readonly
        exit_code = shell.run_command("declare -lrx CONST=UPPER")
        assert exit_code == 0
        assert shell.state.get_variable("CONST") == "upper"
        assert shell.state.env.get("CONST") == "upper"
        
        # Try to modify
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("CONST=changed")
        assert exit_code == 1
    
    # Test attribute removal with +
    
    def test_declare_remove_export(self, shell):
        """Test removing export attribute with +x."""
        # Export a variable
        shell.run_command("declare -x EXPORTED=value")
        assert "EXPORTED" in shell.state.env
        
        # Remove export attribute
        exit_code = shell.run_command("declare +x EXPORTED")
        assert exit_code == 0
        assert shell.state.get_variable("EXPORTED") == "value"
        assert "EXPORTED" not in shell.state.env
    
    def test_declare_remove_readonly_fails(self, shell):
        """Test that removing readonly attribute fails."""
        # Create readonly variable
        shell.run_command("declare -r READONLY=value")
        
        # Try to remove readonly attribute
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("declare +r READONLY")
        
        # This should fail - can't remove readonly
        assert exit_code == 1
    
    # Test special characters and escaping
    
    @pytest.mark.xfail(reason="Tokenizer bug with dollar signs in strings")
    def test_declare_p_special_characters(self, shell):
        """Test declare -p with special characters in values."""
        # Variables with special characters
        shell.run_command('VAR1="double quotes"')
        shell.run_command("VAR2='single quotes'")
        shell.run_command("VAR3='$dollar sign'")
        shell.run_command('VAR4="`backticks`"')
        shell.run_command('VAR5="\\backslash"')
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            shell.run_command("declare -p VAR1 VAR2 VAR3 VAR4 VAR5")
        
        result = ''.join(output)
        
        # Check proper escaping in output
        assert 'VAR1="\\"double quotes\\""' in result or 'VAR1="double quotes"' in result
        assert 'VAR2="single quotes"' in result
        assert 'VAR3="\\$dollar sign"' in result
        assert 'VAR4="\\`backticks\\`"' in result
        assert 'VAR5="\\\\backslash"' in result
    
    # Test backward compatibility
    
    def test_declare_f_still_works(self, shell):
        """Test that -f flag still works for functions."""
        shell.run_command("myfunc() { echo test; }")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("declare -f myfunc")
        
        assert exit_code == 0
        result = ''.join(output)
        assert "myfunc ()" in result
        assert "echo test" in result
    
    def test_declare_F_still_works(self, shell):
        """Test that -F flag still works for function names."""
        shell.run_command("func1() { echo 1; }")
        shell.run_command("func2() { echo 2; }")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("declare -F")
        
        assert exit_code == 0
        result = ''.join(output)
        assert "declare -f func1" in result
        assert "declare -f func2" in result
    
    # Test invalid option handling
    
    def test_declare_invalid_option(self, shell):
        """Test that invalid options are rejected."""
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("declare -q VAR")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "invalid option: -q" in error_msg
    
    def test_declare_invalid_plus_option(self, shell):
        """Test that invalid + options are rejected."""
        errors = []
        with patch('sys.stderr.write') as mock_err:
            mock_err.side_effect = lambda x: errors.append(x)
            exit_code = shell.run_command("declare +q VAR")
        
        assert exit_code == 1
        error_msg = ''.join(errors)
        assert "invalid option: +q" in error_msg
    
    # Test edge cases
    
    def test_declare_no_arguments_lists_all(self, shell):
        """Test that declare with no arguments lists all variables."""
        # Set some variables
        shell.run_command("VAR1=value1")
        shell.run_command("declare -i NUM=42")
        shell.run_command("declare -l LOWER=TEST")
        
        output = []
        with patch('sys.stdout.write') as mock_out:
            mock_out.side_effect = lambda x: output.append(x)
            exit_code = shell.run_command("declare")
        
        assert exit_code == 0
        result = ''.join(output)
        
        # Should show all variables with their values
        assert "VAR1=value1" in result
        assert "NUM=42" in result
        assert "LOWER=test" in result
    
    def test_declare_attribute_without_value(self, shell):
        """Test declaring attributes without assigning values."""
        # Declare with attributes but no value
        shell.run_command("declare -i intvar")
        shell.run_command("declare -u uppervar")
        shell.run_command("declare -l lowervar")
        
        # Variables should exist with empty/zero values
        assert shell.state.get_variable("intvar") is not None
        assert shell.state.get_variable("uppervar") is not None
        assert shell.state.get_variable("lowervar") is not None
        
        # Assign values and check transformations
        shell.run_command("intvar='5 + 3'")
        assert shell.state.get_variable("intvar") == "8"
        
        shell.run_command("uppervar=hello")
        assert shell.state.get_variable("uppervar") == "HELLO"
        
        shell.run_command("lowervar=WORLD")
        assert shell.state.get_variable("lowervar") == "world"
    
    def test_declare_existing_variable_add_attributes(self, shell):
        """Test adding attributes to existing variables."""
        # Create a regular variable
        shell.run_command("VAR=hello")
        assert shell.state.get_variable("VAR") == "hello"
        
        # Add uppercase attribute
        shell.run_command("declare -u VAR")
        # Existing value should be transformed
        assert shell.state.get_variable("VAR") == "HELLO"
        
        # Future assignments should also be uppercase
        shell.run_command("VAR=world")
        assert shell.state.get_variable("VAR") == "WORLD"
    
    def test_declare_options_parsing(self, shell):
        """Test various option parsing scenarios."""
        # Combined short options
        exit_code = shell.run_command("declare -ixr NUM=42")
        assert exit_code == 0
        
        # Options with --
        exit_code = shell.run_command("declare -l -- -weirdname=value")
        assert exit_code == 0
        assert shell.state.get_variable("-weirdname") == "value"
        
        # Mixed + and - options
        shell.run_command("declare -x VAR=test")
        assert "VAR" in shell.state.env
        
        shell.run_command("declare +x -u VAR")
        assert "VAR" not in shell.state.env
        assert shell.state.get_variable("VAR") == "TEST"