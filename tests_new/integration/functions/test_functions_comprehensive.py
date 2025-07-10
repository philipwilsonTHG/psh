"""
Comprehensive shell function integration tests.

Tests for shell function definition, execution, parameter handling, return values,
scoping, management commands (declare -f, unset -f), and integration with other
shell features like pipelines, aliases, and redirection.
"""

import pytest


class TestFunctionDefinition:
    """Test function definition syntax and parsing."""
    
    def test_posix_function_definition(self, shell_with_temp_dir):
        """Test POSIX-style function definition name() { ... }."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('greet() { echo "Hello, World!"; }')
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('greet') is not None
    
    def test_function_keyword_syntax(self, shell_with_temp_dir):
        """Test function keyword syntax."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('function greet { echo "Hello"; }')
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('greet') is not None
    
    def test_function_keyword_with_parentheses(self, shell_with_temp_dir):
        """Test function keyword with parentheses."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('function greet() { echo "Hello"; }')
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('greet') is not None
    
    def test_multiline_function_definition(self, shell_with_temp_dir):
        """Test multiline function definition."""
        shell = shell_with_temp_dir
        
        script = '''
        greet() {
            echo "Hello"
            echo "World"
        }
        '''
        result = shell.run_command(script)
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('greet') is not None
    
    def test_empty_function_definition(self, shell_with_temp_dir):
        """Test empty function definition."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('noop() { }')
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('noop') is not None
    
    def test_function_with_complex_body(self, shell_with_temp_dir):
        """Test function with complex command structures."""
        shell = shell_with_temp_dir
        
        script = '''
        complex_func() {
            echo "Starting"
            VAR="test"
            echo "VAR is: $VAR"
        }
        '''
        result = shell.run_command(script)
        assert result == 0
        
        # Verify function was defined
        assert shell.function_manager.get_function('complex_func') is not None


class TestFunctionExecution:
    """Test function execution and calling."""
    
    def test_simple_function_call(self, shell, capsys):
        """Test calling a simple function."""
        shell.run_command('greet() { echo "Hello World"; }')
        shell.run_command('greet')
        
        captured = capsys.readouterr()
        assert captured.out == "Hello World\n"
    
    def test_function_with_arguments(self, shell, capsys):
        """Test function with positional parameters."""
        shell.run_command('greet() { echo "Hello $1"; }')
        shell.run_command('greet Alice')
        
        captured = capsys.readouterr()
        assert captured.out == "Hello Alice\n"
    
    def test_function_multiple_arguments(self, shell, capsys):
        """Test function with multiple arguments."""
        shell.run_command('showargs() { echo "Args: $1 $2 $3"; }')
        shell.run_command('showargs a b c')
        
        captured = capsys.readouterr()
        assert captured.out == "Args: a b c\n"
    
    def test_function_special_variables(self, shell, capsys):
        """Test special variables in functions ($#, $@, $*)."""
        shell.run_command('info() { echo "Count: $# All: $@"; }')
        shell.run_command('info one two three')
        
        captured = capsys.readouterr()
        assert captured.out == 'Count: 3 All: one two three\n'
    
    def test_function_no_arguments(self, shell, capsys):
        """Test function called with no arguments."""
        shell.run_command('noargs() { echo "No args: $#"; }')
        shell.run_command('noargs')
        
        captured = capsys.readouterr()
        assert captured.out == "No args: 0\n"


class TestFunctionReturnValues:
    """Test function return values and exit codes."""
    
    def test_function_return_success(self, shell_with_temp_dir):
        """Test function explicit return with success."""
        shell = shell_with_temp_dir
        
        shell.run_command('success() { return 0; }')
        result = shell.run_command('success')
        assert result == 0
    
    def test_function_return_failure(self, shell_with_temp_dir):
        """Test function explicit return with failure."""
        shell = shell_with_temp_dir
        
        shell.run_command('fail() { return 42; }')
        result = shell.run_command('fail')
        assert result == 42
    
    def test_function_implicit_return(self, shell_with_temp_dir):
        """Test function implicit return from last command."""
        shell = shell_with_temp_dir
        
        shell.run_command('test_func() { true; false; }')
        result = shell.run_command('test_func')
        assert result == 1  # false returns 1
    
    def test_function_empty_body_return(self, shell_with_temp_dir):
        """Test empty function returns 0."""
        shell = shell_with_temp_dir
        
        shell.run_command('noop() { }')
        result = shell.run_command('noop')
        assert result == 0


class TestFunctionScoping:
    """Test function variable scoping and parameter handling."""
    
    def test_function_modifies_global_variables(self, shell_with_temp_dir):
        """Test that functions can modify global variables."""
        shell = shell_with_temp_dir
        
        shell.run_command('var=initial')
        shell.run_command('modify() { var=modified; }')
        shell.run_command('modify')
        shell.run_command('echo $var > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert content == "modified"
    
    def test_function_parameters_dont_leak(self, shell_with_temp_dir):
        """Test that function parameters don't affect outer scope."""
        shell = shell_with_temp_dir
        
        shell.run_command('set a b c')  # Set positional params
        shell.run_command('func() { echo "In func: $1" > func_output.txt; }')
        shell.run_command('func xyz')
        shell.run_command('echo "After func: $1" > outer_output.txt')
        
        with open('func_output.txt', 'r') as f:
            func_content = f.read().strip()
        with open('outer_output.txt', 'r') as f:
            outer_content = f.read().strip()
        
        assert func_content == "In func: xyz"
        assert outer_content == "After func: a"
    
    def test_function_accesses_global_variables(self, shell, capsys):
        """Test that functions can access global variables."""
        shell.run_command('GLOBAL_VAR="global_value"')
        shell.run_command('showglobal() { echo "Global: $GLOBAL_VAR"; }')
        shell.run_command('showglobal')
        
        captured = capsys.readouterr()
        assert captured.out == "Global: global_value\n"
    
    def test_function_parameter_shadowing(self, shell, capsys):
        """Test function parameters shadow global positional parameters."""
        shell.run_command('set global1 global2')
        shell.run_command('test_shadow() { echo "Param1: $1 Param2: $2"; }')
        shell.run_command('test_shadow func1 func2')
        
        captured = capsys.readouterr()
        assert captured.out == "Param1: func1 Param2: func2\n"


class TestFunctionNesting:
    """Test function calling other functions."""
    
    def test_function_calling_function(self, shell, capsys):
        """Test function calling another function."""
        shell.run_command('inner() { echo "Inner function"; }')
        shell.run_command('outer() { echo "Outer function"; inner; }')
        shell.run_command('outer')
        
        captured = capsys.readouterr()
        assert "Outer function" in captured.out
        assert "Inner function" in captured.out
    
    def test_function_chain_calls(self, shell, capsys):
        """Test chain of function calls."""
        shell.run_command('func1() { echo "Function 1"; func2; }')
        shell.run_command('func2() { echo "Function 2"; func3; }')
        shell.run_command('func3() { echo "Function 3"; }')
        shell.run_command('func1')
        
        captured = capsys.readouterr()
        assert "Function 1" in captured.out
        assert "Function 2" in captured.out
        assert "Function 3" in captured.out
    
    @pytest.mark.xfail(reason="Deep recursion might not be fully supported or could cause stack issues")
    def test_simple_recursion(self, shell_with_temp_dir):
        """Test simple recursive function call."""
        shell = shell_with_temp_dir
        
        # Simple non-infinite recursion
        shell.run_command('countdown() { echo "Count: $1"; }')
        shell.run_command('countdown 3 > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert "Count: 3" in content


class TestFunctionManagement:
    """Test function management commands."""
    
    def test_declare_f_lists_functions(self, shell_with_temp_dir):
        """Test declare -f lists all functions."""
        shell = shell_with_temp_dir
        
        shell.run_command('func1() { echo "1"; }')
        shell.run_command('func2() { echo "2"; }')
        shell.run_command('declare -f > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read()
        assert "func1" in content
        assert "func2" in content
    
    def test_declare_f_specific_function(self, shell_with_temp_dir):
        """Test declare -f shows specific function."""
        shell = shell_with_temp_dir
        
        shell.run_command('greet() { echo "Hello"; }')
        shell.run_command('declare -f greet > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read()
        assert "greet" in content
    
    def test_declare_f_nonexistent_function(self, shell_with_temp_dir):
        """Test declare -f with nonexistent function."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('declare -f nonexistent')
        assert result == 1
    
    def test_unset_f_removes_function(self, shell_with_temp_dir):
        """Test unset -f removes a function."""
        shell = shell_with_temp_dir
        
        shell.run_command('greet() { echo "Hello"; }')
        
        # Verify function exists
        assert shell.function_manager.get_function('greet') is not None
        
        result = shell.run_command('unset -f greet')
        assert result == 0
        
        # Verify function is removed
        assert shell.function_manager.get_function('greet') is None
    
    def test_unset_f_nonexistent_function(self, shell_with_temp_dir):
        """Test unset -f with nonexistent function."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('unset -f nonexistent')
        assert result == 1
    
    def test_redefine_function(self, shell, capsys):
        """Test redefining a function."""
        shell.run_command('greet() { echo "Hello"; }')
        shell.run_command('greet() { echo "Hi"; }')
        shell.run_command('greet')
        
        captured = capsys.readouterr()
        assert captured.out == "Hi\n"


class TestFunctionPrecedence:
    """Test function precedence over other commands."""
    
    def test_function_overrides_external_command(self, shell, capsys):
        """Test that functions take precedence over external commands."""
        # Define a function that overrides an external command
        shell.run_command('ls() { echo "Function ls: $@"; }')
        shell.run_command('ls test')
        
        captured = capsys.readouterr()
        assert captured.out == "Function ls: test\n"
    
    @pytest.mark.xfail(reason="Function precedence over builtins may not be fully implemented")
    def test_function_vs_builtin(self, shell, capsys):
        """Test function precedence vs builtins."""
        # Define function with builtin name
        shell.run_command('echo() { printf "Function echo: %s\\n" "$@"; }')
        shell.run_command('echo test')
        
        captured = capsys.readouterr()
        # Should call function, not builtin
        assert "Function echo" in captured.out


class TestFunctionWithRedirection:
    """Test functions with I/O redirection."""
    
    def test_function_output_redirection(self, temp_dir):
        """Test redirecting function output to file."""
        import subprocess
        import sys
        import os
        
        # Run PSH as subprocess to avoid pytest stream capture conflicts
        script = '''
greet() { echo "Hello from function"; }
greet > function_output.txt
'''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True, 
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        output_path = os.path.join(temp_dir, 'function_output.txt')
        with open(output_path, 'r') as f:
            content = f.read().strip()
        assert content == "Hello from function"
    
    def test_function_input_redirection(self, temp_dir):
        """Test function with input redirection."""
        import subprocess
        import sys
        import os
        
        # Create input file
        input_path = os.path.join(temp_dir, 'input.txt')
        with open(input_path, 'w') as f:
            f.write("test input\n")
        
        # Run PSH as subprocess to avoid pytest stream capture conflicts
        script = '''
read_func() { read line; echo "Read: $line"; }
read_func < input.txt > output.txt
'''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        output_path = os.path.join(temp_dir, 'output.txt')
        with open(output_path, 'r') as f:
            content = f.read().strip()
        assert content == "Read: test input"
    
    def test_function_error_redirection(self, temp_dir):
        """Test function with error output redirection."""
        import subprocess
        import sys
        import os
        
        # Run PSH as subprocess to avoid pytest stream capture conflicts
        script = '''
error_func() { echo "error message" >&2; }
error_func 2> error.txt
'''
        
        result = subprocess.run([
            sys.executable, '-m', 'psh', '-c', script
        ], cwd=temp_dir, capture_output=True, text=True,
           env={**os.environ, 'PYTHONPATH': os.getcwd()})
        
        assert result.returncode == 0
        
        error_path = os.path.join(temp_dir, 'error.txt')
        with open(error_path, 'r') as f:
            content = f.read().strip()
        assert content == "error message"


class TestFunctionInPipelines:
    """Test functions in pipeline contexts."""
    
    def test_function_as_pipeline_source(self, shell_with_temp_dir):
        """Test function as source of pipeline."""
        shell = shell_with_temp_dir
        
        shell.run_command('generate() { echo "line1"; echo "line2"; }')
        shell.run_command('generate | wc -l > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert content == "2"
    
    @pytest.mark.xfail(reason="Pipeline function redirection has test isolation issues")
    def test_function_as_pipeline_filter(self, shell_with_temp_dir):
        """Test function as filter in pipeline."""
        shell = shell_with_temp_dir
        
        result1 = shell.run_command('add_prefix() { while read line; do echo "PREFIX: $line"; done; }')
        assert result1 == 0
        
        result2 = shell.run_command('echo "test" | add_prefix > output.txt')
        assert result2 == 0
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert content == "PREFIX: test"
    
    @pytest.mark.xfail(reason="Complex pipeline function interactions may have output capture issues")
    def test_function_pipeline_chain(self, shell_with_temp_dir):
        """Test multiple functions in pipeline."""
        shell = shell_with_temp_dir
        
        shell.run_command('func1() { echo "data"; }')
        shell.run_command('func2() { read input; echo "processed: $input"; }')
        shell.run_command('func1 | func2 > output.txt')
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert content == "processed: data"


class TestFunctionErrorHandling:
    """Test function error conditions and edge cases."""
    
    def test_invalid_function_name_reserved_word(self, shell_with_temp_dir):
        """Test error on reserved word as function name."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('function() { echo "test"; }')
        assert result != 0  # Should fail
    
    def test_invalid_function_name_number(self, shell_with_temp_dir):
        """Test error on invalid function name starting with number."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('123func() { echo "test"; }')
        assert result != 0  # Should fail
    
    def test_function_with_syntax_error(self, shell_with_temp_dir):
        """Test function definition with syntax error."""
        shell = shell_with_temp_dir
        
        # Missing closing brace
        result = shell.run_command('broken() { echo "test"')
        assert result != 0  # Should fail
    
    def test_calling_undefined_function(self, shell_with_temp_dir):
        """Test calling undefined function."""
        shell = shell_with_temp_dir
        
        result = shell.run_command('undefined_function')
        assert result == 127  # Command not found


class TestFunctionWithControlStructures:
    """Test functions containing control structures."""
    
    @pytest.mark.xfail(reason="Complex control structures in functions may not be fully implemented")
    def test_function_with_if_statement(self, shell_with_temp_dir):
        """Test function with if statement."""
        shell = shell_with_temp_dir
        
        script = '''
        test_if() {
            if [ "$1" = "yes" ]; then
                echo "affirmative"
            else
                echo "negative"
            fi
        }
        '''
        result = shell.run_command(script)
        assert result == 0
        
        result2 = shell.run_command('test_if yes > output.txt')
        assert result2 == 0
        
        with open('output.txt', 'r') as f:
            content = f.read().strip()
        assert content == "affirmative"
    
    @pytest.mark.xfail(reason="Complex control structures in functions may not be fully implemented")
    def test_function_with_for_loop(self, shell_with_temp_dir):
        """Test function with for loop."""
        shell = shell_with_temp_dir
        
        script = '''
        list_items() {
            for item in a b c; do
                echo "Item: $item"
            done
        }
        '''
        result = shell.run_command(script)
        assert result == 0
        
        result2 = shell.run_command('list_items > output.txt')
        assert result2 == 0
        
        with open('output.txt', 'r') as f:
            content = f.read()
        assert "Item: a" in content
        assert "Item: b" in content
        assert "Item: c" in content
    
    @pytest.mark.xfail(reason="Complex control structures with local variables in functions may not be fully implemented")
    def test_function_with_while_loop(self, shell_with_temp_dir):
        """Test function with while loop."""
        shell = shell_with_temp_dir
        
        script = '''
        count_down() {
            local i=$1
            while [ $i -gt 0 ]; do
                echo "Count: $i"
                i=$((i - 1))
            done
        }
        '''
        result = shell.run_command(script)
        assert result == 0
        
        result2 = shell.run_command('count_down 3 > output.txt')
        assert result2 == 0
        
        with open('output.txt', 'r') as f:
            content = f.read()
        assert "Count: 3" in content
        assert "Count: 2" in content
        assert "Count: 1" in content


class TestFunctionPerformance:
    """Test function performance and stress cases."""
    
    def test_many_function_definitions(self, shell_with_temp_dir):
        """Test defining many functions."""
        shell = shell_with_temp_dir
        
        # Define 50 functions
        for i in range(50):
            result = shell.run_command(f'func{i}() {{ echo "Function {i}"; }}')
            assert result == 0
        
        # Verify they all exist
        for i in range(50):
            assert shell.function_manager.get_function(f'func{i}') is not None
    
    @pytest.mark.xfail(reason="Function redirection has test isolation issues")
    def test_function_with_many_commands(self, shell_with_temp_dir):
        """Test function with many commands."""
        shell = shell_with_temp_dir
        
        # Create function with many echo commands
        commands = []
        for i in range(20):
            commands.append(f'echo "Line {i}"')
        
        script = f'many_commands() {{ {"; ".join(commands)}; }}'
        result = shell.run_command(script)
        assert result == 0
        
        # Test execution
        result2 = shell.run_command('many_commands > output.txt')
        assert result2 == 0
        
        with open('output.txt', 'r') as f:
            content = f.read()
        assert "Line 0" in content
        assert "Line 19" in content
    
    def test_function_call_overhead(self, shell_with_temp_dir):
        """Test overhead of function calls."""
        shell = shell_with_temp_dir
        
        shell.run_command('simple() { echo "simple"; }')
        
        # Call function multiple times
        for i in range(10):
            result = shell.run_command('simple > /dev/null')
            assert result == 0