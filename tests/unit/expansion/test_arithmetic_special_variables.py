"""Test arithmetic expansion with special variables and parameters.

This module tests the parser combinator's ability to handle special shell variables
in arithmetic expansion, including positional parameters, special parameters, and arrays.

Part of Phase 2 of the arithmetic expansion testing plan.
"""
import pytest


class TestArithmeticSpecialVariables:
    """Test arithmetic expansion with special variables and parameters."""
    
    # Positional parameter tests ($1, $2, etc.)
    
    def test_positional_parameters_basic(self, shell, capsys):
        """Test arithmetic with basic positional parameters."""
        # Set positional parameters
        shell.run_command('set -- 10 20 30')
        
        # Test $1 + $2
        result = shell.run_command('echo $(($1 + $2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "30"
    
    def test_positional_parameters_multiplication(self, shell, capsys):
        """Test multiplication with positional parameters."""
        shell.run_command('set -- 5 7')
        
        # Test $1 * $2
        result = shell.run_command('echo $(($1 * $2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "35"
    
    def test_positional_parameters_complex(self, shell, capsys):
        """Test complex expression with positional parameters."""
        shell.run_command('set -- 3 4 5')
        
        # Test ($1 + $2) * $3
        result = shell.run_command('echo $((($1 + $2) * $3))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "35"  # (3 + 4) * 5 = 35
    
    def test_positional_parameters_beyond_9(self, shell, capsys):
        """Test positional parameters beyond $9."""
        shell.run_command('set -- 1 2 3 4 5 6 7 8 9 10 11 12')
        
        # Test ${10} + ${11}
        result = shell.run_command('echo $((${10} + ${11}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "21"  # 10 + 11 = 21
    
    def test_positional_parameters_zero_means_script_name(self, shell, capsys):
        """Test that $0 in arithmetic context behaves appropriately."""
        # $0 should be the script name, which in arithmetic should be 0
        # unless it's a number
        result = shell.run_command('echo $(($0 + 5))')
        assert result == 0
        captured = capsys.readouterr()
        # $0 might be 0 or the script name treated as 0
        output = captured.out.strip()
        assert output.isdigit()  # Should be a number
    
    def test_undefined_positional_parameters(self, shell, capsys):
        """Test undefined positional parameters in arithmetic."""
        # Clear positional parameters
        shell.run_command('set --')
        
        # Undefined parameters should evaluate to 0 in arithmetic
        result = shell.run_command('echo $(($1 + 5))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"  # 0 + 5 = 5
    
    # Special parameter tests ($#, $?, $$, etc.)
    
    def test_argument_count_parameter(self, shell, capsys):
        """Test $# (argument count) in arithmetic."""
        shell.run_command('set -- a b c d')
        
        # Test $# * 10
        result = shell.run_command('echo $(($# * 10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "40"  # 4 * 10 = 40
    
    def test_argument_count_empty(self, shell, capsys):
        """Test $# when no arguments are set."""
        shell.run_command('set --')
        
        result = shell.run_command('echo $(($# + 1))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "1"  # 0 + 1 = 1
    
    def test_exit_status_parameter(self, shell, capsys):
        """Test $? (exit status) in arithmetic."""
        # Run a command that succeeds
        shell.run_command('true')
        
        result = shell.run_command('echo $(($? + 5))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"  # 0 + 5 = 5
    
    def test_exit_status_parameter_failure(self, shell, capsys):
        """Test $? after a failed command."""
        # Run a command that fails
        shell.run_command('false')
        
        result = shell.run_command('echo $(($? + 5))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "6"  # 1 + 5 = 6
    
    def test_process_id_parameter(self, shell, capsys):
        """Test $$ (process ID) in arithmetic."""
        # $$ should be a positive number
        result = shell.run_command('echo $(($$))')
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output.isdigit()
        assert int(output) > 0
    
    def test_process_id_in_calculation(self, shell, capsys):
        """Test $$ in a calculation."""
        # $$ % 2 should be 0 or 1
        result = shell.run_command('echo $(($$ % 2))')
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert output in ["0", "1"]
    
    def test_last_background_pid_parameter(self, shell, capsys):
        """Test $! (last background PID) in arithmetic."""
        # Start a background job
        shell.run_command('sleep 0.1 &')
        # Clear any job control output
        capsys.readouterr()
        
        # $! should be a positive number
        result = shell.run_command('echo $(($!))')
        assert result == 0
        captured = capsys.readouterr()
        output = captured.out.strip()
        # Might be 0 if no background job or the actual PID
        assert output.isdigit()
    
    def test_special_parameters_combination(self, shell, capsys):
        """Test combination of special parameters."""
        shell.run_command('set -- 1 2 3')
        shell.run_command('true')  # Set exit status to 0
        
        # Test $# + $?
        result = shell.run_command('echo $(($# + $?))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "3"  # 3 + 0 = 3
    
    # Array arithmetic tests
    
    def test_array_element_arithmetic(self, shell, capsys):
        """Test arithmetic with array elements."""
        shell.run_command('arr=(5 10 15 20)')
        
        # Test ${arr[0]} + ${arr[1]}
        result = shell.run_command('echo $((${arr[0]} + ${arr[1]}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "15"  # 5 + 10 = 15
    
    def test_array_element_multiplication(self, shell, capsys):
        """Test multiplication with array elements."""
        shell.run_command('arr=(3 4 5)')
        
        # Test ${arr[1]} * ${arr[2]}
        result = shell.run_command('echo $((${arr[1]} * ${arr[2]}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "20"  # 4 * 5 = 20
    
    def test_array_indices_from_arithmetic(self, shell, capsys):
        """Test using arithmetic results as array indices (corrected)."""
        shell.run_command('arr=(10 20 30 40 50)')
        shell.run_command('i=2')
        
        # Test ${arr[$((i-1))]} + ${arr[$((i+1))]}
        result = shell.run_command('echo $((${arr[$((i-1))]} + ${arr[$((i+1))]}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "60"  # arr[1] + arr[3] = 20 + 40 = 60
    
    def test_array_length_parameter(self, shell, capsys):
        """Test ${#array[@]} in arithmetic."""
        shell.run_command('arr=(a b c d e)')
        
        # Test ${#arr[@]} * 2
        result = shell.run_command('echo $((${#arr[@]} * 2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"  # 5 * 2 = 10
    
    def test_array_length_all_elements(self, shell, capsys):
        """Test ${#array[*]} syntax."""
        shell.run_command('arr=(x y z)')
        
        # Test ${#arr[*]} + 1
        result = shell.run_command('echo $((${#arr[*]} + 1))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "4"  # 3 + 1 = 4
    
    def test_sparse_array_arithmetic(self, shell, capsys):
        """Test arithmetic with sparse arrays."""
        shell.run_command('arr[0]=10')
        shell.run_command('arr[5]=50')
        shell.run_command('arr[10]=100')
        
        # Test ${arr[0]} + ${arr[5]} + ${arr[10]}
        result = shell.run_command('echo $((${arr[0]} + ${arr[5]} + ${arr[10]}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "160"  # 10 + 50 + 100 = 160
    
    def test_undefined_array_elements(self, shell, capsys):
        """Test undefined array elements in arithmetic."""
        shell.run_command('arr=(1 2 3)')
        
        # Test ${arr[10]} + 5 (undefined element)
        result = shell.run_command('echo $((${arr[10]} + 5))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"  # 0 + 5 = 5 (undefined elements are 0)
    
    # Variable integration tests
    
    def test_regular_variables_in_arithmetic(self, shell, capsys):
        """Test regular variables in arithmetic expansion."""
        shell.run_command('x=15')
        shell.run_command('y=25')
        
        # Test $x + $y
        result = shell.run_command('echo $(($x + $y))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "40"  # 15 + 25 = 40
    
    def test_variable_without_dollar_sign(self, shell, capsys):
        """Test variables without $ in arithmetic context."""
        shell.run_command('num=42')
        
        # Test num * 2 (without $)
        result = shell.run_command('echo $((num * 2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "84"  # 42 * 2 = 84
    
    def test_mixed_variable_and_parameter_syntax(self, shell, capsys):
        """Test mixing variable and parameter syntax."""
        shell.run_command('x=10')
        shell.run_command('set -- 5')
        
        # Test $x + $1 + x
        result = shell.run_command('echo $(($x + $1 + x))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "25"  # 10 + 5 + 10 = 25
    
    def test_string_variables_as_zero(self, shell, capsys):
        """Test string variables evaluate to 0 in arithmetic."""
        shell.run_command('str="hello"')
        
        # String should evaluate to 0
        result = shell.run_command('echo $(($str + 10))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "10"  # 0 + 10 = 10
    
    def test_numeric_string_variables(self, shell, capsys):
        """Test numeric string variables."""
        shell.run_command('num_str="123"')
        
        # Numeric string should evaluate to its numeric value
        result = shell.run_command('echo $(($num_str + 7))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "130"  # 123 + 7 = 130
    
    def test_empty_variables(self, shell, capsys):
        """Test empty variables in arithmetic."""
        shell.run_command('empty=""')
        
        # Empty variables should evaluate to 0
        result = shell.run_command('echo $(($empty + 15))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "15"  # 0 + 15 = 15
    
    def test_unset_variables(self, shell, capsys):
        """Test unset variables in arithmetic."""
        shell.run_command('unset undefined_var 2>/dev/null || true')
        
        # Unset variables should evaluate to 0
        result = shell.run_command('echo $(($undefined_var + 8))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "8"  # 0 + 8 = 8
    
    # Complex integration tests
    
    def test_nested_arithmetic_with_variables(self, shell, capsys):
        """Test nested arithmetic with various variable types."""
        shell.run_command('x=5')
        shell.run_command('set -- 3 7')
        shell.run_command('arr=(2 4 6)')
        
        # Complex expression: x * ($1 + $2) + ${arr[1]}
        result = shell.run_command('echo $((x * ($1 + $2) + ${arr[1]}))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "54"  # 5 * (3 + 7) + 4 = 5 * 10 + 4 = 54
    
    def test_all_special_parameters_together(self, shell, capsys):
        """Test multiple special parameters in one expression."""
        shell.run_command('set -- 1 2')
        shell.run_command('true')  # Set $? = 0
        
        # Test $# + $? + $1 + $2
        result = shell.run_command('echo $(($# + $? + $1 + $2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "5"  # 2 + 0 + 1 + 2 = 5
    
    def test_arithmetic_assignment_with_special_vars(self, shell, capsys):
        """Test arithmetic assignment using special variables."""
        shell.run_command('set -- 10 20')
        
        # Test result = $1 + $2
        result = shell.run_command('echo $((result = $1 + $2))')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "30"
        
        # Verify the variable was set
        result = shell.run_command('echo $result')
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "30"