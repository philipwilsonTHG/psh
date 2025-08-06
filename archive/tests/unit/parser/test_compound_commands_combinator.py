#!/usr/bin/env python3
"""Test compound command support in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import SubshellGroup, BraceGroup


class TestCompoundCommandsCombinator:
    """Test compound command parsing in parser combinator."""
    
    def setup_method(self):
        """Set up parser for testing."""
        self.parser = ParserCombinatorShellParser()
    
    def find_compound_commands(self, node, visited=None):
        """Recursively find compound command nodes in AST."""
        if visited is None:
            visited = set()
        
        # Avoid infinite recursion
        if id(node) in visited:
            return []
        visited.add(id(node))
        
        result = []
        
        if isinstance(node, (SubshellGroup, BraceGroup)):
            result.append(node)
        
        if hasattr(node, '__dict__'):
            for attr_value in node.__dict__.values():
                if hasattr(attr_value, '__dict__'):
                    result.extend(self.find_compound_commands(attr_value, visited))
                elif isinstance(attr_value, list):
                    for item in attr_value:
                        if hasattr(item, '__dict__'):
                            result.extend(self.find_compound_commands(item, visited))
        
        return result
    
    def test_simple_subshell(self):
        """Test simple subshell (echo hello)."""
        test_input = "(echo hello)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        subshell = compounds[0]
        assert isinstance(subshell, SubshellGroup)
        assert len(subshell.statements.statements) == 1
    
    def test_simple_brace_group(self):
        """Test simple brace group { echo hello; }."""
        test_input = "{ echo hello; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        brace_group = compounds[0]
        assert isinstance(brace_group, BraceGroup)
        assert len(brace_group.statements.statements) == 1
    
    def test_subshell_with_multiple_commands(self):
        """Test subshell with multiple commands (echo a; echo b)."""
        test_input = "(echo a; echo b)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        subshell = compounds[0]
        assert isinstance(subshell, SubshellGroup)
        assert len(subshell.statements.statements) == 2
    
    def test_brace_group_with_multiple_commands(self):
        """Test brace group with multiple commands { echo a; echo b; }."""
        test_input = "{ echo a; echo b; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        brace_group = compounds[0]
        assert isinstance(brace_group, BraceGroup)
        assert len(brace_group.statements.statements) == 2
    
    def test_subshell_with_pipeline(self):
        """Test subshell containing pipeline (cat file | grep pattern)."""
        test_input = "(cat file | grep pattern)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        subshell = compounds[0]
        assert isinstance(subshell, SubshellGroup)
        # Should have one statement containing a pipeline
        assert len(subshell.statements.statements) == 1
    
    def test_brace_group_with_pipeline(self):
        """Test brace group containing pipeline { cat file | grep pattern; }."""
        test_input = "{ cat file | grep pattern; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        brace_group = compounds[0]
        assert isinstance(brace_group, BraceGroup)
        # Should have one statement containing a pipeline
        assert len(brace_group.statements.statements) == 1
    
    def test_nested_subshells(self):
        """Test nested subshells ( (echo nested) )."""
        test_input = "( (echo nested) )"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 2  # Outer and inner subshell
        
        # Check that we have nested subshells
        for compound in compounds:
            assert isinstance(compound, SubshellGroup)
    
    def test_mixed_compound_commands(self):
        """Test subshell containing brace group ({ echo mixed; })."""
        test_input = "({ echo mixed; })"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 2  # One subshell, one brace group
        
        # Check that we have both types
        types = [type(c).__name__ for c in compounds]
        assert 'SubshellGroup' in types
        assert 'BraceGroup' in types
    
    def test_compound_command_in_pipeline(self):
        """Test compound commands as pipeline components."""
        test_input = "echo start | (cat; echo middle) | echo end"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        
        subshell = compounds[0]
        assert isinstance(subshell, SubshellGroup)
        assert len(subshell.statements.statements) == 2  # cat; echo middle
    
    def test_compound_commands_parsing_basic(self):
        """Test that basic compound command syntax parses without errors."""
        test_cases = [
            "(echo test)",
            "{ echo test; }",
            "(ls -l)",
            "{ pwd; }",
            "(date; uptime)",
            "{ date; uptime; }"
        ]
        
        for test_input in test_cases:
            tokens = list(tokenize(test_input))
            # Should not raise an exception
            ast = self.parser.parse(tokens)
            assert ast is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])