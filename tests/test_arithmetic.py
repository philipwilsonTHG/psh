import pytest
from io import StringIO
from unittest.mock import patch
from psh.shell import Shell
from psh.arithmetic import (
    ArithTokenizer, ArithParser, ArithmeticEvaluator, 
    evaluate_arithmetic, ArithmeticError
)


class TestArithmeticTokenizer:
    """Test arithmetic expression tokenizer"""
    
    def test_basic_numbers(self):
        tokenizer = ArithTokenizer("42")
        tokens = tokenizer.tokenize()
        assert len(tokens) == 2  # number + EOF
        assert tokens[0].value == 42
    
    def test_hex_numbers(self):
        tokenizer = ArithTokenizer("0xFF")
        tokens = tokenizer.tokenize()
        assert tokens[0].value == 255
        
        tokenizer = ArithTokenizer("0x10")
        tokens = tokenizer.tokenize()
        assert tokens[0].value == 16
    
    def test_octal_numbers(self):
        tokenizer = ArithTokenizer("010")
        tokens = tokenizer.tokenize()
        assert tokens[0].value == 8
        
        tokenizer = ArithTokenizer("077")
        tokens = tokenizer.tokenize()
        assert tokens[0].value == 63
    
    def test_basic_operators(self):
        tokenizer = ArithTokenizer("1 + 2 * 3")
        tokens = tokenizer.tokenize()
        values = [t.value for t in tokens[:-1]]  # Exclude EOF
        assert values == [1, '+', 2, '*', 3]
    
    def test_comparison_operators(self):
        tokenizer = ArithTokenizer("a < b && c >= d")
        tokens = tokenizer.tokenize()
        values = [t.value for t in tokens[:-1]]
        assert values == ['a', '<', 'b', '&&', 'c', '>=', 'd']
    
    def test_assignment_operators(self):
        tokenizer = ArithTokenizer("x = 5, x += 3")
        tokens = tokenizer.tokenize()
        values = [t.value for t in tokens[:-1]]
        assert values == ['x', '=', 5, ',', 'x', '+=', 3]
    
    def test_increment_decrement(self):
        tokenizer = ArithTokenizer("++x + y--")
        tokens = tokenizer.tokenize()
        values = [t.value for t in tokens[:-1]]
        assert values == ['++', 'x', '+', 'y', '--']


class TestArithmeticParser:
    """Test arithmetic expression parser"""
    
    def test_simple_expression(self):
        tokenizer = ArithTokenizer("2 + 3")
        tokens = tokenizer.tokenize()
        parser = ArithParser(tokens)
        ast = parser.parse()
        assert ast is not None
    
    def test_precedence(self):
        # Test that multiplication has higher precedence than addition
        tokenizer = ArithTokenizer("2 + 3 * 4")
        tokens = tokenizer.tokenize()
        parser = ArithParser(tokens)
        ast = parser.parse()
        # Should parse as 2 + (3 * 4), not (2 + 3) * 4
        assert ast.op.name == 'PLUS'
        assert ast.right.op.name == 'MULTIPLY'
    
    def test_parentheses(self):
        tokenizer = ArithTokenizer("(2 + 3) * 4")
        tokens = tokenizer.tokenize()
        parser = ArithParser(tokens)
        ast = parser.parse()
        # Should parse as (2 + 3) * 4
        assert ast.op.name == 'MULTIPLY'
        assert ast.left.op.name == 'PLUS'
    
    def test_ternary_operator(self):
        tokenizer = ArithTokenizer("x > 0 ? x : -x")
        tokens = tokenizer.tokenize()
        parser = ArithParser(tokens)
        ast = parser.parse()
        assert hasattr(ast, 'condition')
        assert hasattr(ast, 'true_expr')
        assert hasattr(ast, 'false_expr')


class TestArithmeticEvaluator:
    """Test arithmetic expression evaluator"""
    
    def setup_method(self):
        self.shell = Shell()
    
    def test_basic_arithmetic(self):
        assert evaluate_arithmetic("2 + 2", self.shell) == 4
        assert evaluate_arithmetic("10 - 3", self.shell) == 7
        assert evaluate_arithmetic("4 * 5", self.shell) == 20
        assert evaluate_arithmetic("20 / 4", self.shell) == 5
        assert evaluate_arithmetic("17 % 5", self.shell) == 2
        assert evaluate_arithmetic("2 ** 8", self.shell) == 256
    
    def test_precedence_evaluation(self):
        assert evaluate_arithmetic("2 + 3 * 4", self.shell) == 14
        assert evaluate_arithmetic("(2 + 3) * 4", self.shell) == 20
        assert evaluate_arithmetic("2 * 3 + 4", self.shell) == 10
        assert evaluate_arithmetic("2 * (3 + 4)", self.shell) == 14
    
    def test_comparison_operators(self):
        assert evaluate_arithmetic("5 > 3", self.shell) == 1
        assert evaluate_arithmetic("3 > 5", self.shell) == 0
        assert evaluate_arithmetic("5 >= 5", self.shell) == 1
        assert evaluate_arithmetic("5 < 3", self.shell) == 0
        assert evaluate_arithmetic("3 <= 3", self.shell) == 1
        assert evaluate_arithmetic("5 == 5", self.shell) == 1
        assert evaluate_arithmetic("5 != 3", self.shell) == 1
    
    def test_logical_operators(self):
        assert evaluate_arithmetic("1 && 1", self.shell) == 1
        assert evaluate_arithmetic("1 && 0", self.shell) == 0
        assert evaluate_arithmetic("0 || 1", self.shell) == 1
        assert evaluate_arithmetic("0 || 0", self.shell) == 0
        assert evaluate_arithmetic("!0", self.shell) == 1
        assert evaluate_arithmetic("!5", self.shell) == 0
    
    def test_bitwise_operators(self):
        assert evaluate_arithmetic("5 & 3", self.shell) == 1  # 101 & 011 = 001
        assert evaluate_arithmetic("5 | 3", self.shell) == 7  # 101 | 011 = 111
        assert evaluate_arithmetic("5 ^ 3", self.shell) == 6  # 101 ^ 011 = 110
        assert evaluate_arithmetic("~0", self.shell) == -1  # Bash uses 32-bit signed integers
        assert evaluate_arithmetic("~5", self.shell) == -6  # Bash behavior: ~5 = -6
        assert evaluate_arithmetic("4 << 2", self.shell) == 16
        assert evaluate_arithmetic("16 >> 2", self.shell) == 4
    
    def test_variable_expansion(self):
        self.shell.state.set_variable('x', '10')
        assert evaluate_arithmetic("x", self.shell) == 10
        assert evaluate_arithmetic("x + 5", self.shell) == 15
        assert evaluate_arithmetic("x * 2", self.shell) == 20
    
    def test_variable_assignment(self):
        evaluate_arithmetic("x = 10", self.shell)
        assert self.shell.state.get_variable('x') == '10'
        
        evaluate_arithmetic("x += 5", self.shell)
        assert self.shell.state.get_variable('x') == '15'
        
        evaluate_arithmetic("x *= 2", self.shell)
        assert self.shell.state.get_variable('x') == '30'
    
    def test_increment_decrement(self):
        self.shell.state.set_variable('x', '5')
        
        # Pre-increment
        assert evaluate_arithmetic("++x", self.shell) == 6
        assert self.shell.state.get_variable('x') == '6'
        
        # Post-increment
        assert evaluate_arithmetic("x++", self.shell) == 6
        assert self.shell.state.get_variable('x') == '7'
        
        # Pre-decrement
        assert evaluate_arithmetic("--x", self.shell) == 6
        assert self.shell.state.get_variable('x') == '6'
        
        # Post-decrement
        assert evaluate_arithmetic("x--", self.shell) == 6
        assert self.shell.state.get_variable('x') == '5'
    
    def test_ternary_operator(self):
        assert evaluate_arithmetic("1 ? 10 : 20", self.shell) == 10
        assert evaluate_arithmetic("0 ? 10 : 20", self.shell) == 20
        
        self.shell.state.set_variable('x', '5')
        assert evaluate_arithmetic("x > 0 ? x : -x", self.shell) == 5
        
        self.shell.state.set_variable('x', '-3')
        assert evaluate_arithmetic("x > 0 ? x : -x", self.shell) == 3
    
    def test_comma_operator(self):
        # Comma operator evaluates both but returns rightmost
        assert evaluate_arithmetic("3, 5", self.shell) == 5
        
        # With side effects
        evaluate_arithmetic("x = 10, y = 20", self.shell)
        assert self.shell.state.get_variable('x') == '10'
        assert self.shell.state.get_variable('y') == '20'
        
        assert evaluate_arithmetic("x = 5, x + 10", self.shell) == 15
    
    def test_complex_expressions(self):
        # Fibonacci-like calculation
        self.shell.state.set_variable('a', '1')
        self.shell.state.set_variable('b', '1')
        result = evaluate_arithmetic("c = a + b, a = b, b = c, c", self.shell)
        assert result == 2
        assert self.shell.state.get_variable('a') == '1'
        assert self.shell.state.get_variable('b') == '2'
        assert self.shell.state.get_variable('c') == '2'
    
    def test_division_by_zero(self):
        with pytest.raises(ArithmeticError, match="Division by zero"):
            evaluate_arithmetic("5 / 0", self.shell)
        
        with pytest.raises(ArithmeticError, match="Division by zero"):
            evaluate_arithmetic("5 % 0", self.shell)
    
    def test_empty_expression(self):
        # Empty expression evaluates to 0
        assert evaluate_arithmetic("", self.shell) == 0
    
    def test_non_numeric_variables(self):
        # Non-numeric strings evaluate to 0
        self.shell.state.set_variable('text', 'hello')
        assert evaluate_arithmetic("text", self.shell) == 0
        assert evaluate_arithmetic("text + 5", self.shell) == 5


class TestArithmeticIntegration:
    """Test arithmetic expansion integration with shell"""
    
    def setup_method(self):
        self.shell = Shell()
    
    def test_basic_arithmetic_expansion(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((2 + 2))")
            assert mock_stdout.getvalue().strip() == "4"
    
    def test_arithmetic_with_variables(self):
        self.shell.run_command("x=10")
        self.shell.run_command("y=3")
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((x + y))")
            assert mock_stdout.getvalue().strip() == "13"
    
    def test_arithmetic_assignment(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((x = 5 * 4))")
            assert mock_stdout.getvalue().strip() == "20"
        
        assert self.shell.state.get_variable('x') == '20'
    
    def test_nested_arithmetic(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $(( (2 + 3) * (4 + 5) ))")
            assert mock_stdout.getvalue().strip() == "45"
    
    def test_arithmetic_in_conditionals(self):
        # Test arithmetic in if statements
        result = self.shell.run_command("if [ $((5 > 3)) -eq 1 ]; then echo yes; fi")
        assert result == 0
    
    def test_multiple_arithmetic_expansions(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((2 + 2)) plus $((3 * 3)) equals $((4 + 9))")
            assert mock_stdout.getvalue().strip() == "4 plus 9 equals 13"
    
    def test_arithmetic_with_hex(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((0xFF))")
            assert mock_stdout.getvalue().strip() == "255"
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((0x10 + 0x20))")
            assert mock_stdout.getvalue().strip() == "48"
    
    def test_arithmetic_with_octal(self):
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((010))")
            assert mock_stdout.getvalue().strip() == "8"
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((010 + 020))")
            assert mock_stdout.getvalue().strip() == "24"
    
    def test_arithmetic_errors(self):
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                self.shell.run_command("echo $((5 / 0))")
                assert "arithmetic error" in mock_stderr.getvalue()
                assert mock_stdout.getvalue().strip() == "0"
    
    def test_arithmetic_side_effects(self):
        # Test that arithmetic assignments have side effects
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.shell.run_command("echo $((x = 10, y = x + 5, x * y))")
            assert mock_stdout.getvalue().strip() == "150"  # 10 * 15
        
        assert self.shell.state.get_variable('x') == '10'
        assert self.shell.state.get_variable('y') == '15'