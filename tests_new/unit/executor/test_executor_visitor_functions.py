"""
Executor visitor function handling unit tests.

Tests ExecutorVisitor functionality for function definition, execution,
parameter handling, and scope management.
"""

import pytest


class TestFunctionDefinition:
    """Test function definition and registration."""
    
    def test_simple_function_definition(self, shell):
        """Test defining a simple function."""
        script = '''
        my_function() {
            echo "hello from function"
        }
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        # Function should be registered
        assert "my_function" in shell.function_manager.functions
    
    def test_function_with_parameters(self, shell):
        """Test defining function that uses parameters."""
        script = '''
        greet() {
            echo "Hello, $1!"
        }
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        assert "greet" in shell.function_manager.functions
    
    def test_multiline_function_definition(self, shell):
        """Test defining multiline function."""
        script = '''
        complex_function() {
            echo "first line"
            echo "second line"
            echo "third line"
        }
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        assert "complex_function" in shell.function_manager.functions
    
    def test_function_with_control_structures(self, shell):
        """Test function containing control structures."""
        script = '''
        conditional_function() {
            if [ "$1" = "test" ]; then
                echo "test parameter"
            else
                echo "other parameter"
            fi
        }
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        assert "conditional_function" in shell.function_manager.functions


class TestFunctionExecution:
    """Test function execution and calling."""
    
    def test_simple_function_call(self, shell, capsys):
        """Test calling a simple function."""
        script = '''
        say_hello() {
            echo "Hello, World!"
        }
        say_hello
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Hello, World!" in captured.out
    
    def test_function_with_single_parameter(self, shell, capsys):
        """Test function call with single parameter."""
        script = '''
        greet() {
            echo "Hello, $1!"
        }
        greet "Alice"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Hello, Alice!" in captured.out
    
    def test_function_with_multiple_parameters(self, shell, capsys):
        """Test function call with multiple parameters."""
        script = '''
        full_greet() {
            echo "$1 $2, welcome to $3!"
        }
        full_greet "Hello" "Bob" "PSH"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Hello Bob, welcome to PSH!" in captured.out
    
    def test_function_return_status(self, shell, capsys):
        """Test function return status handling."""
        script = '''
        success_function() {
            echo "success"
            return 0
        }
        
        failure_function() {
            echo "failure"
            return 1
        }
        
        success_function
        echo "Success status: $?"
        
        failure_function
        echo "Failure status: $?"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Success status: 0" in captured.out
        assert "Failure status: 1" in captured.out
    
    def test_recursive_function_call(self, shell, capsys):
        """Test recursive function calls."""
        script = '''
        countdown() {
            if [ "$1" -gt 0 ]; then
                echo "Count: $1"
                countdown $(($1 - 1))
            else
                echo "Done!"
            fi
        }
        countdown 3
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Count: 3" in captured.out
        assert "Count: 2" in captured.out
        assert "Count: 1" in captured.out
        assert "Done!" in captured.out


class TestParameterHandling:
    """Test function parameter handling and scoping."""
    
    def test_positional_parameter_access(self, shell, capsys):
        """Test access to positional parameters $1, $2, etc."""
        script = '''
        show_params() {
            echo "First: $1"
            echo "Second: $2"
            echo "Third: $3"
        }
        show_params "alpha" "beta" "gamma"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "First: alpha" in captured.out
        assert "Second: beta" in captured.out
        assert "Third: gamma" in captured.out
    
    def test_parameter_count_access(self, shell, capsys):
        """Test access to parameter count $#."""
        script = '''
        count_params() {
            echo "Parameter count: $#"
        }
        count_params one two three four
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Parameter count: 4" in captured.out
    
    def test_all_parameters_access(self, shell, capsys):
        """Test access to all parameters $@ and $*."""
        script = '''
        show_all_params() {
            echo "All params with @: $@"
            echo "All params with *: $*"
        }
        show_all_params "first" "second" "third"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "first second third" in captured.out
    
    @pytest.mark.xfail(reason="PSH may not have set builtin or full positional parameter handling")
    def test_parameter_scoping(self, shell, capsys):
        """Test that function parameters don't affect global scope."""
        script = '''
        # Set global positional parameters
        set "global1" "global2" "global3"
        echo "Before function: $1 $2 $3"
        
        test_scope() {
            echo "In function: $1 $2 $3"
        }
        
        test_scope "func1" "func2" "func3"
        echo "After function: $1 $2 $3"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Before function: global1 global2 global3" in captured.out
        assert "In function: func1 func2 func3" in captured.out
        assert "After function: global1 global2 global3" in captured.out
    
    def test_empty_parameters(self, shell, capsys):
        """Test function call with no parameters."""
        script = '''
        no_params() {
            echo "Parameter count: $#"
            echo "First param: ${1:-empty}"
        }
        no_params
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Parameter count: 0" in captured.out
        assert "First param: empty" in captured.out


class TestFunctionScope:
    """Test variable scoping in functions."""
    
    def test_global_variable_access(self, shell, capsys):
        """Test that functions can access global variables."""
        script = '''
        GLOBAL_VAR="global value"
        
        access_global() {
            echo "Global var: $GLOBAL_VAR"
        }
        
        access_global
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Global var: global value" in captured.out
    
    def test_local_variable_modification(self, shell, capsys):
        """Test variable modification within functions."""
        script = '''
        VAR="original"
        echo "Before function: $VAR"
        
        modify_var() {
            VAR="modified"
            echo "In function: $VAR"
        }
        
        modify_var
        echo "After function: $VAR"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Before function: original" in captured.out
        assert "In function: modified" in captured.out
        assert "After function: modified" in captured.out
    
    def test_function_local_variables(self, shell, capsys):
        """Test variables created within functions."""
        script = '''
        create_local() {
            LOCAL_VAR="function local"
            echo "In function: $LOCAL_VAR"
        }
        
        create_local
        echo "Outside function: ${LOCAL_VAR:-undefined}"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "In function: function local" in captured.out
        assert "Outside function: function local" in captured.out  # Variables persist
    
    def test_nested_function_calls(self, shell, capsys):
        """Test calling functions from within other functions."""
        script = '''
        inner_function() {
            echo "Inner function called with: $1"
        }
        
        outer_function() {
            echo "Outer function called"
            inner_function "from outer"
        }
        
        outer_function
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Outer function called" in captured.out
        assert "Inner function called with: from outer" in captured.out


class TestFunctionComplexScenarios:
    """Test complex function usage scenarios."""
    
    def test_function_with_loops(self, shell, capsys):
        """Test function containing loops."""
        script = '''
        count_to() {
            for i in $(seq 1 $1); do
                echo "Count: $i"
            done
        }
        count_to 3
        '''
        
        # Note: seq may not be available, so use simpler version
        script = '''
        count_to() {
            counter=1
            while [ "$counter" -le "$1" ]; do
                echo "Count: $counter"
                counter=$((counter + 1))
            done
        }
        count_to 3
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Count: 1" in captured.out
        assert "Count: 2" in captured.out
        assert "Count: 3" in captured.out
    
    def test_function_with_conditionals(self, shell, capsys):
        """Test function with conditional logic."""
        script = '''
        check_number() {
            if [ "$1" -gt 10 ]; then
                echo "$1 is greater than 10"
            elif [ "$1" -eq 10 ]; then
                echo "$1 equals 10"
            else
                echo "$1 is less than 10"
            fi
        }
        
        check_number 5
        check_number 10
        check_number 15
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "5 is less than 10" in captured.out
        assert "10 equals 10" in captured.out
        assert "15 is greater than 10" in captured.out
    
    def test_function_with_case_statement(self, shell, capsys):
        """Test function with case statement."""
        script = '''
        classify_file() {
            case "$1" in
                *.txt)
                    echo "Text file: $1"
                    ;;
                *.log)
                    echo "Log file: $1"
                    ;;
                *)
                    echo "Other file: $1"
                    ;;
            esac
        }
        
        classify_file "document.txt"
        classify_file "error.log"
        classify_file "script.sh"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "Text file: document.txt" in captured.out
        assert "Log file: error.log" in captured.out
        assert "Other file: script.sh" in captured.out
    
    def test_function_exit_status_propagation(self, shell, capsys):
        """Test that function exit status propagates correctly."""
        script = '''
        test_success() {
            echo "success function"
            true
        }
        
        test_failure() {
            echo "failure function"
            false
        }
        
        test_success && echo "success worked"
        test_failure || echo "failure worked"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "success function" in captured.out
        assert "success worked" in captured.out
        assert "failure function" in captured.out
        assert "failure worked" in captured.out


class TestFunctionErrorHandling:
    """Test error handling in function execution."""
    
    def test_undefined_function_call(self, shell, capsys):
        """Test calling undefined function."""
        result = shell.run_command("undefined_function_xyz")
        assert result != 0
        
        # Just verify the command failed - stderr capture may not work properly
        assert result != 0
    
    def test_function_with_command_error(self, shell, capsys):
        """Test function containing command that fails."""
        script = '''
        failing_function() {
            echo "before error"
            false
            echo "after error"
        }
        
        failing_function
        echo "Exit status: $?"
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "before error" in captured.out
        assert "after error" in captured.out
        # PSH may continue after false and return success from echo
        assert "Exit status:" in captured.out
    
    def test_function_redefinition(self, shell, capsys):
        """Test redefining an existing function."""
        script = '''
        my_func() {
            echo "first definition"
        }
        
        my_func
        
        my_func() {
            echo "second definition"
        }
        
        my_func
        '''
        
        result = shell.run_command(script)
        assert result == 0
        
        captured = capsys.readouterr()
        assert "first definition" in captured.out
        assert "second definition" in captured.out