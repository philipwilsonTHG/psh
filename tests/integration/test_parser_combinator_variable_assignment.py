#!/usr/bin/env python3
"""Integration tests for parser combinator variable assignment support.

This module tests that the parser combinator correctly parses variable
assignments and that the resulting AST nodes are properly structured.
"""

import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.ast_nodes import (
    SimpleCommand, Pipeline, CommandList, AndOrList,
    ArrayAssignment, ArrayElementAssignment
)


class TestParserCombinatorVariableAssignment:
    """Test variable assignment parsing with parser combinator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def parse(self, command: str):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return self.parser.parse(tokens)
    
    def get_simple_command(self, ast):
        """Extract SimpleCommand from AST."""
        if isinstance(ast, CommandList):
            statement = ast.statements[0]
            if isinstance(statement, AndOrList):
                pipeline = statement.pipelines[0]
                cmd = pipeline.commands[0]
            elif isinstance(statement, Pipeline):
                cmd = statement.commands[0]
            else:
                cmd = statement
        else:
            cmd = ast
            
        return cmd if isinstance(cmd, SimpleCommand) else None


class TestSimpleAssignments(TestParserCombinatorVariableAssignment):
    """Test simple variable assignment parsing."""
    
    def test_single_assignment(self):
        """Test: VAR=value"""
        cmd = self.get_simple_command(self.parse("VAR=value"))
        assert cmd is not None
        
        # Parser combinator treats VAR=value as args
        assert len(cmd.args) == 1
        assert cmd.args[0] == "VAR=value"
    
    def test_multiple_assignments(self):
        """Test: VAR1=val1 VAR2=val2 VAR3=val3"""
        cmd = self.get_simple_command(self.parse("VAR1=val1 VAR2=val2 VAR3=val3"))
        assert cmd is not None
        
        # All assignments parsed as arguments
        assert len(cmd.args) == 3
        assert cmd.args[0] == "VAR1=val1"
        assert cmd.args[1] == "VAR2=val2"
        assert cmd.args[2] == "VAR3=val3"
    
    def test_assignment_with_empty_value(self):
        """Test: VAR="""
        cmd = self.get_simple_command(self.parse("VAR="))
        assert cmd is not None
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == "VAR="
    
    def test_assignment_with_quoted_value(self):
        """Test: VAR="hello world" """
        cmd = self.get_simple_command(self.parse('VAR="hello world"'))
        assert cmd is not None
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == 'VAR="hello world"'
    
    def test_assignment_with_single_quotes(self):
        """Test: VAR='$PATH'"""
        cmd = self.get_simple_command(self.parse("VAR='$PATH'"))
        assert cmd is not None
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == "VAR='$PATH'"


class TestAssignmentWithCommands(TestParserCombinatorVariableAssignment):
    """Test variable assignments with commands."""
    
    def test_assignment_before_command(self):
        """Test: VAR=value command arg"""
        cmd = self.get_simple_command(self.parse("VAR=value command arg"))
        assert cmd is not None
        
        # All parsed as args
        assert len(cmd.args) == 3
        assert cmd.args[0] == "VAR=value"
        assert cmd.args[1] == "command"
        assert cmd.args[2] == "arg"
    
    def test_multiple_assignments_with_command(self):
        """Test: VAR1=a VAR2=b cmd -x"""
        cmd = self.get_simple_command(self.parse("VAR1=a VAR2=b cmd -x"))
        assert cmd is not None
        
        # All parsed as args
        assert len(cmd.args) == 4
        assert cmd.args[0] == "VAR1=a"
        assert cmd.args[1] == "VAR2=b"
        assert cmd.args[2] == "cmd"
        assert cmd.args[3] == "-x"
    
    def test_path_assignment_with_command(self):
        """Test: PATH=/usr/local/bin:/usr/bin command"""
        cmd = self.get_simple_command(self.parse("PATH=/usr/local/bin:/usr/bin command"))
        assert cmd is not None
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == "PATH=/usr/local/bin:/usr/bin"
        assert cmd.args[1] == "command"


class TestExportDeclarations(TestParserCombinatorVariableAssignment):
    """Test export declarations."""
    
    def test_export_with_assignment(self):
        """Test: export VAR=value"""
        cmd = self.get_simple_command(self.parse("export VAR=value"))
        assert cmd is not None
        
        # export is the first arg (command)
        assert len(cmd.args) == 2
        assert cmd.args[0] == "export"
        assert cmd.args[1] == "VAR=value"
    
    def test_export_variable_only(self):
        """Test: export VAR"""
        cmd = self.get_simple_command(self.parse("export VAR"))
        assert cmd is not None
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == "export"
        assert cmd.args[1] == "VAR"
    
    def test_export_multiple_variables(self):
        """Test: export VAR1 VAR2=value VAR3"""
        cmd = self.get_simple_command(self.parse("export VAR1 VAR2=value VAR3"))
        assert cmd is not None
        
        assert len(cmd.args) == 4
        assert cmd.args[0] == "export"
        assert cmd.args[1] == "VAR1"
        assert cmd.args[2] == "VAR2=value"
        assert cmd.args[3] == "VAR3"


class TestArrayAssignments(TestParserCombinatorVariableAssignment):
    """Test array assignment parsing."""
    
    def test_array_element_assignment(self):
        """Test: arr[0]=value"""
        cmd = self.get_simple_command(self.parse("arr[0]=value"))
        assert cmd is not None
        
        # Should parse as a single argument
        assert len(cmd.args) == 1
        assert cmd.args[0] == "arr[0]=value"
    
    def test_array_element_with_variable_index(self):
        """Test: arr[$i]=value"""
        cmd = self.get_simple_command(self.parse("arr[$i]=value"))
        assert cmd is not None
        
        # Should handle variable in index
        assert len(cmd.args) == 1
        assert cmd.args[0] == "arr[$i]=value"
    
    def test_array_initialization_not_supported(self):
        """Test that array initialization is not supported."""
        # arr=(1 2 3) syntax is not supported
        with pytest.raises(Exception):
            self.parse("arr=(1 2 3)")


class TestAssignmentInControlStructures(TestParserCombinatorVariableAssignment):
    """Test assignments within control structures."""
    
    def test_assignment_in_if_block(self):
        """Test: if true; then VAR=value; echo $VAR; fi"""
        ast = self.parse("if true; then VAR=value; echo $VAR; fi")
        
        # Navigate to then block
        if_stmt = ast.items[0]
        then_block = if_stmt.then_block
        
        # First statement should be assignment command
        first_stmt = then_block.statements[0]
        if isinstance(first_stmt, AndOrList):
            pipeline = first_stmt.pipelines[0]
            cmd = pipeline.commands[0]
            
            assert isinstance(cmd, SimpleCommand)
            # Assignment only (parsed as single arg)
            assert len(cmd.args) == 1
            assert cmd.args[0] == "VAR=value"
    
    def test_assignment_in_loop(self):
        """Test: for i in 1 2 3; do COUNT=$i; done"""
        ast = self.parse("for i in 1 2 3; do COUNT=$i; done")
        
        # Navigate to loop body
        for_loop = ast.items[0]
        body = for_loop.body
        
        # Should have assignment in body
        first_stmt = body.statements[0]
        if isinstance(first_stmt, AndOrList):
            pipeline = first_stmt.pipelines[0]
            cmd = pipeline.commands[0]
            
            assert isinstance(cmd, SimpleCommand)
            # Assignment parsed as single arg
            assert len(cmd.args) == 1
            assert cmd.args[0] == "COUNT=$i"


class TestComplexAssignmentPatterns(TestParserCombinatorVariableAssignment):
    """Test complex assignment patterns."""
    
    def test_assignment_with_command_substitution(self):
        """Test: VAR=$(date)"""
        cmd = self.get_simple_command(self.parse("VAR=$(date)"))
        assert cmd is not None
        
        # Should parse the assignment
        assert len(cmd.args) == 1
        assert "VAR=" in cmd.args[0]
        assert "date" in cmd.args[0]
    
    def test_assignment_with_arithmetic(self):
        """Test: COUNT=$((COUNT + 1))"""
        cmd = self.get_simple_command(self.parse("COUNT=$((COUNT + 1))"))
        assert cmd is not None
        
        # Should parse the assignment with arithmetic expansion
        assert len(cmd.args) == 1
        assert "COUNT=" in cmd.args[0]
    
    def test_readonly_declaration(self):
        """Test: readonly VAR=value"""
        cmd = self.get_simple_command(self.parse("readonly VAR=value"))
        assert cmd is not None
        
        # readonly is the command
        assert len(cmd.args) == 2
        assert cmd.args[0] == "readonly"
        assert cmd.args[1] == "VAR=value"
    
    def test_local_declaration(self):
        """Test: local VAR=value"""
        cmd = self.get_simple_command(self.parse("local VAR=value"))
        assert cmd is not None
        
        # local is the command
        assert len(cmd.args) == 2
        assert cmd.args[0] == "local"
        assert cmd.args[1] == "VAR=value"


class TestAssignmentEdgeCases(TestParserCombinatorVariableAssignment):
    """Test edge cases in assignment parsing."""
    
    def test_assignment_with_special_chars(self):
        """Test: VAR_NAME=value-with-dash"""
        cmd = self.get_simple_command(self.parse("VAR_NAME=value-with-dash"))
        assert cmd is not None
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == "VAR_NAME=value-with-dash"
    
    def test_assignment_with_equals_in_value(self):
        """Test: OPTIONS=--flag=value"""
        cmd = self.get_simple_command(self.parse("OPTIONS=--flag=value"))
        assert cmd is not None
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == "OPTIONS=--flag=value"
    
    def test_mixed_assignment_and_redirect(self):
        """Test: VAR=value command > output.txt"""
        cmd = self.get_simple_command(self.parse("VAR=value command > output.txt"))
        assert cmd is not None
        
        # Check args
        assert len(cmd.args) == 2
        assert cmd.args[0] == "VAR=value"
        assert cmd.args[1] == "command"
        
        # Check redirect
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].target == "output.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])