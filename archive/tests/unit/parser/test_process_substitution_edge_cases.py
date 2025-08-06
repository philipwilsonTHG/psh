#!/usr/bin/env python3
"""Test edge cases and complex scenarios for process substitution in parser combinator."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import ProcessSubstitution


class TestProcessSubstitutionEdgeCases:
    """Test edge cases and complex scenarios for process substitution."""
    
    def setup_method(self):
        """Set up parser with Word AST nodes enabled."""
        self.parser = ParserCombinatorShellParser()
        self.parser.config.build_word_ast_nodes = True
    
    def find_process_substitutions(self, node, visited=None):
        """Recursively find ProcessSubstitution nodes in AST."""
        if visited is None:
            visited = set()
        
        # Avoid infinite recursion
        if id(node) in visited:
            return []
        visited.add(id(node))
        
        result = []
        
        if isinstance(node, ProcessSubstitution):
            result.append(node)
        
        if hasattr(node, '__dict__'):
            for attr_value in node.__dict__.values():
                if hasattr(attr_value, '__dict__'):
                    result.extend(self.find_process_substitutions(attr_value, visited))
                elif isinstance(attr_value, list):
                    for item in attr_value:
                        if hasattr(item, '__dict__'):
                            result.extend(self.find_process_substitutions(item, visited))
        
        return result
    
    def test_nested_process_substitutions(self):
        """Test nested process substitutions."""
        # This is a complex case - process substitution inside another
        test_input = "cat <(diff <(sort file1) <(sort file2))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        # Should find the outer process substitution
        # The inner ones are part of the command string
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'diff <(sort file1) <(sort file2)'
    
    def test_process_substitution_with_complex_redirection(self):
        """Test process substitution with complex redirection patterns."""
        test_input = "cat <(ls 2>/dev/null | sort) > output.txt"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'ls 2>/dev/null | sort'
    
    def test_process_substitution_in_conditional(self):
        """Test process substitution in conditional expressions."""
        test_input = "if diff <(sort file1) <(sort file2) >/dev/null; then echo same; fi"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 2
        
        for ps in process_subs:
            assert ps.direction == 'in'
        
        commands = [ps.command for ps in process_subs]
        assert 'sort file1' in commands
        assert 'sort file2' in commands
    
    def test_process_substitution_with_arithmetic(self):
        """Test process substitution with arithmetic expansion."""
        test_input = "cat <(seq 1 $((10+5)))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'seq 1 $((10+5))'
    
    def test_process_substitution_with_variables(self):
        """Test process substitution with variable expansion."""
        test_input = "cat <(echo $HOME $USER)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'echo $HOME $USER'
    
    def test_process_substitution_with_command_substitution(self):
        """Test process substitution containing command substitution."""
        test_input = "cat <(echo $(date))"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'echo $(date)'
    
    def test_process_substitution_with_backtick_command_substitution(self):
        """Test process substitution containing backtick command substitution."""
        test_input = "cat <(echo `date`)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'echo `date`'
    
    def test_process_substitution_in_background(self):
        """Test process substitution with background commands."""
        test_input = "cat <(sleep 1; echo done) &"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'sleep 1; echo done'
        
        # Check that the command is backgrounded
        stmt = ast.statements[0]
        pipeline = stmt.pipelines[0]
        cmd = pipeline.commands[0]
        assert cmd.background == True
    
    def test_process_substitution_with_quotes_in_command(self):
        """Test process substitution with quoted content in command."""
        test_input = '''cat <(echo "hello world" 'test string')'''
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == """echo "hello world" 'test string'"""
    
    def test_process_substitution_with_escaped_characters(self):
        """Test process substitution with escaped characters in command."""
        test_input = r"cat <(echo \( \) \< \>)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == r'echo \( \) \< \>'
    
    def test_multiple_process_substitutions_same_line(self):
        """Test multiple process substitutions in same complex command."""
        test_input = "paste <(cut -f1 data) <(cut -f2 data) | tee >(sort > sorted1) >(uniq > unique1)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 4
        
        # Count by direction
        input_subs = [ps for ps in process_subs if ps.direction == 'in']
        output_subs = [ps for ps in process_subs if ps.direction == 'out']
        
        assert len(input_subs) == 2
        assert len(output_subs) == 2
        
        # Check specific commands
        all_commands = [ps.command for ps in process_subs]
        assert 'cut -f1 data' in all_commands
        assert 'cut -f2 data' in all_commands
        assert 'sort > sorted1' in all_commands
        assert 'uniq > unique1' in all_commands
    
    def test_process_substitution_with_heredoc_in_command(self):
        """Test process substitution containing heredoc."""
        test_input = "cat <(cat <<EOF\nhello\nworld\nEOF\n)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        # The command should contain the heredoc syntax
        assert 'cat <<EOF' in ps.command
    
    def test_process_substitution_edge_whitespace(self):
        """Test process substitution with edge case whitespace."""
        test_input = "cat <( echo test )"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        # Should preserve the whitespace in the command
        assert ps.command == ' echo test '
    
    def test_process_substitution_minimal_command(self):
        """Test process substitution with minimal single character command."""
        test_input = "cat <(w)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'w'
    
    def test_process_substitution_with_function_call(self):
        """Test process substitution calling a shell function."""
        test_input = "cat <(my_function arg1 arg2)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'my_function arg1 arg2'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])