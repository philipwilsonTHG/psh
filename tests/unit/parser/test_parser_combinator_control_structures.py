#!/usr/bin/env python3
"""Comprehensive unit tests for parser combinator control structures.

This module tests all control structures (if, while, for, case) implemented
in the parser combinator, ensuring they correctly parse shell syntax and
generate proper AST nodes.
"""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    IfConditional, WhileLoop, ForLoop, CStyleForLoop, CaseConditional,
    CaseItem, CasePattern, SimpleCommand, AndOrList, Pipeline, CommandList
)


class TestParserCombinatorControlStructures:
    """Test suite for parser combinator control structures."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def parse(self, command: str):
        """Helper to parse a command string."""
        # Strip leading/trailing whitespace and handle multiline strings
        command = command.strip()
        tokens = tokenize(command)
        return self.parser.parse(tokens)
    
    def get_first_statement(self, ast):
        """Extract first statement from AST, unwrapping AndOrList if needed."""
        stmt = ast.statements[0]
        if isinstance(stmt, AndOrList) and len(stmt.pipelines) == 1:
            return stmt.pipelines[0]
        return stmt


class TestIfStatements(TestParserCombinatorControlStructures):
    """Test if/then/elif/else/fi statements."""
    
    def test_simple_if(self):
        """Test basic if/then/fi."""
        ast = self.parse("if true; then echo yes; fi")
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        assert len(if_stmt.condition.statements) == 1
        assert len(if_stmt.then_part.statements) == 1
        assert if_stmt.elif_parts == []
        assert if_stmt.else_part is None
    
    def test_if_else(self):
        """Test if/then/else/fi."""
        ast = self.parse("if false; then echo no; else echo yes; fi")
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        assert if_stmt.else_part is not None
        assert len(if_stmt.else_part.statements) == 1
    
    def test_if_elif_else(self):
        """Test if/then/elif/then/else/fi."""
        ast = self.parse("""
            if test -f file; then
                echo "file"
            elif test -d file; then
                echo "directory"
            else
                echo "not found"
            fi
        """)
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        assert len(if_stmt.elif_parts) == 1
        assert if_stmt.else_part is not None
        
        # Check elif part
        elif_cond, elif_body = if_stmt.elif_parts[0]
        assert len(elif_cond.statements) == 1
        assert len(elif_body.statements) == 1
    
    def test_multiple_elif(self):
        """Test if with multiple elif branches."""
        ast = self.parse("""
            if test $x -eq 1; then echo "one"
            elif test $x -eq 2; then echo "two"
            elif test $x -eq 3; then echo "three"
            else echo "other"
            fi
        """)
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        assert len(if_stmt.elif_parts) == 2
        assert if_stmt.else_part is not None
    
    def test_if_with_complex_condition(self):
        """Test if with pipeline in condition."""
        ast = self.parse("if echo test | grep -q test; then echo found; fi")
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        # Condition should contain a pipeline
        assert len(if_stmt.condition.statements) == 1
    
    def test_if_with_multiple_commands(self):
        """Test if with multiple commands in branches."""
        ast = self.parse("""
            if true; then
                echo "Line 1"
                echo "Line 2"
                echo "Line 3"
            fi
        """)
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        assert len(if_stmt.then_part.statements) >= 3


class TestWhileLoops(TestParserCombinatorControlStructures):
    """Test while/do/done loops."""
    
    def test_simple_while(self):
        """Test basic while loop."""
        ast = self.parse("while true; do echo loop; done")
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        assert len(while_loop.condition.statements) == 1
        assert len(while_loop.body.statements) >= 1
    
    def test_while_with_test_condition(self):
        """Test while with test command."""
        ast = self.parse("while test -f lockfile; do sleep 1; done")
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        assert len(while_loop.condition.statements) == 1
    
    def test_while_with_pipeline_condition(self):
        """Test while with pipeline in condition."""
        ast = self.parse("while ps aux | grep -q process; do wait; done")
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        assert len(while_loop.condition.statements) == 1
    
    def test_while_with_multiple_commands(self):
        """Test while with multiple commands in body."""
        ast = self.parse("""
            while read line; do
                echo "Processing: $line"
                process_line "$line"
                log_result
            done
        """)
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        assert len(while_loop.body.statements) >= 3
    
    def test_while_empty_body(self):
        """Test while with empty body."""
        ast = self.parse("while false; do done")
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        # Empty body should parse correctly
        assert while_loop.body is not None


class TestForLoops(TestParserCombinatorControlStructures):
    """Test for loops (both traditional and C-style)."""
    
    def test_simple_for(self):
        """Test basic for/in loop."""
        ast = self.parse("for i in a b c; do echo $i; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == 'i'
        assert for_loop.items == ['a', 'b', 'c']
        assert len(for_loop.body.statements) >= 1
    
    def test_for_with_quoted_items(self):
        """Test for loop with quoted strings."""
        ast = self.parse('for file in "file 1.txt" "file 2.txt"; do cat "$file"; done')
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == 'file'
        assert len(for_loop.items) == 2
        assert 'file 1.txt' in for_loop.items
        assert 'file 2.txt' in for_loop.items
    
    def test_for_with_variables(self):
        """Test for loop with variable expansion."""
        ast = self.parse("for x in $VAR1 $VAR2 $VAR3; do process $x; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == 'x'
        # Variables are preserved in items
        assert len(for_loop.items) == 3
    
    def test_for_with_glob(self):
        """Test for loop with glob pattern."""
        ast = self.parse("for f in *.txt; do echo $f; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == 'f'
        assert '*.txt' in for_loop.items
    
    def test_for_empty_list(self):
        """Test for loop with empty item list."""
        ast = self.parse("for i in; do echo empty; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == 'i'
        assert for_loop.items == []
    
    def test_c_style_for(self):
        """Test C-style for loop."""
        ast = self.parse("for ((i=0; i<10; i++)); do echo $i; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, CStyleForLoop)
        assert for_loop.init_expr == 'i=0'
        assert for_loop.condition_expr == 'i<10'
        assert for_loop.update_expr == 'i++'
        assert len(for_loop.body.statements) >= 1
    
    def test_c_style_for_empty_parts(self):
        """Test C-style for with empty parts."""
        ast = self.parse("for ((;;)); do break; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, CStyleForLoop)
        assert for_loop.init_expr in [None, '']
        assert for_loop.condition_expr in [None, '']
        assert for_loop.update_expr in [None, '']
    
    def test_c_style_for_complex_expressions(self):
        """Test C-style for with complex expressions."""
        ast = self.parse("for ((i=0, j=10; i<j; i++, j--)); do echo $i $j; done")
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, CStyleForLoop)
        assert 'i=0' in for_loop.init_expr
        assert 'j=10' in for_loop.init_expr
        assert 'i<j' in for_loop.condition_expr
        assert 'i++' in for_loop.update_expr
        assert 'j--' in for_loop.update_expr


class TestCaseStatements(TestParserCombinatorControlStructures):
    """Test case/esac statements."""
    
    def test_simple_case(self):
        """Test basic case statement."""
        ast = self.parse('case $x in a) echo "A";; esac')
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert case_stmt.expr == 'x'
        assert len(case_stmt.items) == 1
        
        item = case_stmt.items[0]
        assert len(item.patterns) == 1
        assert item.patterns[0].pattern == 'a'
        assert item.terminator == ';;'
    
    def test_case_multiple_patterns(self):
        """Test case with multiple patterns."""
        ast = self.parse('case $x in a|b|c) echo "ABC";; esac')
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 1
        
        item = case_stmt.items[0]
        assert len(item.patterns) == 3
        patterns = [p.pattern for p in item.patterns]
        assert 'a' in patterns
        assert 'b' in patterns
        assert 'c' in patterns
    
    def test_case_multiple_items(self):
        """Test case with multiple items."""
        ast = self.parse("""
            case $option in
                -h|--help) show_help;;
                -v|--version) show_version;;
                *) echo "Unknown option";;
            esac
        """)
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 3
        
        # Check default case
        default_item = case_stmt.items[2]
        assert default_item.patterns[0].pattern == '*'
    
    def test_case_glob_patterns(self):
        """Test case with glob patterns."""
        ast = self.parse("""
            case $file in
                *.txt) echo "Text file";;
                *.py) echo "Python file";;
                *.sh) echo "Shell script";;
            esac
        """)
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 3
        assert case_stmt.items[0].patterns[0].pattern == '*.txt'
        assert case_stmt.items[1].patterns[0].pattern == '*.py'
        assert case_stmt.items[2].patterns[0].pattern == '*.sh'
    
    def test_case_empty_commands(self):
        """Test case with empty command list."""
        ast = self.parse('case $x in a) ;; b) echo "B";; esac')
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 2
        
        # First item should have empty commands
        assert len(case_stmt.items[0].commands.statements) == 0
        # Second item should have one command
        assert len(case_stmt.items[1].commands.statements) >= 1
    
    def test_case_complex_commands(self):
        """Test case with multiple commands per item."""
        ast = self.parse("""
            case $action in
                start)
                    echo "Starting service..."
                    check_config
                    start_daemon
                    echo "Started"
                    ;;
                stop)
                    echo "Stopping service..."
                    stop_daemon
                    ;;
            esac
        """)
        case_stmt = self.get_first_statement(ast)
        
        assert isinstance(case_stmt, CaseConditional)
        assert len(case_stmt.items) == 2
        
        # Start item should have multiple commands
        start_item = case_stmt.items[0]
        assert len(start_item.commands.statements) >= 4


class TestNestedControlStructures(TestParserCombinatorControlStructures):
    """Test nested control structures."""
    
    def test_if_inside_while(self):
        """Test if statement inside while loop."""
        ast = self.parse("""
            while true; do
                if test -f stop; then
                    break
                fi
                sleep 1
            done
        """)
        while_loop = self.get_first_statement(ast)
        
        assert isinstance(while_loop, WhileLoop)
        # Body should contain if statement and sleep
        assert len(while_loop.body.statements) >= 2
    
    def test_while_inside_if(self):
        """Test while loop inside if statement."""
        ast = self.parse("""
            if test -f data; then
                while read line; do
                    echo "$line"
                done < data
            fi
        """)
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        # Then part should contain while loop
        assert len(if_stmt.then_part.statements) >= 1
    
    def test_for_inside_for(self):
        """Test nested for loops."""
        ast = self.parse("""
            for i in 1 2 3; do
                for j in a b c; do
                    echo "$i$j"
                done
            done
        """)
        outer_for = self.get_first_statement(ast)
        
        assert isinstance(outer_for, ForLoop)
        assert outer_for.variable == 'i'
        assert outer_for.items == ['1', '2', '3']
        # Body should contain inner for loop
        assert len(outer_for.body.statements) >= 1
    
    def test_case_inside_if(self):
        """Test case statement inside if."""
        ast = self.parse("""
            if test $# -gt 0; then
                case $1 in
                    -h) help;;
                    -v) version;;
                esac
            fi
        """)
        if_stmt = self.get_first_statement(ast)
        
        assert isinstance(if_stmt, IfConditional)
        # Then part should contain case statement
        assert len(if_stmt.then_part.statements) >= 1
    
    def test_complex_nesting(self):
        """Test complex multi-level nesting."""
        ast = self.parse("""
            for file in *.txt; do
                if test -r "$file"; then
                    while read line; do
                        case "$line" in
                            START*) echo "Found start";;
                            END*) break;;
                        esac
                    done < "$file"
                fi
            done
        """)
        for_loop = self.get_first_statement(ast)
        
        assert isinstance(for_loop, ForLoop)
        # This tests parser's ability to handle deep nesting
        assert len(for_loop.body.statements) >= 1


class TestControlStructureEdgeCases(TestParserCombinatorControlStructures):
    """Test edge cases and error conditions."""
    
    def test_if_without_then(self):
        """Test if without then - should fail."""
        with pytest.raises(Exception):
            self.parse("if true; echo yes; fi")
    
    def test_if_without_fi(self):
        """Test if without fi - should fail."""
        with pytest.raises(Exception):
            self.parse("if true; then echo yes")
    
    def test_while_without_do(self):
        """Test while without do - should fail."""
        with pytest.raises(Exception):
            self.parse("while true; echo loop; done")
    
    def test_for_without_in(self):
        """Test for without in - should fail."""
        with pytest.raises(Exception):
            self.parse("for i a b c; do echo $i; done")
    
    def test_case_without_in(self):
        """Test case without in - should fail."""
        with pytest.raises(Exception):
            self.parse("case $x a) echo A;; esac")
    
    def test_case_without_closing_paren(self):
        """Test case pattern without ) - should fail."""
        with pytest.raises(Exception):
            self.parse("case $x in a echo A;; esac")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])