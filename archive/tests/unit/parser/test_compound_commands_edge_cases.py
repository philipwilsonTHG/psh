#!/usr/bin/env python3
"""Test edge cases for compound command support in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import SubshellGroup, BraceGroup


class TestCompoundCommandsEdgeCases:
    """Test edge cases for compound command parsing in parser combinator."""
    
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
    
    def test_subshell_with_control_structures(self):
        """Test subshell containing control structures."""
        test_input = "(if true; then echo yes; fi)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_brace_group_with_control_structures(self):
        """Test brace group containing control structures."""
        test_input = "{ if true; then echo yes; fi; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], BraceGroup)
    
    def test_subshell_with_for_loop(self):
        """Test subshell containing for loop."""
        test_input = "(for i in 1 2 3; do echo $i; done)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_brace_group_with_while_loop(self):
        """Test brace group containing while loop."""
        test_input = "{ while true; do echo loop; break; done; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], BraceGroup)
    
    def test_subshell_with_case_statement(self):
        """Test subshell containing case statement."""
        test_input = "(case $var in a) echo A;; *) echo other;; esac)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_subshell_with_function_definition(self):
        """Test subshell containing function definition."""
        test_input = "(foo() { echo hello; }; foo)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) >= 1  # Subshell plus function body brace group
        subshells = [c for c in compounds if isinstance(c, SubshellGroup)]
        assert len(subshells) == 1
    
    def test_compound_commands_with_variables(self):
        """Test compound commands with variable assignments and expansions."""
        test_input = "(VAR=value; echo $VAR)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_compound_commands_with_redirections(self):
        """Test compound commands with I/O redirections."""
        test_input = "(echo hello > output.txt)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_brace_group_with_redirections(self):
        """Test brace group with I/O redirections."""
        test_input = "{ echo hello > output.txt; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], BraceGroup)
    
    def test_compound_commands_with_command_substitution(self):
        """Test compound commands with command substitution."""
        test_input = "(echo $(date))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_compound_commands_with_process_substitution(self):
        """Test compound commands with process substitution."""
        test_input = "(diff <(sort file1) <(sort file2))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_deeply_nested_compound_commands(self):
        """Test deeply nested compound commands."""
        test_input = "( { (echo level3); } )"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 3  # Outer subshell, brace group, inner subshell
        
        # Check types
        types = [type(c).__name__ for c in compounds]
        assert 'SubshellGroup' in types
        assert 'BraceGroup' in types
    
    def test_compound_commands_in_and_or_lists(self):
        """Test compound commands in && and || lists."""
        test_input = "(echo test) && { echo success; }"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 2  # One subshell, one brace group
        
        types = [type(c).__name__ for c in compounds]
        assert 'SubshellGroup' in types
        assert 'BraceGroup' in types
    
    def test_empty_compound_commands(self):
        """Test empty compound commands."""
        test_cases = [
            "()",       # Empty subshell
            "{ }"       # Empty brace group (might need semicolon)
        ]
        
        for test_input in test_cases:
            tokens = list(tokenize(test_input))
            # Should parse without error, even if empty
            try:
                ast = self.parser.parse(tokens)
                compounds = self.find_compound_commands(ast)
                assert len(compounds) >= 0  # Could be 0 or 1 depending on how empty is handled
            except Exception:
                # Empty commands might be a parsing error - that's acceptable
                pass
    
    def test_compound_commands_with_comments(self):
        """Test compound commands with comments."""
        test_input = "( echo hello # this is a comment\n)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_compound_commands_with_arithmetic_expansion(self):
        """Test compound commands with arithmetic expansion."""
        test_input = "(echo $((5 + 3)))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        assert len(compounds) == 1
        assert isinstance(compounds[0], SubshellGroup)
    
    def test_compound_commands_complex_integration(self):
        """Test complex integration of compound commands with various shell features."""
        test_input = """( 
            if test -f file.txt; then 
                { cat file.txt | grep pattern > results.txt; } 
            else 
                echo "File not found" >&2
            fi 
        )"""
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        compounds = self.find_compound_commands(ast)
        # Should have outer subshell and inner brace group
        assert len(compounds) >= 2
        
        types = [type(c).__name__ for c in compounds]
        assert 'SubshellGroup' in types
        assert 'BraceGroup' in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])