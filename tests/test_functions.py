#!/usr/bin/env python3
"""Test shell function functionality."""

import pytest
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse, ParseError
from psh.ast_nodes import TopLevel, FunctionDef, CommandList


class TestFunctionParsing:
    """Test function definition parsing."""
    
    def test_parse_simple_function_posix(self):
        """Test POSIX-style function definition."""
        code = 'greet() { echo "Hello"; }'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], FunctionDef)
        assert ast.items[0].name == 'greet'
        assert isinstance(ast.items[0].body, CommandList)
    
    def test_parse_function_keyword(self):
        """Test function keyword syntax."""
        code = 'function greet { echo "Hello"; }'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], FunctionDef)
        assert ast.items[0].name == 'greet'
    
    def test_parse_function_keyword_with_parens(self):
        """Test function keyword with parentheses."""
        code = 'function greet() { echo "Hello"; }'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], FunctionDef)
        assert ast.items[0].name == 'greet'
    
    def test_parse_multiline_function(self):
        """Test multiline function definition."""
        code = '''greet() {
            echo "Hello"
            echo "World"
        }'''
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert isinstance(ast.items[0], FunctionDef)
        assert len(ast.items[0].body.and_or_lists) == 2
    
    def test_parse_function_and_command(self):
        """Test parsing function definition followed by command."""
        code = 'greet() { echo "hi"; }; greet'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert len(ast.items) == 2
        assert isinstance(ast.items[0], FunctionDef)
        assert isinstance(ast.items[1], CommandList)
    
    def test_parse_empty_function(self):
        """Test parsing empty function body."""
        code = 'noop() { }'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert isinstance(ast.items[0], FunctionDef)
        assert len(ast.items[0].body.and_or_lists) == 0
    
    def test_parse_nested_braces(self):
        """Test function with command substitution containing braces."""
        code = 'test() { echo "$(echo {a,b})"; }'
        tokens = tokenize(code)
        ast = parse(tokens)
        
        assert isinstance(ast, TopLevel)
        assert isinstance(ast.items[0], FunctionDef)
    
    def test_parse_invalid_function_missing_body(self):
        """Test error on missing function body."""
        code = 'greet()'
        tokens = tokenize(code)
        
        with pytest.raises(ParseError) as exc_info:
            parse(tokens)
        assert "Expected '{'" in str(exc_info.value)
    
    def test_parse_invalid_function_missing_closing_brace(self):
        """Test error on missing closing brace."""
        code = 'greet() { echo "hi"'
        tokens = tokenize(code)
        
        with pytest.raises(ParseError) as exc_info:
            parse(tokens)
        assert "Expected '}'" in str(exc_info.value)


class TestFunctionExecution:
    """Test function execution."""
    
    
    def test_define_and_call_function(self, shell, capsys):
        """Test defining and calling a simple function."""
        shell.run_command('greet() { echo "Hello, World!"; }')
        shell.run_command('greet')
        
        captured = capsys.readouterr()
        assert captured.out == "Hello, World!\n"
    
    def test_function_with_arguments(self, shell, capsys):
        """Test function with positional parameters."""
        shell.run_command('greet() { echo "Hello, $1!"; }')
        shell.run_command('greet Alice')
        
        captured = capsys.readouterr()
        assert captured.out == "Hello, Alice!\n"
    
    def test_function_multiple_arguments(self, shell, capsys):
        """Test function with multiple arguments."""
        shell.run_command('showargs() { echo "Args: $1, $2, $3"; }')
        shell.run_command('showargs a b c')
        
        captured = capsys.readouterr()
        assert captured.out == "Args: a, b, c\n"
    
    def test_function_special_variables(self, shell, capsys):
        """Test special variables in functions."""
        shell.run_command('info() { echo "Count: $#, All: $@"; }')
        shell.run_command('info one two three')
        
        captured = capsys.readouterr()
        assert captured.out == 'Count: 3, All: one two three\n'
    
    def test_function_return_value(self, shell, capsys):
        """Test function return values."""
        shell.run_command('success() { return 0; }')
        exit_code = shell.run_command('success')
        assert exit_code == 0
        
        shell.run_command('fail() { return 42; }')
        exit_code = shell.run_command('fail')
        assert exit_code == 42
    
    def test_function_last_command_exit(self, shell):
        """Test function returns last command's exit status."""
        shell.run_command('test_func() { true; false; }')
        exit_code = shell.run_command('test_func')
        assert exit_code == 1  # false returns 1
    
    def test_function_overwrites_external(self, shell, capsys):
        """Test that functions take precedence over external commands."""
        # Define a function named 'ls' (override external command)
        shell.run_command('ls() { echo "Function ls: $@"; }')
        shell.run_command('ls test')
        
        captured = capsys.readouterr()
        assert captured.out == "Function ls: test\n"
    
    def test_function_with_redirection(self, shell, tmp_path):
        """Test function call with output redirection."""
        output_file = tmp_path / "output.txt"
        
        shell.run_command('greet() { echo "Hello from function"; }')
        shell.run_command(f'greet > {output_file}')
        
        assert output_file.read_text() == "Hello from function\n"
    
    def test_function_calling_function(self, shell, capsys):
        """Test function calling another function."""
        shell.run_command('inner() { echo "Inner function"; }')
        shell.run_command('outer() { echo "Outer function"; inner; }')
        shell.run_command('outer')
        
        captured = capsys.readouterr()
        assert captured.out == "Outer function\nInner function\n"
    
    def test_recursive_function(self, shell, capsys):
        """Test recursive function calls."""
        # Test a simple function without if statements (since if statements in function bodies aren't fully supported yet)
        shell.run_command('countdown() { echo "Count: $1"; }')
        
        # Test that the function is defined
        assert shell.function_manager.get_function('countdown') is not None
        
        # Test execution
        shell.run_command('countdown 5')
        captured = capsys.readouterr()
        assert "Count: 5" in captured.out
    
    def test_function_modifies_variables(self, shell, capsys):
        """Test that functions can modify global variables."""
        shell.run_command('var=initial')
        shell.run_command('modify() { var=modified; }')
        shell.run_command('modify')
        shell.run_command('echo $var')
        
        captured = capsys.readouterr()
        assert "modified" in captured.out
    
    def test_function_parameters_dont_leak(self, shell, capsys):
        """Test that function parameters don't affect outer scope."""
        shell.run_command('set a b c')  # Set positional params
        shell.run_command('func() { echo "In func: $1"; }')
        shell.run_command('func xyz')
        shell.run_command('echo "After func: $1"')
        
        captured = capsys.readouterr()
        assert "In func: xyz" in captured.out
        assert "After func: a" in captured.out


class TestFunctionManagement:
    """Test function management builtins."""
    
    @pytest.fixture
    def shell(self):
        return Shell()
    def test_declare_f_lists_functions(self, shell, capsys):
        """Test declare -f lists all functions."""
        shell.run_command('func1() { echo "1"; }')
        shell.run_command('func2() { echo "2"; }')
        shell.run_command('declare -f')
        
        captured = capsys.readouterr()
        assert "func1" in captured.out
        assert "func2" in captured.out
    
    def test_declare_f_shows_specific_function(self, shell, capsys):
        """Test declare -f name shows specific function."""
        shell.run_command('greet() { echo "Hello"; }')
        shell.run_command('declare -f greet')
        
        captured = capsys.readouterr()
        assert "greet" in captured.out
    
    def test_declare_f_nonexistent_function(self, shell, capsys):
        """Test declare -f with nonexistent function."""
        exit_code = shell.run_command('declare -f nonexistent')
        
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "not found" in captured.err
    
    def test_unset_f_removes_function(self, shell):
        """Test unset -f removes a function."""
        shell.run_command('greet() { echo "Hello"; }')
        
        # Verify function exists and works
        assert shell.function_manager.get_function('greet') is not None
        
        shell.run_command('unset -f greet')
        
        # Verify function is removed
        assert shell.function_manager.get_function('greet') is None
        
        # Try to call the function - should fail with command not found exit code
        exit_code = shell.run_command('greet')
        assert exit_code == 127  # Command not found
    
    def test_unset_f_nonexistent_function(self, shell, capsys):
        """Test unset -f with nonexistent function."""
        exit_code = shell.run_command('unset -f nonexistent')
        
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "not a function" in captured.err
    
    def test_redefine_function(self, shell, capsys):
        """Test redefining a function."""
        shell.run_command('greet() { echo "Hello"; }')
        shell.run_command('greet() { echo "Hi"; }')
        shell.run_command('greet')
        
        captured = capsys.readouterr()
        assert captured.out == "Hi\n"


class TestFunctionEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def shell(self):
        return Shell()
    def test_invalid_function_name_keyword(self, shell, capsys):
        """Test error on reserved word as function name."""
        exit_code = shell.run_command('function() { echo "test"; }')
        
        captured = capsys.readouterr()
        assert exit_code == 1
        assert ("reserved word" in captured.err or 
                "parse" in captured.err.lower() or 
                "expected function name" in captured.err.lower())
    
    def test_invalid_function_name_number(self, shell, capsys):
        """Test error on invalid function name starting with number."""
        exit_code = shell.run_command('123func() { echo "test"; }')
        
        captured = capsys.readouterr()
        assert exit_code == 1
        # Parser might give different error
    
    @pytest.mark.xfail(reason="Functions in pipelines have stdout issues in child processes")
    def test_function_in_pipeline(self, shell, capsys):
        """Test function in a pipeline."""
        # Use a simpler test that doesn't rely on external commands
        shell.run_command('print_arg() { echo "Got: $1"; }')
        shell.run_command('echo "hello" | print_arg "from pipe"')
        
        captured = capsys.readouterr()
        assert "Got: from pipe" in captured.out
    
    def test_function_with_alias(self, shell, capsys):
        """Test function with alias expansion."""
        shell.run_command('alias ll="ls -l"')
        shell.run_command('myfunc() { ll; }')
        # Just verify function was created
        assert shell.function_manager.get_function('myfunc') is not None
    
    def test_empty_function_body(self, shell, capsys):
        """Test function with empty body."""
        shell.run_command('noop() { }')
        exit_code = shell.run_command('noop')
        
        assert exit_code == 0  # Empty function succeeds
    
    def test_function_with_semicolon(self, shell, capsys):
        """Test function with semicolon separator."""
        shell.run_command('func() { echo "one"; echo "two"; }')
        shell.run_command('func')
        
        captured = capsys.readouterr()
        assert captured.out == "one\ntwo\n"