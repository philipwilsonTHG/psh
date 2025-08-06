"""Unit tests for parser combinator function definitions."""

import pytest
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import FunctionDef, ForLoop, IfConditional, SimpleCommand, StatementList, AndOrList, Pipeline
from psh.token_types import Token, TokenType
from psh.lexer import tokenize as lexer_tokenize


def tokenize(code: str) -> list:
    """Helper to tokenize shell code."""
    return lexer_tokenize(code.strip())


def parse(code: str):
    """Helper to parse shell code."""
    parser = ParserCombinatorShellParser()
    tokens = tokenize(code)
    return parser.parse(tokens)


def unwrap_ast(ast):
    """Helper to unwrap common AST patterns for cleaner assertions."""
    # Handle CommandList/StatementList
    if hasattr(ast, 'statements') and len(ast.statements) == 1:
        return unwrap_ast(ast.statements[0])
    # Handle AndOrList with single pipeline
    if hasattr(ast, 'pipelines') and len(ast.pipelines) == 1 and not ast.operators:
        return unwrap_ast(ast.pipelines[0])
    # Handle Pipeline with single command
    if hasattr(ast, 'commands') and len(ast.commands) == 1:
        return unwrap_ast(ast.commands[0])
    return ast


class TestPOSIXFunctionDefinitions:
    """Test POSIX-style function definitions: name() { ... }"""
    
    def test_simple_posix_function(self):
        """Test basic POSIX function definition."""
        ast = parse("greet() { echo Hello; }")
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        assert isinstance(func.body, StatementList)
        assert len(func.body.statements) == 1
        
        cmd = unwrap_ast(func.body.statements[0])
        assert isinstance(cmd, SimpleCommand)
        assert cmd.args == ["echo", "Hello"]
    
    def test_posix_function_with_newlines(self):
        """Test POSIX function with newlines."""
        ast = parse("""
            greet() {
                echo Hello
                echo World
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        assert len(func.body.statements) == 2
    
    def test_empty_posix_function(self):
        """Test empty POSIX function."""
        ast = parse("noop() { }")
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "noop"
        assert isinstance(func.body, StatementList)
        assert len(func.body.statements) == 0
    
    def test_posix_function_with_control_structures(self):
        """Test POSIX function with control structures."""
        ast = parse("""
            process() {
                if test -f "$1"; then
                    cat "$1"
                else
                    echo "File not found"
                fi
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "process"
        assert len(func.body.statements) == 1
        
        if_stmt = unwrap_ast(func.body.statements[0])
        assert isinstance(if_stmt, IfConditional)


class TestFunctionKeywordDefinitions:
    """Test function keyword style: function name { ... }"""
    
    def test_simple_function_keyword(self):
        """Test basic function keyword definition."""
        ast = parse("function greet { echo Hello; }")
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        assert isinstance(func.body, StatementList)
        assert len(func.body.statements) == 1
    
    def test_function_keyword_with_newlines(self):
        """Test function keyword with newlines."""
        ast = parse("""
            function greet {
                echo Hello
                echo World
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        assert len(func.body.statements) == 2
    
    def test_function_keyword_with_parentheses(self):
        """Test function keyword with parentheses."""
        ast = parse("function greet() { echo Hello; }")
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        assert isinstance(func.body, StatementList)
        assert len(func.body.statements) == 1


class TestFunctionNameValidation:
    """Test function name validation rules."""
    
    def test_valid_function_names(self):
        """Test various valid function names."""
        valid_names = [
            "hello",
            "hello_world",
            "hello123",
            "_private",
            "my-function",  # Hyphens are allowed
            "a1b2c3",
            "_123",
        ]
        
        for name in valid_names:
            ast = parse(f"{name}() {{ echo test; }}")
            func = unwrap_ast(ast)
            assert isinstance(func, FunctionDef)
            assert func.name == name
    
    def test_reserved_words_rejected(self):
        """Test that reserved words cannot be function names."""
        reserved = ['if', 'then', 'else', 'elif', 'fi', 'while', 'do', 
                   'done', 'for', 'case', 'esac', 'function', 'in']
        
        parser = ParserCombinatorShellParser()
        for word in reserved:
            # Try POSIX style
            tokens = tokenize(f"{word}() {{ echo test; }}")
            with pytest.raises(Exception) as excinfo:
                parser.parse(tokens)
            assert "Reserved word cannot be function name" in str(excinfo.value) or "Unexpected token" in str(excinfo.value)


class TestComplexFunctions:
    """Test complex function definitions."""
    
    def test_function_with_loops(self):
        """Test function containing loops."""
        ast = parse("""
            process_files() {
                for file in *.txt; do
                    if test -f "$file"; then
                        echo "Processing $file"
                        cat "$file"
                    fi
                done
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "process_files"
        
        for_loop = unwrap_ast(func.body.statements[0])
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == "file"
        assert for_loop.items == ["*.txt"]
    
    def test_nested_functions(self):
        """Test function containing another function definition."""
        ast = parse("""
            outer() {
                inner() {
                    echo "Inner function"
                }
                inner
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "outer"
        assert len(func.body.statements) == 2
        
        # First statement is inner function definition
        inner_func = unwrap_ast(func.body.statements[0])
        assert isinstance(inner_func, FunctionDef)
        assert inner_func.name == "inner"
        
        # Second statement is call to inner
        call = unwrap_ast(func.body.statements[1])
        assert isinstance(call, SimpleCommand)
        assert call.args == ["inner"]
    
    def test_function_with_local_variables(self):
        """Test function with local variable declarations."""
        ast = parse("""
            calculate() {
                local a=$1
                local b=$2
                echo $((a + b))
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "calculate"
        assert len(func.body.statements) == 3
        
        # Check local declarations
        local1 = unwrap_ast(func.body.statements[0])
        assert isinstance(local1, SimpleCommand)
        assert local1.args[0] == "local"
        
        local2 = unwrap_ast(func.body.statements[1])
        assert isinstance(local2, SimpleCommand)
        assert local2.args[0] == "local"
    
    def test_function_with_return(self):
        """Test function with return statement."""
        ast = parse("""
            check_file() {
                if test -f "$1"; then
                    return 0
                else
                    return 1
                fi
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "check_file"
        
        if_stmt = unwrap_ast(func.body.statements[0])
        assert isinstance(if_stmt, IfConditional)


class TestMultipleFunctions:
    """Test multiple function definitions in same script."""
    
    def test_two_functions(self):
        """Test two function definitions."""
        ast = parse("""
            first() {
                echo "First"
            }
            
            second() {
                echo "Second"
            }
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 2
        
        # Functions at statement level are wrapped in AndOrList -> Pipeline
        func1 = unwrap_ast(ast.statements[0])
        assert isinstance(func1, FunctionDef)
        assert func1.name == "first"
        
        func2 = unwrap_ast(ast.statements[1])
        assert isinstance(func2, FunctionDef)
        assert func2.name == "second"
    
    def test_functions_and_commands(self):
        """Test mix of functions and commands."""
        ast = parse("""
            greet() {
                echo "Hello $1"
            }
            
            echo "Starting..."
            greet World
            echo "Done."
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 4
        
        # First is function (wrapped in AndOrList)
        func = unwrap_ast(ast.statements[0])
        assert isinstance(func, FunctionDef)
        assert func.name == "greet"
        
        # Rest are commands (wrapped in AndOrList)
        for i in range(1, 4):
            assert isinstance(ast.statements[i], AndOrList)


class TestFunctionParsing:
    """Test function parsing edge cases."""
    
    def test_function_with_empty_body_newlines(self):
        """Test function with empty body but newlines."""
        ast = parse("""
            empty() {
            
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "empty"
        assert len(func.body.statements) == 0
    
    def test_function_inline_definition(self):
        """Test function defined on single line."""
        ast = parse("oneliner() { echo test; echo done; }")
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "oneliner"
        assert len(func.body.statements) == 2
    
    def test_function_with_pipeline_body(self):
        """Test function with pipeline in body."""
        ast = parse("""
            filter() {
                cat "$1" | grep pattern | sort
            }
        """)
        func = unwrap_ast(ast)
        
        assert isinstance(func, FunctionDef)
        assert func.name == "filter"
        assert len(func.body.statements) == 1
        
        # Body contains a pipeline
        pipeline = func.body.statements[0].pipelines[0]
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 3