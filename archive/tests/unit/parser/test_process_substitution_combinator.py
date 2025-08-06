#!/usr/bin/env python3
"""Test process substitution support in parser combinator implementation."""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import ProcessSubstitution, Word, ExpansionPart


class TestProcessSubstitutionCombinator:
    """Test process substitution parsing in parser combinator."""
    
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
    
    def test_simple_input_process_substitution(self):
        """Test simple input process substitution <(...)."""
        test_input = "cat <(echo hello)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'echo hello'
    
    def test_simple_output_process_substitution(self):
        """Test simple output process substitution >(...)."""
        test_input = "tee >(cat > output.txt)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'out'
        assert ps.command == 'cat > output.txt'
    
    def test_multiple_input_process_substitutions(self):
        """Test multiple input process substitutions."""
        test_input = "diff <(sort file1) <(sort file2)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 2
        
        # Both should be input process substitutions
        for ps in process_subs:
            assert ps.direction == 'in'
        
        # Check specific commands
        commands = [ps.command for ps in process_subs]
        assert 'sort file1' in commands
        assert 'sort file2' in commands
    
    def test_multiple_output_process_substitutions(self):
        """Test multiple output process substitutions."""
        test_input = "command | tee >(grep ERROR > errors.log) >(grep WARN > warnings.log)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 2
        
        # Both should be output process substitutions
        for ps in process_subs:
            assert ps.direction == 'out'
        
        # Check specific commands
        commands = [ps.command for ps in process_subs]
        assert 'grep ERROR > errors.log' in commands
        assert 'grep WARN > warnings.log' in commands
    
    def test_mixed_process_substitutions(self):
        """Test mixed input and output process substitutions."""
        test_input = "comm -12 <(sort input) | tee >(wc -l > count.txt)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 2
        
        # Check directions
        directions = [ps.direction for ps in process_subs]
        assert 'in' in directions
        assert 'out' in directions
        
        # Check commands
        commands = [ps.command for ps in process_subs]
        assert 'sort input' in commands
        assert 'wc -l > count.txt' in commands
    
    def test_complex_process_substitution_commands(self):
        """Test process substitutions with complex internal commands."""
        test_input = "cat <(ls -la | grep '^d' | awk '{print $9}')"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == "ls -la | grep '^d' | awk '{print $9}'"
    
    def test_process_substitution_in_word_ast(self):
        """Test that process substitution is correctly embedded in Word AST."""
        test_input = "cat <(echo test)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        # Navigate to the command
        stmt = ast.statements[0]
        pipeline = stmt.pipelines[0]
        cmd = pipeline.commands[0]
        
        # Should have 2 words: "cat" and "<(echo test)"
        assert len(cmd.words) == 2
        
        # First word should be literal "cat"
        word1 = cmd.words[0]
        assert len(word1.parts) == 1
        assert word1.parts[0].text == 'cat'
        
        # Second word should contain process substitution
        word2 = cmd.words[1]
        assert len(word2.parts) == 1
        assert isinstance(word2.parts[0], ExpansionPart)
        assert isinstance(word2.parts[0].expansion, ProcessSubstitution)
        
        ps = word2.parts[0].expansion
        assert ps.direction == 'in'
        assert ps.command == 'echo test'
    
    def test_process_substitution_with_redirections(self):
        """Test process substitution alongside regular redirections."""
        test_input = "cat <(echo test) > output.txt"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'echo test'
        
        # Should also have a regular redirection
        stmt = ast.statements[0]
        pipeline = stmt.pipelines[0]
        cmd = pipeline.commands[0]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == '>'
    
    def test_tokenization_of_process_substitution(self):
        """Test that process substitution tokens are generated correctly."""
        test_input = "cat <(echo test) >(tee output)"
        
        tokens = list(tokenize(test_input))
        token_types = [t.type.name for t in tokens if t.type.name != 'EOF']
        token_values = [t.value for t in tokens if t.type.name != 'EOF']
        
        expected_types = ['WORD', 'PROCESS_SUB_IN', 'PROCESS_SUB_OUT']
        expected_values = ['cat', '<(echo test)', '>(tee output)']
        
        assert token_types == expected_types
        assert token_values == expected_values
    
    def test_empty_process_substitution(self):
        """Test process substitution with minimal command."""
        test_input = "cat <(true)"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        assert ps.command == 'true'
    
    def test_process_substitution_with_special_characters(self):
        """Test process substitution with special characters in command."""
        test_input = r"cat <(echo 'hello world' | sed 's/world/universe/')"
        
        tokens = list(tokenize(test_input))
        ast = self.parser.parse(tokens)
        
        process_subs = self.find_process_substitutions(ast)
        assert len(process_subs) == 1
        
        ps = process_subs[0]
        assert ps.direction == 'in'
        # The command should preserve the quotes and special characters
        assert "echo 'hello world'" in ps.command
        assert "sed 's/world/universe/'" in ps.command


if __name__ == "__main__":
    pytest.main([__file__, "-v"])