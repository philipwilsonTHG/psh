"""Assignment pattern recognizer for enhanced lexer."""

import re
from typing import Optional

from ...token_enhanced import SemanticType
from ...token_types import Token, TokenType
from ..context_recognizer import ContextAwareRecognizer
from ..enhanced_context import EnhancedLexerContext


class AssignmentRecognizer(ContextAwareRecognizer):
    """Recognizes assignment patterns in command position."""

    def __init__(self):
        # High priority to catch assignments before word recognizer
        super().__init__(priority=90)

        # Patterns for different assignment types
        self.simple_assignment = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)=')
        self.array_assignment = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[([^\]]*)\]=')
        self.compound_assignment = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)([+\-*/%&|^]|<<|>>)?=')

        # Assignment operator mapping
        self.assignment_operators = {
            '=': TokenType.ASSIGNMENT_WORD,
            '+=': TokenType.PLUS_ASSIGN,
            '-=': TokenType.MINUS_ASSIGN,
            '*=': TokenType.MULT_ASSIGN,
            '/=': TokenType.DIV_ASSIGN,
            '%=': TokenType.MOD_ASSIGN,
            '&=': TokenType.AND_ASSIGN,
            '|=': TokenType.OR_ASSIGN,
            '^=': TokenType.XOR_ASSIGN,
            '<<=': TokenType.LSHIFT_ASSIGN,
            '>>=': TokenType.RSHIFT_ASSIGN,
        }

    def can_recognize(
        self,
        char: str,
        position: int,
        context: EnhancedLexerContext
    ) -> bool:
        """Check if this recognizer can handle the current position."""
        # Only recognize assignments in command position
        if not context.should_expect_assignment():
            return False

        # Must start with identifier character
        return char.isalpha() or char == '_'

    def recognize_basic(
        self,
        text: str,
        position: int,
        context: EnhancedLexerContext
    ) -> Optional[Token]:
        """Recognize assignment patterns."""
        remaining = text[position:]

        # Try array assignment first (most specific)
        match = self.array_assignment.match(remaining)
        if match:
            var_name = match.group(1)
            index_expr = match.group(2)
            full_match = match.group(0)

            # Validate array assignment
            if self._validate_array_assignment(var_name, index_expr):
                return Token(
                    type=TokenType.ARRAY_ASSIGNMENT_WORD,
                    value=full_match,
                    position=position,
                    end_position=position + len(full_match)
                )

        # Try compound assignment
        match = self.compound_assignment.match(remaining)
        if match:
            var_name = match.group(1)
            operator = match.group(2) or ''
            full_operator = operator + '='
            full_match = match.group(0)

            # Validate variable name
            if self._validate_variable_name(var_name):
                # Determine specific token type
                token_type = self.assignment_operators.get(
                    full_operator,
                    TokenType.ASSIGNMENT_WORD
                )

                return Token(
                    type=token_type,
                    value=full_match,
                    position=position,
                    end_position=position + len(full_match)
                )

        return None

    def _enhance_token(
        self,
        token: Token,
        context: EnhancedLexerContext
    ):
        """Add assignment-specific enhancements."""
        super()._enhance_token(token, context)

        # All assignment tokens get assignment semantic type
        if token.type in {TokenType.ASSIGNMENT_WORD, TokenType.ARRAY_ASSIGNMENT_WORD} or \
           token.type in self.assignment_operators.values():
            token.set_semantic_type(SemanticType.ASSIGNMENT)

        # Parse assignment components for metadata
        if token.type == TokenType.ASSIGNMENT_WORD:
            self._parse_simple_assignment(token)
        elif token.type == TokenType.ARRAY_ASSIGNMENT_WORD:
            self._parse_array_assignment(token)
        elif token.type in self.assignment_operators.values():
            self._parse_compound_assignment(token)

    def _parse_simple_assignment(self, token: Token):
        """Parse simple assignment (VAR=value) components."""
        if '=' not in token.value:
            return

        var_part, value_part = token.value.split('=', 1)

        # Add metadata about assignment components
        # This could be used later for semantic analysis
        if not hasattr(token, 'assignment_info'):
            token.assignment_info = {}

        token.assignment_info['variable'] = var_part
        token.assignment_info['value'] = value_part
        token.assignment_info['type'] = 'simple'

    def _parse_array_assignment(self, token: Token):
        """Parse array assignment (arr[index]=value) components."""
        match = self.array_assignment.match(token.value)
        if not match:
            return

        var_name = match.group(1)
        index_expr = match.group(2)
        # Extract value part (everything after =)
        value_part = token.value[match.end():]

        if not hasattr(token, 'assignment_info'):
            token.assignment_info = {}

        token.assignment_info['variable'] = var_name
        token.assignment_info['index'] = index_expr
        token.assignment_info['value'] = value_part
        token.assignment_info['type'] = 'array'

    def _parse_compound_assignment(self, token: Token):
        """Parse compound assignment (VAR+=value) components."""
        match = self.compound_assignment.match(token.value)
        if not match:
            return

        var_name = match.group(1)
        operator = match.group(2) or ''
        # Extract value part
        equals_pos = token.value.find('=')
        value_part = token.value[equals_pos + 1:] if equals_pos != -1 else ''

        if not hasattr(token, 'assignment_info'):
            token.assignment_info = {}

        token.assignment_info['variable'] = var_name
        token.assignment_info['operator'] = operator
        token.assignment_info['value'] = value_part
        token.assignment_info['type'] = 'compound'

    def _validate_variable_name(self, name: str) -> bool:
        """Validate that a variable name is valid."""
        if not name:
            return False

        # Must start with letter or underscore
        if not (name[0].isalpha() or name[0] == '_'):
            return False

        # Must contain only alphanumeric characters and underscores
        return all(c.isalnum() or c == '_' for c in name)

    def _validate_array_assignment(self, var_name: str, index_expr: str) -> bool:
        """Validate array assignment components."""
        # Validate variable name
        if not self._validate_variable_name(var_name):
            return False

        # Index can be empty (for appending), or contain various expressions
        # We'll be permissive here and let the parser/executor handle complex validation
        return True

    def get_assignment_type(self, token_value: str) -> str:
        """Get the type of assignment from token value."""
        if self.array_assignment.match(token_value):
            return 'array'
        elif self.compound_assignment.match(token_value):
            match = self.compound_assignment.match(token_value)
            if match and match.group(2):
                return 'compound'
        return 'simple'

    def extract_variable_name(self, token_value: str) -> Optional[str]:
        """Extract variable name from assignment token."""
        # Try array assignment first
        match = self.array_assignment.match(token_value)
        if match:
            return match.group(1)

        # Try compound assignment
        match = self.compound_assignment.match(token_value)
        if match:
            return match.group(1)

        # Try simple assignment
        match = self.simple_assignment.match(token_value)
        if match:
            return match.group(1)

        return None

    def extract_assignment_value(self, token_value: str) -> Optional[str]:
        """Extract assignment value from token."""
        equals_pos = token_value.find('=')
        if equals_pos == -1:
            return None

        return token_value[equals_pos + 1:]
