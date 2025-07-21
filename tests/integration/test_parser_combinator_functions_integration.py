"""Integration tests for parser combinator function definitions.

These tests verify that functions work correctly in combination with
other shell features like pipelines, redirections, and control flow.
"""

import pytest
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    FunctionDef, ForLoop, IfConditional, SimpleCommand, StatementList, 
    AndOrList, Pipeline, WhileLoop, CaseConditional
)
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


class TestFunctionIntegration:
    """Test functions integrated with other shell features."""
    
    def test_function_with_pipeline_calls(self):
        """Test function that uses pipelines internally."""
        ast = parse("""
            process_logs() {
                cat /var/log/system.log | grep ERROR | sort | uniq -c
            }
            
            process_logs | head -10
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 2
        
        # First statement is function definition
        func = unwrap_ast(ast.statements[0])
        assert isinstance(func, FunctionDef)
        assert func.name == "process_logs"
        
        # Function body contains a pipeline
        func_pipeline = func.body.statements[0].pipelines[0]
        assert isinstance(func_pipeline, Pipeline)
        assert len(func_pipeline.commands) == 4  # cat | grep | sort | uniq
        
        # Second statement is a pipeline calling the function
        call_pipeline = ast.statements[1].pipelines[0]
        assert isinstance(call_pipeline, Pipeline)
        assert len(call_pipeline.commands) == 2  # process_logs | head
    
    def test_function_with_redirections(self):
        """Test function with input/output redirections."""
        ast = parse("""
            backup() {
                tar czf backup.tar.gz "$@" 2>backup.err
            }
            
            restore() {
                tar xzf "$1" >restore.log 2>&1
            }
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 2
        
        # Check backup function
        backup = unwrap_ast(ast.statements[0])
        assert isinstance(backup, FunctionDef)
        assert backup.name == "backup"
        
        tar_cmd = unwrap_ast(backup.body.statements[0])
        assert isinstance(tar_cmd, SimpleCommand)
        assert len(tar_cmd.redirects) == 1
        assert tar_cmd.redirects[0].type == "2>"
        assert tar_cmd.redirects[0].target == "backup.err"
        
        # Check restore function
        restore = unwrap_ast(ast.statements[1])
        assert isinstance(restore, FunctionDef)
        assert restore.name == "restore"
    
    def test_function_with_and_or_logic(self):
        """Test function using && and || operators."""
        ast = parse("""
            try_command() {
                command1 && command2 || command3
            }
            
            safe_remove() {
                test -f "$1" && rm "$1" || echo "File not found"
            }
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 2
        
        # Check try_command function
        try_cmd = unwrap_ast(ast.statements[0])
        assert isinstance(try_cmd, FunctionDef)
        assert try_cmd.name == "try_command"
        
        and_or_list = try_cmd.body.statements[0]
        assert isinstance(and_or_list, AndOrList)
        assert len(and_or_list.pipelines) == 3
        assert and_or_list.operators == ["&&", "||"]
        
        # Check safe_remove function
        safe_rm = unwrap_ast(ast.statements[1])
        assert isinstance(safe_rm, FunctionDef)
        assert safe_rm.name == "safe_remove"
    
    def test_nested_function_calls(self):
        """Test functions calling other functions."""
        ast = parse("""
            helper() {
                echo "Helper: $1"
            }
            
            wrapper() {
                echo "Before"
                helper "test"
                echo "After"
            }
            
            main() {
                wrapper
                helper "direct"
            }
        """)
        
        assert isinstance(ast, StatementList)
        assert len(ast.statements) == 3
        
        # Verify all three functions
        funcs = [unwrap_ast(s) for s in ast.statements]
        assert all(isinstance(f, FunctionDef) for f in funcs)
        assert [f.name for f in funcs] == ["helper", "wrapper", "main"]
        
        # Check wrapper calls helper
        wrapper = funcs[1]
        wrapper_cmds = [unwrap_ast(s) for s in wrapper.body.statements]
        assert wrapper_cmds[1].args[0] == "helper"
        
        # Check main calls both
        main = funcs[2]
        main_cmds = [unwrap_ast(s) for s in main.body.statements]
        assert main_cmds[0].args[0] == "wrapper"
        assert main_cmds[1].args[0] == "helper"
    
    def test_function_with_complex_control_flow(self):
        """Test function with nested control structures."""
        ast = parse("""
            process_files() {
                for dir in "$@"; do
                    if [ -d "$dir" ]; then
                        while read -r file; do
                            case "$file" in
                                *.txt) cat "$file" ;;
                                *.log) tail -n 100 "$file" ;;
                                *) echo "Unknown type: $file" ;;
                            esac
                        done < <(find "$dir" -type f)
                    else
                        echo "Not a directory: $dir"
                    fi
                done
            }
        """)
        
        func = unwrap_ast(parse("""
            process_files() {
                for dir in "$@"; do
                    if [ -d "$dir" ]; then
                        while read -r file; do
                            case "$file" in
                                *.txt) cat "$file" ;;
                                *.log) tail -n 100 "$file" ;;
                                *) echo "Unknown type: $file" ;;
                            esac
                        done
                    else
                        echo "Not a directory: $dir"
                    fi
                done
            }
        """))
        
        assert isinstance(func, FunctionDef)
        assert func.name == "process_files"
        
        # Check for loop
        for_loop = unwrap_ast(func.body.statements[0])
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == "dir"
        
        # Check if statement inside for loop
        if_stmt = unwrap_ast(for_loop.body.statements[0])
        assert isinstance(if_stmt, IfConditional)
        
        # Check while loop in then part
        while_loop = unwrap_ast(if_stmt.then_part.statements[0])
        assert isinstance(while_loop, WhileLoop)
        
        # Check case statement in while loop
        case_stmt = unwrap_ast(while_loop.body.statements[0])
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 3
    
    def test_function_parameter_handling(self):
        """Test function using positional parameters."""
        ast = parse("""
            validate_args() {
                if [ $# -eq 0 ]; then
                    echo "Usage: validate_args <args...>"
                    return 1
                fi
                
                echo "First arg: $1"
                echo "All args: $@"
                shift
                echo "After shift: $@"
            }
        """)
        
        func = unwrap_ast(ast)
        assert isinstance(func, FunctionDef)
        assert func.name == "validate_args"
        
        # Verify the function body has expected structure
        assert len(func.body.statements) >= 3
        
        # First statement is if
        if_stmt = unwrap_ast(func.body.statements[0])
        assert isinstance(if_stmt, IfConditional)
    
    def test_recursive_function(self):
        """Test recursive function definition."""
        ast = parse("""
            factorial() {
                local n=$1
                if [ $n -le 1 ]; then
                    echo 1
                else
                    local prev=$(factorial $((n - 1)))
                    echo $((n * prev))
                fi
            }
        """)
        
        func = unwrap_ast(ast)
        assert isinstance(func, FunctionDef)
        assert func.name == "factorial"
        
        # Check if statement
        if_stmt = unwrap_ast(func.body.statements[1])
        assert isinstance(if_stmt, IfConditional)
        
        # Check recursive call in else part
        else_stmts = if_stmt.else_part.statements
        assert len(else_stmts) >= 2
        
        # The recursive call is in a command substitution
        local_cmd = unwrap_ast(else_stmts[0])
        assert isinstance(local_cmd, SimpleCommand)
        assert local_cmd.args[0] == "local"
    
    def test_function_with_background_jobs(self):
        """Test function that launches background jobs."""
        ast = parse("""
            parallel_process() {
                process1 &
                process2 &
                process3 &
                wait
            }
        """)
        
        func = unwrap_ast(ast)
        assert isinstance(func, FunctionDef)
        assert func.name == "parallel_process"
        
        # Check background commands
        for i in range(3):
            cmd = unwrap_ast(func.body.statements[i])
            assert isinstance(cmd, SimpleCommand)
            assert cmd.background == True
        
        # Check wait command
        wait_cmd = unwrap_ast(func.body.statements[3])
        assert isinstance(wait_cmd, SimpleCommand)
        assert wait_cmd.args[0] == "wait"
        assert wait_cmd.background == False


class TestFunctionScriptIntegration:
    """Test complete scripts with functions."""
    
    def test_utility_script(self):
        """Test a complete utility script with multiple functions."""
        ast = parse("""
            #!/bin/bash
            
            # Logging functions
            log() {
                echo "[$(date +%Y-%m-%d\\ %H:%M:%S)] $@"
            }
            
            error() {
                log "ERROR: $@" >&2
                return 1
            }
            
            # Main processing function
            process() {
                local file=$1
                
                if [ ! -f "$file" ]; then
                    error "File not found: $file"
                    return 1
                fi
                
                log "Processing $file"
                cat "$file" | sort | uniq
            }
            
            # Script execution
            for arg in "$@"; do
                process "$arg" || continue
            done
        """)
        
        assert isinstance(ast, StatementList)
        # Should have: shebang comment (simple command), 3 functions, 1 for loop
        assert len(ast.statements) >= 4
        
        # Find functions
        functions = []
        for stmt in ast.statements:
            func = unwrap_ast(stmt)
            if isinstance(func, FunctionDef):
                functions.append(func)
        
        assert len(functions) == 3
        assert [f.name for f in functions] == ["log", "error", "process"]
    
    def test_function_library(self):
        """Test a function library pattern."""
        ast = parse("""
            # String manipulation library
            
            str_trim() {
                local str="$1"
                str="${str#"${str%%[![:space:]]*}"}"
                str="${str%"${str##*[![:space:]]}"}"
                echo "$str"
            }
            
            str_upper() {
                echo "$1" | tr '[:lower:]' '[:upper:]'
            }
            
            str_lower() {
                echo "$1" | tr '[:upper:]' '[:lower:]'
            }
            
            str_replace() {
                local str="$1"
                local search="$2"
                local replace="$3"
                echo "${str//$search/$replace}"
            }
        """)
        
        assert isinstance(ast, StatementList)
        
        # All statements should be functions
        functions = [unwrap_ast(s) for s in ast.statements]
        assert all(isinstance(f, FunctionDef) for f in functions)
        assert [f.name for f in functions] == ["str_trim", "str_upper", "str_lower", "str_replace"]