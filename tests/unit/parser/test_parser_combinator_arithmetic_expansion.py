"""Test arithmetic expansion parsing in the parser combinator.

This module tests that the parser combinator correctly parses arithmetic
expansion syntax $((expression)) into proper AST nodes with Word structures
containing ExpansionPart and ArithmeticExpansion nodes.
"""
import pytest
from psh.lexer import tokenize
from psh.parser.implementations.parser_combinator_example import ParserCombinatorShellParser
from psh.parser.config import ParserConfig
from psh.ast_nodes import (
    Word, LiteralPart, ExpansionPart,
    ArithmeticExpansion, VariableExpansion,
    SimpleCommand, CommandList, AndOrList, Pipeline
)


class TestParserCombinatorArithmeticExpansion:
    """Test arithmetic expansion parsing in parser combinator."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ParserCombinatorShellParser()
        self.parser.config = ParserConfig(build_word_ast_nodes=True)
    
    def parse(self, command: str):
        """Parse a command string."""
        tokens = tokenize(command)
        return self.parser.parse(tokens)
    
    def get_simple_command(self, ast) -> SimpleCommand:
        """Extract simple command from AST."""
        cmd_list = ast
        if isinstance(ast, CommandList):
            cmd_list = ast.statements[0]
        if isinstance(cmd_list, AndOrList):
            pipeline = cmd_list.pipelines[0]
            if isinstance(pipeline, Pipeline):
                return pipeline.commands[0]
        return None
    
    # Basic arithmetic expansion tests
    
    def test_simple_arithmetic_expansion(self):
        """Test: echo $((1 + 2))"""
        cmd = self.get_simple_command(self.parse("echo $((1 + 2))"))
        assert cmd is not None
        assert len(cmd.words) == 2
        
        # First word is 'echo'
        assert cmd.words[0].parts[0].text == "echo"
        
        # Second word is arithmetic expansion
        word = cmd.words[1]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "1 + 2"
        assert str(word) == "$((1 + 2))"
    
    def test_arithmetic_expansion_no_spaces(self):
        """Test: echo $((1+2))"""
        cmd = self.get_simple_command(self.parse("echo $((1+2))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "1+2"
        assert str(word) == "$((1+2))"
    
    def test_arithmetic_with_variables(self):
        """Test: echo $((x + y))"""
        cmd = self.get_simple_command(self.parse("echo $((x + y))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x + y"
        assert str(word) == "$((x + y))"
    
    def test_arithmetic_with_variable_expansion(self):
        """Test: echo $(($x + $y))"""
        cmd = self.get_simple_command(self.parse("echo $(($x + $y))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "$x + $y"
        assert str(word) == "$(($x + $y))"
    
    # Complex arithmetic expressions
    
    def test_arithmetic_multiplication(self):
        """Test: echo $((3 * 4))"""
        cmd = self.get_simple_command(self.parse("echo $((3 * 4))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "3 * 4"
    
    def test_arithmetic_division(self):
        """Test: echo $((10 / 2))"""
        cmd = self.get_simple_command(self.parse("echo $((10 / 2))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "10 / 2"
    
    def test_arithmetic_modulo(self):
        """Test: echo $((10 % 3))"""
        cmd = self.get_simple_command(self.parse("echo $((10 % 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "10 % 3"
    
    def test_arithmetic_parentheses(self):
        """Test: echo $(((2 + 3) * 4))"""
        cmd = self.get_simple_command(self.parse("echo $(((2 + 3) * 4))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "(2 + 3) * 4"
    
    # Bitwise operations
    
    def test_arithmetic_bitwise_and(self):
        """Test: echo $((5 & 3))"""
        cmd = self.get_simple_command(self.parse("echo $((5 & 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 & 3"
    
    def test_arithmetic_bitwise_or(self):
        """Test: echo $((5 | 3))"""
        cmd = self.get_simple_command(self.parse("echo $((5 | 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 | 3"
    
    def test_arithmetic_bitwise_xor(self):
        """Test: echo $((5 ^ 3))"""
        cmd = self.get_simple_command(self.parse("echo $((5 ^ 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 ^ 3"
    
    def test_arithmetic_bitwise_not(self):
        """Test: echo $((~5))"""
        cmd = self.get_simple_command(self.parse("echo $((~5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "~5"
    
    def test_arithmetic_shift_left(self):
        """Test: echo $((1 << 3))"""
        cmd = self.get_simple_command(self.parse("echo $((1 << 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "1 << 3"
    
    def test_arithmetic_shift_right(self):
        """Test: echo $((8 >> 2))"""
        cmd = self.get_simple_command(self.parse("echo $((8 >> 2))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "8 >> 2"
    
    # Comparison operations
    
    def test_arithmetic_less_than(self):
        """Test: echo $((3 < 5))"""
        cmd = self.get_simple_command(self.parse("echo $((3 < 5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "3 < 5"
    
    def test_arithmetic_greater_than(self):
        """Test: echo $((5 > 3))"""
        cmd = self.get_simple_command(self.parse("echo $((5 > 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 > 3"
    
    def test_arithmetic_less_equal(self):
        """Test: echo $((3 <= 5))"""
        cmd = self.get_simple_command(self.parse("echo $((3 <= 5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "3 <= 5"
    
    def test_arithmetic_greater_equal(self):
        """Test: echo $((5 >= 3))"""
        cmd = self.get_simple_command(self.parse("echo $((5 >= 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "5 >= 3"
    
    def test_arithmetic_equality(self):
        """Test: echo $((3 == 3))"""
        cmd = self.get_simple_command(self.parse("echo $((3 == 3))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "3 == 3"
    
    def test_arithmetic_inequality(self):
        """Test: echo $((3 != 5))"""
        cmd = self.get_simple_command(self.parse("echo $((3 != 5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "3 != 5"
    
    # Logical operations
    
    def test_arithmetic_logical_and(self):
        """Test: echo $((1 && 1))"""
        cmd = self.get_simple_command(self.parse("echo $((1 && 1))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "1 && 1"
    
    def test_arithmetic_logical_or(self):
        """Test: echo $((0 || 1))"""
        cmd = self.get_simple_command(self.parse("echo $((0 || 1))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "0 || 1"
    
    def test_arithmetic_logical_not(self):
        """Test: echo $((!0))"""
        cmd = self.get_simple_command(self.parse("echo $((!0))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "!0"
    
    # Unary operations
    
    def test_arithmetic_unary_minus(self):
        """Test: echo $((-5))"""
        cmd = self.get_simple_command(self.parse("echo $((-5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "-5"
    
    def test_arithmetic_unary_plus(self):
        """Test: echo $((+5))"""
        cmd = self.get_simple_command(self.parse("echo $((+5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "+5"
    
    # Increment/decrement operations
    
    def test_arithmetic_pre_increment(self):
        """Test: echo $((++x))"""
        cmd = self.get_simple_command(self.parse("echo $((++x))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "++x"
    
    def test_arithmetic_post_increment(self):
        """Test: echo $((x++))"""
        cmd = self.get_simple_command(self.parse("echo $((x++))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x++"
    
    def test_arithmetic_pre_decrement(self):
        """Test: echo $((--x))"""
        cmd = self.get_simple_command(self.parse("echo $((--x))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "--x"
    
    def test_arithmetic_post_decrement(self):
        """Test: echo $((x--))"""
        cmd = self.get_simple_command(self.parse("echo $((x--))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x--"
    
    # Assignment operations
    
    def test_arithmetic_assignment(self):
        """Test: echo $((x = 5))"""
        cmd = self.get_simple_command(self.parse("echo $((x = 5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x = 5"
    
    def test_arithmetic_compound_assignment(self):
        """Test: echo $((x += 5))"""
        cmd = self.get_simple_command(self.parse("echo $((x += 5))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x += 5"
    
    # Ternary operator
    
    def test_arithmetic_ternary(self):
        """Test: echo $((x > 0 ? x : -x))"""
        cmd = self.get_simple_command(self.parse("echo $((x > 0 ? x : -x))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x > 0 ? x : -x"
    
    # Complex expressions
    
    def test_arithmetic_complex_expression(self):
        """Test: echo $((x * (y + 3) - z / 2))"""
        cmd = self.get_simple_command(self.parse("echo $((x * (y + 3) - z / 2))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x * (y + 3) - z / 2"
    
    def test_arithmetic_comma_operator(self):
        """Test: echo $((x = 5, y = 10, x + y))"""
        cmd = self.get_simple_command(self.parse("echo $((x = 5, y = 10, x + y))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "x = 5, y = 10, x + y"
    
    # Mixed words with arithmetic expansion
    
    def test_arithmetic_in_mixed_word(self):
        """Test: echo prefix$((1+2))suffix
        
        Note: The current lexer tokenizes this as separate words.
        This test documents the current behavior.
        """
        cmd = self.get_simple_command(self.parse("echo prefix$((1+2))suffix"))
        assert cmd is not None
        assert len(cmd.words) == 4  # Currently parsed as 4 separate words
        
        # Word 1: echo
        assert cmd.words[0].parts[0].text == "echo"
        
        # Word 2: prefix
        assert cmd.words[1].parts[0].text == "prefix"
        
        # Word 3: arithmetic expansion
        word = cmd.words[2]
        assert len(word.parts) == 1
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "1+2"
        
        # Word 4: suffix
        assert cmd.words[3].parts[0].text == "suffix"
    
    def test_multiple_arithmetic_expansions(self):
        """Test: echo $((x + 1)) $((y * 2))"""
        cmd = self.get_simple_command(self.parse("echo $((x + 1)) $((y * 2))"))
        assert cmd is not None
        assert len(cmd.words) == 3
        
        # First arithmetic expansion
        word1 = cmd.words[1]
        assert isinstance(word1.parts[0], ExpansionPart)
        assert isinstance(word1.parts[0].expansion, ArithmeticExpansion)
        assert word1.parts[0].expansion.expression == "x + 1"
        
        # Second arithmetic expansion
        word2 = cmd.words[2]
        assert isinstance(word2.parts[0], ExpansionPart)
        assert isinstance(word2.parts[0].expansion, ArithmeticExpansion)
        assert word2.parts[0].expansion.expression == "y * 2"
    
    def test_arithmetic_with_other_expansions(self):
        """Test: echo $((x + 1)) $USER ${HOME}"""
        cmd = self.get_simple_command(self.parse("echo $((x + 1)) $USER ${HOME}"))
        assert cmd is not None
        assert len(cmd.words) == 4
        
        # Arithmetic expansion
        word1 = cmd.words[1]
        assert isinstance(word1.parts[0], ExpansionPart)
        assert isinstance(word1.parts[0].expansion, ArithmeticExpansion)
        
        # Variable expansion
        word2 = cmd.words[2]
        assert isinstance(word2.parts[0], ExpansionPart)
        assert isinstance(word2.parts[0].expansion, VariableExpansion)
        
        # Parameter expansion
        word3 = cmd.words[3]
        assert isinstance(word3.parts[0], ExpansionPart)
        # Note: ${HOME} is parsed as parameter expansion
        assert str(word3) == "${HOME}"
    
    # Special cases
    
    def test_arithmetic_empty_expression(self):
        """Test: echo $(())"""
        cmd = self.get_simple_command(self.parse("echo $(())"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == ""
    
    def test_arithmetic_whitespace_only(self):
        """Test: echo $((   ))"""
        cmd = self.get_simple_command(self.parse("echo $((   ))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "   "
    
    def test_arithmetic_with_newlines(self):
        """Test multiline arithmetic expression."""
        # Note: The lexer should handle this, but let's test what happens
        cmd = self.get_simple_command(self.parse("echo $((1 +\n2))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        # The expression should preserve the newline
        assert word.parts[0].expansion.expression == "1 +\n2"
    
    # Edge cases with special characters
    
    def test_arithmetic_with_dollar_signs(self):
        """Test: echo $(($$ + 1))"""
        cmd = self.get_simple_command(self.parse("echo $(($$ + 1))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "$$ + 1"
    
    def test_arithmetic_octal_numbers(self):
        """Test: echo $((010 + 1))"""
        cmd = self.get_simple_command(self.parse("echo $((010 + 1))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "010 + 1"
    
    def test_arithmetic_hex_numbers(self):
        """Test: echo $((0x10 + 1))"""
        cmd = self.get_simple_command(self.parse("echo $((0x10 + 1))"))
        assert cmd is not None
        
        word = cmd.words[1]
        assert isinstance(word.parts[0], ExpansionPart)
        assert isinstance(word.parts[0].expansion, ArithmeticExpansion)
        assert word.parts[0].expansion.expression == "0x10 + 1"