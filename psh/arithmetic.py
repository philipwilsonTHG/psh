"""Arithmetic expression evaluator for shell arithmetic expansion $((...))"""

import builtins
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Union


class ArithTokenType(Enum):
    """Token types for arithmetic expressions"""
    NUMBER = auto()
    IDENTIFIER = auto()

    # Arithmetic operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    POWER = auto()

    # Comparison operators
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NE = auto()

    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()

    # Bitwise operators
    BIT_AND = auto()
    BIT_OR = auto()
    BIT_XOR = auto()
    BIT_NOT = auto()
    LSHIFT = auto()
    RSHIFT = auto()

    # Assignment operators
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    MULTIPLY_ASSIGN = auto()
    DIVIDE_ASSIGN = auto()
    MODULO_ASSIGN = auto()

    # Other operators
    QUESTION = auto()
    COLON = auto()
    COMMA = auto()

    # Increment/decrement
    INCREMENT = auto()
    DECREMENT = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()

    # End of input
    EOF = auto()


@dataclass
class ArithToken:
    """Arithmetic token with type and value"""
    type: ArithTokenType
    value: Union[str, int]
    position: int


class ArithTokenizer:
    """Tokenizer for arithmetic expressions"""

    def __init__(self, expr: str):
        self.expr = expr
        self.position = 0
        self.tokens: List[ArithToken] = []

    def current_char(self) -> Optional[str]:
        if self.position >= len(self.expr):
            return None
        return self.expr[self.position]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        pos = self.position + offset
        if pos >= len(self.expr):
            return None
        return self.expr[pos]

    def advance(self) -> None:
        self.position += 1

    def skip_whitespace(self) -> None:
        while self.current_char() and self.current_char() in ' \t\n':
            self.advance()

    def read_number(self) -> int:
        """Read a number (decimal, octal, hex, or base#number)"""
        start_pos = self.position

        # First, check for base#number notation
        # We need to look ahead to see if there's a # after initial digits
        saved_pos = self.position
        base_str = ''
        while self.current_char() and self.current_char().isdigit():
            base_str += self.current_char()
            self.advance()

        if self.current_char() == '#' and base_str:
            # This is base#number notation
            self.advance()  # Skip #
            base = int(base_str)
            if base < 2 or base > 36:
                raise SyntaxError(f"Invalid base {base} at position {start_pos}")

            # Read the number in the specified base
            num_str = ''
            while self.current_char():
                char = self.current_char().upper()
                if char.isdigit():
                    digit_val = ord(char) - ord('0')
                elif char.isalpha() and char <= 'Z':
                    digit_val = ord(char) - ord('A') + 10
                else:
                    break

                # Check if digit is valid for this base
                if digit_val >= base:
                    break

                num_str += self.current_char()
                self.advance()

            if not num_str:
                raise SyntaxError(f"Invalid base {base} number at position {start_pos}")

            return int(num_str, base)

        # Not base#number, restore position and check other formats
        self.position = saved_pos

        # Check for hex (0x or 0X)
        if self.current_char() == '0' and self.peek_char() and self.peek_char().lower() == 'x':
            self.advance()  # Skip 0
            self.advance()  # Skip x
            hex_digits = ''
            while self.current_char() and self.current_char() in '0123456789abcdefABCDEF':
                hex_digits += self.current_char()
                self.advance()
            if not hex_digits:
                raise SyntaxError(f"Invalid hex number at position {start_pos}")
            return int(hex_digits, 16)

        # Check for octal (leading 0)
        if self.current_char() == '0' and self.peek_char() and self.peek_char().isdigit():
            octal_digits = ''
            while self.current_char() and self.current_char() in '01234567':
                octal_digits += self.current_char()
                self.advance()
            # If we hit 8 or 9, it's an invalid octal digit (bash errors here)
            if self.current_char() and self.current_char() in '89':
                # Read the rest of the digits so the error message shows the full token
                while self.current_char() and self.current_char().isdigit():
                    octal_digits += self.current_char()
                    self.advance()
                raise SyntaxError(
                    f"0{octal_digits}: value too great for base (error token is \"0{octal_digits}\")"
                )
            return int(octal_digits, 8) if octal_digits else 0

        # Regular decimal
        return self.read_decimal()

    def read_decimal(self) -> int:
        """Read a decimal number"""
        num_str = ''
        while self.current_char() and self.current_char().isdigit():
            num_str += self.current_char()
            self.advance()
        return int(num_str) if num_str else 0

    def read_identifier(self) -> str:
        """Read an identifier (variable name)"""
        ident = ''
        # First character must be letter or underscore
        if self.current_char() and (self.current_char().isalpha() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()
            # Rest can be letters, digits, or underscore
            while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
                ident += self.current_char()
                self.advance()
        return ident

    def tokenize(self) -> List[ArithToken]:
        """Tokenize the arithmetic expression"""
        while self.position < len(self.expr):
            self.skip_whitespace()

            if self.position >= len(self.expr):
                break

            start_pos = self.position
            char = self.current_char()

            # Numbers
            if char and char.isdigit():
                value = self.read_number()
                self.tokens.append(ArithToken(ArithTokenType.NUMBER, value, start_pos))

            # Identifiers
            elif char and (char.isalpha() or char == '_'):
                ident = self.read_identifier()
                self.tokens.append(ArithToken(ArithTokenType.IDENTIFIER, ident, start_pos))

            # Operators and delimiters
            elif char == '+':
                if self.peek_char() == '+':
                    self.tokens.append(ArithToken(ArithTokenType.INCREMENT, '++', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.PLUS_ASSIGN, '+=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.PLUS, '+', start_pos))
                    self.advance()

            elif char == '-':
                if self.peek_char() == '-':
                    self.tokens.append(ArithToken(ArithTokenType.DECREMENT, '--', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.MINUS_ASSIGN, '-=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.MINUS, '-', start_pos))
                    self.advance()

            elif char == '*':
                if self.peek_char() == '*':
                    self.tokens.append(ArithToken(ArithTokenType.POWER, '**', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.MULTIPLY_ASSIGN, '*=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.MULTIPLY, '*', start_pos))
                    self.advance()

            elif char == '/':
                if self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.DIVIDE_ASSIGN, '/=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.DIVIDE, '/', start_pos))
                    self.advance()

            elif char == '%':
                if self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.MODULO_ASSIGN, '%=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.MODULO, '%', start_pos))
                    self.advance()

            elif char == '<':
                if self.peek_char() == '<':
                    self.tokens.append(ArithToken(ArithTokenType.LSHIFT, '<<', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.LE, '<=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.LT, '<', start_pos))
                    self.advance()

            elif char == '>':
                if self.peek_char() == '>':
                    self.tokens.append(ArithToken(ArithTokenType.RSHIFT, '>>', start_pos))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.GE, '>=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.GT, '>', start_pos))
                    self.advance()

            elif char == '=':
                if self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.EQ, '==', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.ASSIGN, '=', start_pos))
                    self.advance()

            elif char == '!':
                if self.peek_char() == '=':
                    self.tokens.append(ArithToken(ArithTokenType.NE, '!=', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.NOT, '!', start_pos))
                    self.advance()

            elif char == '&':
                if self.peek_char() == '&':
                    self.tokens.append(ArithToken(ArithTokenType.AND, '&&', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.BIT_AND, '&', start_pos))
                    self.advance()

            elif char == '|':
                if self.peek_char() == '|':
                    self.tokens.append(ArithToken(ArithTokenType.OR, '||', start_pos))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(ArithToken(ArithTokenType.BIT_OR, '|', start_pos))
                    self.advance()

            elif char == '^':
                self.tokens.append(ArithToken(ArithTokenType.BIT_XOR, '^', start_pos))
                self.advance()

            elif char == '~':
                self.tokens.append(ArithToken(ArithTokenType.BIT_NOT, '~', start_pos))
                self.advance()

            elif char == '?':
                self.tokens.append(ArithToken(ArithTokenType.QUESTION, '?', start_pos))
                self.advance()

            elif char == ':':
                self.tokens.append(ArithToken(ArithTokenType.COLON, ':', start_pos))
                self.advance()

            elif char == ',':
                self.tokens.append(ArithToken(ArithTokenType.COMMA, ',', start_pos))
                self.advance()

            elif char == '(':
                self.tokens.append(ArithToken(ArithTokenType.LPAREN, '(', start_pos))
                self.advance()

            elif char == ')':
                self.tokens.append(ArithToken(ArithTokenType.RPAREN, ')', start_pos))
                self.advance()

            else:
                raise SyntaxError(f"Unexpected character '{char}' at position {start_pos}")

        # Add EOF token
        self.tokens.append(ArithToken(ArithTokenType.EOF, '', self.position))
        return self.tokens


# AST Node classes
@dataclass
class ArithNode:
    """Base class for arithmetic AST nodes"""
    pass


@dataclass
class NumberNode(ArithNode):
    """Numeric literal"""
    value: int


@dataclass
class VariableNode(ArithNode):
    """Variable reference"""
    name: str


@dataclass
class UnaryOpNode(ArithNode):
    """Unary operation"""
    op: ArithTokenType
    operand: ArithNode


@dataclass
class BinaryOpNode(ArithNode):
    """Binary operation"""
    op: ArithTokenType
    left: ArithNode
    right: ArithNode


@dataclass
class TernaryNode(ArithNode):
    """Ternary conditional (?:)"""
    condition: ArithNode
    true_expr: ArithNode
    false_expr: ArithNode


@dataclass
class AssignmentNode(ArithNode):
    """Assignment operation"""
    var_name: str
    op: ArithTokenType
    value: ArithNode


@dataclass
class PreIncrementNode(ArithNode):
    """Pre-increment/decrement (++var, --var)"""
    var_name: str
    is_increment: bool


@dataclass
class PostIncrementNode(ArithNode):
    """Post-increment/decrement (var++, var--)"""
    var_name: str
    is_increment: bool


class ArithParser:
    """Recursive descent parser for arithmetic expressions"""

    def __init__(self, tokens: List[ArithToken]):
        self.tokens = tokens
        self.current = 0

    def peek(self) -> ArithToken:
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]  # Return EOF

    def advance(self) -> ArithToken:
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token

    def expect(self, token_type: ArithTokenType) -> ArithToken:
        token = self.peek()
        if token.type != token_type:
            raise SyntaxError(f"Expected {token_type.name}, got {token.type.name} at position {token.position}")
        return self.advance()

    def match(self, *token_types: ArithTokenType) -> bool:
        return self.peek().type in token_types

    def parse(self) -> ArithNode:
        """Parse the arithmetic expression"""
        if self.peek().type == ArithTokenType.EOF:
            # Empty expression evaluates to 0
            return NumberNode(0)

        expr = self.parse_comma()
        if self.peek().type != ArithTokenType.EOF:
            raise SyntaxError(f"Unexpected token after expression: {self.peek().value}")
        return expr

    def parse_comma(self) -> ArithNode:
        """Parse comma operator (lowest precedence)"""
        left = self.parse_ternary()

        while self.match(ArithTokenType.COMMA):
            self.advance()
            # In comma expressions, we evaluate left but return right
            right = self.parse_ternary()
            left = BinaryOpNode(ArithTokenType.COMMA, left, right)

        return left

    def parse_ternary(self) -> ArithNode:
        """Parse ternary conditional (?:)"""
        condition = self.parse_logical_or()

        if self.match(ArithTokenType.QUESTION):
            self.advance()
            true_expr = self.parse_ternary()
            self.expect(ArithTokenType.COLON)
            false_expr = self.parse_ternary()
            return TernaryNode(condition, true_expr, false_expr)

        return condition

    def parse_logical_or(self) -> ArithNode:
        """Parse logical OR (||)"""
        left = self.parse_logical_and()

        while self.match(ArithTokenType.OR):
            op = self.advance().type
            right = self.parse_logical_and()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_logical_and(self) -> ArithNode:
        """Parse logical AND (&&)"""
        left = self.parse_bitwise_or()

        while self.match(ArithTokenType.AND):
            op = self.advance().type
            right = self.parse_bitwise_or()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_bitwise_or(self) -> ArithNode:
        """Parse bitwise OR (|)"""
        left = self.parse_bitwise_xor()

        while self.match(ArithTokenType.BIT_OR):
            op = self.advance().type
            right = self.parse_bitwise_xor()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_bitwise_xor(self) -> ArithNode:
        """Parse bitwise XOR (^)"""
        left = self.parse_bitwise_and()

        while self.match(ArithTokenType.BIT_XOR):
            op = self.advance().type
            right = self.parse_bitwise_and()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_bitwise_and(self) -> ArithNode:
        """Parse bitwise AND (&)"""
        left = self.parse_equality()

        while self.match(ArithTokenType.BIT_AND):
            op = self.advance().type
            right = self.parse_equality()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_equality(self) -> ArithNode:
        """Parse equality operators (==, !=)"""
        left = self.parse_relational()

        while self.match(ArithTokenType.EQ, ArithTokenType.NE):
            op = self.advance().type
            right = self.parse_relational()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_relational(self) -> ArithNode:
        """Parse relational operators (<, >, <=, >=)"""
        left = self.parse_shift()

        while self.match(ArithTokenType.LT, ArithTokenType.GT,
                         ArithTokenType.LE, ArithTokenType.GE):
            op = self.advance().type
            right = self.parse_shift()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_shift(self) -> ArithNode:
        """Parse bit shift operators (<<, >>)"""
        left = self.parse_additive()

        while self.match(ArithTokenType.LSHIFT, ArithTokenType.RSHIFT):
            op = self.advance().type
            right = self.parse_additive()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_additive(self) -> ArithNode:
        """Parse addition and subtraction (+, -)"""
        left = self.parse_multiplicative()

        while self.match(ArithTokenType.PLUS, ArithTokenType.MINUS):
            op = self.advance().type
            right = self.parse_multiplicative()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_multiplicative(self) -> ArithNode:
        """Parse multiplication, division, and modulo (*, /, %)"""
        left = self.parse_power()

        while self.match(ArithTokenType.MULTIPLY, ArithTokenType.DIVIDE,
                         ArithTokenType.MODULO):
            op = self.advance().type
            right = self.parse_power()
            left = BinaryOpNode(op, left, right)

        return left

    def parse_power(self) -> ArithNode:
        """Parse exponentiation (**)"""
        left = self.parse_unary()

        # Right associative
        if self.match(ArithTokenType.POWER):
            op = self.advance().type
            right = self.parse_power()  # Right associative recursion
            return BinaryOpNode(op, left, right)

        return left

    def parse_unary(self) -> ArithNode:
        """Parse unary operators"""
        # Unary operators: +, -, !, ~, ++, --
        if self.match(ArithTokenType.PLUS, ArithTokenType.MINUS,
                     ArithTokenType.NOT, ArithTokenType.BIT_NOT):
            op = self.advance().type
            operand = self.parse_unary()
            return UnaryOpNode(op, operand)

        # Pre-increment/decrement
        if self.match(ArithTokenType.INCREMENT, ArithTokenType.DECREMENT):
            op = self.advance()
            if not self.match(ArithTokenType.IDENTIFIER):
                raise SyntaxError(f"Expected identifier after {op.value}")
            var_name = self.advance().value
            return PreIncrementNode(var_name, op.type == ArithTokenType.INCREMENT)

        return self.parse_postfix()

    def parse_postfix(self) -> ArithNode:
        """Parse postfix operators"""
        expr = self.parse_primary()

        # Post-increment/decrement
        if isinstance(expr, VariableNode) and self.match(ArithTokenType.INCREMENT, ArithTokenType.DECREMENT):
            op = self.advance()
            return PostIncrementNode(expr.name, op.type == ArithTokenType.INCREMENT)

        return expr

    def parse_primary(self) -> ArithNode:
        """Parse primary expressions"""
        # Numbers
        if self.match(ArithTokenType.NUMBER):
            return NumberNode(self.advance().value)

        # Variables (possibly with assignment)
        if self.match(ArithTokenType.IDENTIFIER):
            var_token = self.advance()
            var_name = var_token.value

            # Check for assignment operators
            if self.match(ArithTokenType.ASSIGN, ArithTokenType.PLUS_ASSIGN,
                         ArithTokenType.MINUS_ASSIGN, ArithTokenType.MULTIPLY_ASSIGN,
                         ArithTokenType.DIVIDE_ASSIGN, ArithTokenType.MODULO_ASSIGN):
                op = self.advance().type
                value = self.parse_ternary()  # Assignment is right-associative
                return AssignmentNode(var_name, op, value)

            return VariableNode(var_name)

        # Parenthesized expressions
        if self.match(ArithTokenType.LPAREN):
            self.advance()
            expr = self.parse_comma()  # Allow full expressions in parens
            self.expect(ArithTokenType.RPAREN)
            return expr

        raise SyntaxError(f"Unexpected token: {self.peek().value} at position {self.peek().position}")


class ArithmeticEvaluator:
    """Evaluate arithmetic AST nodes"""

    def __init__(self, shell):
        self.shell = shell

    def get_variable(self, name: str) -> int:
        """Get variable value, converting to integer"""
        # Use state's get_variable which handles scopes
        value = self.shell.state.get_variable(name, '0')

        # Handle empty string as 0
        if not value:
            return 0

        # Try to convert to integer
        try:
            return int(value)
        except ValueError:
            # Non-numeric strings evaluate to 0 in bash arithmetic
            return 0

    def set_variable(self, name: str, value: int) -> None:
        """Set variable value"""
        # Use state's set_variable which handles scopes
        # When in a function and assigning to a local variable,
        # this should update the local, not create a new global
        self.shell.state.set_variable(name, str(value))

    def evaluate(self, node: ArithNode) -> int:
        """Evaluate an arithmetic AST node"""
        if isinstance(node, NumberNode):
            return node.value

        elif isinstance(node, VariableNode):
            return self.get_variable(node.name)

        elif isinstance(node, UnaryOpNode):
            operand = self.evaluate(node.operand)

            if node.op == ArithTokenType.PLUS:
                return operand
            elif node.op == ArithTokenType.MINUS:
                return -operand
            elif node.op == ArithTokenType.NOT:
                return 0 if operand else 1
            elif node.op == ArithTokenType.BIT_NOT:
                # Bash uses 64-bit signed integers for bitwise operations.
                # Python has arbitrary precision, so mask to 64-bit and
                # convert to signed.
                result = ~operand & 0xFFFFFFFFFFFFFFFF
                if result & 0x8000000000000000:
                    result -= 0x10000000000000000
                return result

        elif isinstance(node, BinaryOpNode):
            # Special handling for short-circuit operators
            if node.op == ArithTokenType.AND:
                left = self.evaluate(node.left)
                if not left:
                    return 0
                return 1 if self.evaluate(node.right) else 0

            elif node.op == ArithTokenType.OR:
                left = self.evaluate(node.left)
                if left:
                    return 1
                return 1 if self.evaluate(node.right) else 0

            elif node.op == ArithTokenType.COMMA:
                # Evaluate left for side effects, return right
                self.evaluate(node.left)
                return self.evaluate(node.right)

            # Regular binary operators
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)

            if node.op == ArithTokenType.PLUS:
                return left + right
            elif node.op == ArithTokenType.MINUS:
                return left - right
            elif node.op == ArithTokenType.MULTIPLY:
                return left * right
            elif node.op == ArithTokenType.DIVIDE:
                if right == 0:
                    raise ShellArithmeticError("Division by zero")
                # Bash uses integer division
                return int(left / right)
            elif node.op == ArithTokenType.MODULO:
                if right == 0:
                    raise ShellArithmeticError("Division by zero")
                # C-style truncated remainder (sign matches dividend),
                # not Python's floored modulo (sign matches divisor).
                return left - int(left / right) * right
            elif node.op == ArithTokenType.POWER:
                if right < 0:
                    raise ShellArithmeticError("exponent less than 0")
                if right > 63:
                    # Cap exponent to prevent unbounded memory use
                    raise ShellArithmeticError("exponent too large")
                return left ** right

            # Comparison operators
            elif node.op == ArithTokenType.LT:
                return 1 if left < right else 0
            elif node.op == ArithTokenType.GT:
                return 1 if left > right else 0
            elif node.op == ArithTokenType.LE:
                return 1 if left <= right else 0
            elif node.op == ArithTokenType.GE:
                return 1 if left >= right else 0
            elif node.op == ArithTokenType.EQ:
                return 1 if left == right else 0
            elif node.op == ArithTokenType.NE:
                return 1 if left != right else 0

            # Bitwise operators
            elif node.op == ArithTokenType.BIT_AND:
                return left & right
            elif node.op == ArithTokenType.BIT_OR:
                return left | right
            elif node.op == ArithTokenType.BIT_XOR:
                return left ^ right
            elif node.op == ArithTokenType.LSHIFT:
                if right < 0:
                    raise ShellArithmeticError("negative shift count")
                # Bash/C wraps shift amount modulo 64
                return _to_signed64(left << (right & 63))
            elif node.op == ArithTokenType.RSHIFT:
                if right < 0:
                    raise ShellArithmeticError("negative shift count")
                return _to_signed64(left) >> (right & 63)

        elif isinstance(node, TernaryNode):
            condition = self.evaluate(node.condition)
            if condition:
                return self.evaluate(node.true_expr)
            else:
                return self.evaluate(node.false_expr)

        elif isinstance(node, AssignmentNode):
            value = self.evaluate(node.value)

            if node.op == ArithTokenType.ASSIGN:
                self.set_variable(node.var_name, value)
                return value

            # Compound assignments
            current = self.get_variable(node.var_name)

            if node.op == ArithTokenType.PLUS_ASSIGN:
                result = current + value
            elif node.op == ArithTokenType.MINUS_ASSIGN:
                result = current - value
            elif node.op == ArithTokenType.MULTIPLY_ASSIGN:
                result = current * value
            elif node.op == ArithTokenType.DIVIDE_ASSIGN:
                if value == 0:
                    raise ShellArithmeticError("Division by zero")
                result = int(current / value)
            elif node.op == ArithTokenType.MODULO_ASSIGN:
                if value == 0:
                    raise ShellArithmeticError("Division by zero")
                result = current - int(current / value) * value
            else:
                raise ValueError(f"Unknown assignment operator: {node.op}")

            self.set_variable(node.var_name, result)
            return result

        elif isinstance(node, PreIncrementNode):
            current = self.get_variable(node.var_name)
            new_value = current + 1 if node.is_increment else current - 1
            self.set_variable(node.var_name, new_value)
            return new_value

        elif isinstance(node, PostIncrementNode):
            current = self.get_variable(node.var_name)
            new_value = current + 1 if node.is_increment else current - 1
            self.set_variable(node.var_name, new_value)
            return current  # Return old value

        else:
            raise ValueError(f"Unknown node type: {type(node)}")


# Inherit from the Python builtin ArithmeticError so that callers that
# catch the builtin (without importing psh's version) still work.
class ShellArithmeticError(builtins.ArithmeticError):
    """Exception for arithmetic evaluation errors"""
    pass


# Keep the old name as an alias so that callers that import
# ``from psh.arithmetic import ArithmeticError`` continue to work.
ArithmeticError = ShellArithmeticError  # noqa: A001


def _to_signed64(value: int) -> int:
    """Wrap an arbitrary-precision integer into the signed 64-bit range."""
    value &= 0xFFFFFFFFFFFFFFFF
    if value & 0x8000000000000000:
        value -= 0x10000000000000000
    return value


def evaluate_arithmetic(expr: str, shell) -> int:
    """Evaluate an arithmetic expression with the given shell context"""
    try:
        # First, expand all shell variables and parameter expansions
        expanded_expr = shell.expansion_manager.expand_string_variables(expr)

        # Tokenize the expanded expression
        tokenizer = ArithTokenizer(expanded_expr)
        tokens = tokenizer.tokenize()

        # Parse
        parser = ArithParser(tokens)
        ast = parser.parse()

        # Evaluate
        evaluator = ArithmeticEvaluator(shell)
        return evaluator.evaluate(ast)

    except (SyntaxError, ShellArithmeticError) as e:
        raise ShellArithmeticError(str(e))
    except RecursionError:
        raise ShellArithmeticError("expression too deeply nested")
    except (ValueError, OverflowError, MemoryError) as e:
        raise ShellArithmeticError(str(e))
