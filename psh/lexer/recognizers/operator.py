"""Operator token recognizer."""

from typing import Dict, Optional, Tuple, Set
from .base import ContextualRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType
from ..position import Position


class OperatorRecognizer(ContextualRecognizer):
    """Recognizes shell operators with context awareness."""
    
    # Operators organized by length (longest first for greedy matching)
    OPERATORS = {
        3: {
            '<<<': TokenType.HERE_STRING,
            '<<-': TokenType.HEREDOC_STRIP,
            '2>>': TokenType.REDIRECT_ERR_APPEND,
        },
        2: {
            '>>': TokenType.REDIRECT_APPEND,
            '<<': TokenType.HEREDOC,
            '&&': TokenType.AND_AND,
            '||': TokenType.OR_OR,
            '((': TokenType.DOUBLE_LPAREN,
            '[[': TokenType.DOUBLE_LBRACKET,
            ']]': TokenType.DOUBLE_RBRACKET,
            '=~': TokenType.REGEX_MATCH,
            ';;': TokenType.DOUBLE_SEMICOLON,
            ';&': TokenType.SEMICOLON_AMP,
            '&;': TokenType.AMP_SEMICOLON,
            '2>': TokenType.REDIRECT_ERR,
        },
        1: {
            '|': TokenType.PIPE,
            '&': TokenType.AMPERSAND,
            ';': TokenType.SEMICOLON,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '<': TokenType.REDIRECT_IN,
            '>': TokenType.REDIRECT_OUT,
            '!': TokenType.EXCLAMATION,
            '\n': TokenType.NEWLINE,  # Special handling for newlines
        }
    }
    
    # Characters that can start operators
    OPERATOR_START_CHARS: Set[str] = {
        '<', '>', '&', '|', ';', '(', ')', '{', '}', '[', ']', '!', '=', '2', '\n'
    }
    
    @property
    def priority(self) -> int:
        """High priority for operators."""
        return 150
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position might be an operator."""
        if pos >= len(input_text):
            return False
        
        char = input_text[pos]
        
        # Quick check for operator start characters
        if char in self.OPERATOR_START_CHARS:
            return True
        
        # Special handling for newlines
        if char == '\n':
            return True
            
        return False
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize operators with context awareness."""
        if not self.can_recognize(input_text, pos, context):
            return None
        
        # Special handling for newlines
        if input_text[pos] == '\n':
            token = Token(
                TokenType.NEWLINE,
                '\n',
                pos,
                pos + 1
            )
            return token, pos + 1
        
        # Try longest operators first for greedy matching
        for length in sorted(self.OPERATORS.keys(), reverse=True):
            if pos + length <= len(input_text):
                candidate = input_text[pos:pos + length]
                
                if candidate in self.OPERATORS[length]:
                    # Check if operator is valid in current context
                    if self.is_valid_in_context(candidate, context):
                        token_type = self.OPERATORS[length][candidate]
                        token = Token(
                            token_type,
                            candidate,
                            pos,
                            pos + length
                        )
                        return token, pos + length
        
        return None
    
    def is_valid_in_context(
        self, 
        operator: str, 
        context: LexerContext
    ) -> bool:
        """Check if operator is valid in current context."""
        # [[ and ]] have special context rules
        if operator == '[[':
            # [[ is only valid at command position
            return context.command_position
        
        elif operator == ']]':
            # ]] is only valid when we're inside [[ ]]
            return context.bracket_depth > 0
        
        elif operator == '=~':
            # =~ is only an operator inside [[ ]], otherwise it's a word
            return context.bracket_depth > 0
        
        elif operator in ['<', '>']:
            # Inside [[ ]], < and > are comparison operators, not redirections
            # But we'll let the parser handle this distinction
            return True
        
        # Most operators are valid in any context
        return True
    
    def get_operator_type(self, operator: str) -> Optional[TokenType]:
        """Get the token type for a given operator string."""
        for length_dict in self.OPERATORS.values():
            if operator in length_dict:
                return length_dict[operator]
        return None