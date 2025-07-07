"""Operator token recognizer."""

from typing import Dict, Optional, Tuple, Set
from .base import ContextualRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType
from ..position import Position


class OperatorRecognizer(ContextualRecognizer):
    """Recognizes shell operators with context awareness."""
    
    def __init__(self):
        super().__init__()
        self.config = None  # Will be set by ModularLexer
    
    # Operators organized by length (longest first for greedy matching)
    OPERATORS = {
        3: {
            '<<<': TokenType.HERE_STRING,
            '<<-': TokenType.HEREDOC_STRIP,
            '2>>': TokenType.REDIRECT_ERR_APPEND,
            ';;&': TokenType.AMP_SEMICOLON,
        },
        2: {
            '>>': TokenType.REDIRECT_APPEND,
            '<<': TokenType.HEREDOC,
            '&&': TokenType.AND_AND,
            '||': TokenType.OR_OR,
            '((': TokenType.DOUBLE_LPAREN,
            '))': TokenType.DOUBLE_RPAREN,
            '[[': TokenType.DOUBLE_LBRACKET,
            ']]': TokenType.DOUBLE_RBRACKET,
            '=~': TokenType.REGEX_MATCH,
            '==': TokenType.EQUAL,
            '!=': TokenType.NOT_EQUAL,
            ';;': TokenType.DOUBLE_SEMICOLON,
            ';&': TokenType.SEMICOLON_AMP,
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
    
    def _try_fd_duplication(self, input_text: str, pos: int) -> bool:
        """Check if position starts a file descriptor duplication pattern."""
        # Check for patterns: >&N, <&N, N>&M, N<&M
        remaining = input_text[pos:]
        
        # Check for >&N or <&N
        if len(remaining) >= 3 and remaining[0] in '><' and remaining[1] == '&':
            return remaining[2].isdigit() or remaining[2] == '-'
        
        # Check for N>&M or N<&M
        if pos > 0 and input_text[pos-1].isdigit():
            if len(remaining) >= 2 and remaining[0] in '><' and remaining[1] == '&':
                return True
                
        return False
    
    def _parse_fd_duplication(self, input_text: str, pos: int) -> Optional[Tuple[Token, int]]:
        """Parse file descriptor duplication operators."""
        start_pos = pos
        
        # Check if we have a leading digit (N>&M pattern)
        leading_digit = None
        if pos > 0 and input_text[pos-1].isdigit():
            # Need to backtrack to include the digit
            digit_start = pos - 1
            while digit_start > 0 and input_text[digit_start-1].isdigit():
                digit_start -= 1
            leading_digit = input_text[digit_start:pos]
            start_pos = digit_start
        
        # Now we're at > or <
        direction = input_text[pos]
        pos += 1
        
        # Must be followed by &
        if pos >= len(input_text) or input_text[pos] != '&':
            return None
        pos += 1
        
        # Get the target fd or '-'
        if pos >= len(input_text):
            return None
            
        if input_text[pos] == '-':
            target = '-'
            pos += 1
        elif input_text[pos].isdigit():
            target_start = pos
            while pos < len(input_text) and input_text[pos].isdigit():
                pos += 1
            target = input_text[target_start:pos]
        else:
            return None
        
        # Construct the full operator string
        op_string = input_text[start_pos:pos]
        
        # Create the appropriate token
        token_type = TokenType.WORD  # FD duplication is parsed as a WORD in PSH
        token = Token(token_type, op_string, start_pos, pos)
        
        return token, pos
    
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
        
        # Special handling for file descriptor duplication: >&N or N>&M
        if self._try_fd_duplication(input_text, pos):
            return self._parse_fd_duplication(input_text, pos)
        
        # Try longest operators first for greedy matching
        for length in sorted(self.OPERATORS.keys(), reverse=True):
            if pos + length <= len(input_text):
                candidate = input_text[pos:pos + length]
                
                if candidate in self.OPERATORS[length]:
                    # Check configuration to see if this operator is enabled
                    if not self._is_operator_enabled(candidate):
                        continue
                        
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
    
    def _is_operator_enabled(self, operator: str) -> bool:
        """Check if operator is enabled by configuration."""
        if not self.config:
            return True  # No config means all enabled
            
        # Check pipes
        if operator == '|' and not self.config.enable_pipes:
            return False
            
        # Check redirections
        if operator in ['<', '>', '>>', '<<', '<<<', '2>', '2>>'] and not self.config.enable_redirections:
            return False
            
        # Check background operator
        if operator == '&' and not self.config.enable_background:
            return False
            
        # Check logical operators
        if operator in ['&&', '||'] and not self.config.enable_logical_operators:
            return False
            
        return True
    
    def is_valid_in_context(
        self, 
        operator: str, 
        context: LexerContext
    ) -> bool:
        """Check if operator is valid in current context."""
        # Inside arithmetic context, some operators should not be recognized
        if context.arithmetic_depth > 0:
            # Inside ((...)), don't tokenize these as redirects/operators
            if operator in ['<', '>', '<<', '>>', ';&', ';;&']:
                return False
        
        # [[ and ]] have special context rules
        if operator == '[[':
            # [[ is only valid at command position
            return context.command_position
        
        elif operator == ']]':
            # ]] is only valid when we're inside [[ ]]
            return context.bracket_depth > 0
        
        elif operator in ['=~', '==', '!=']:
            # =~, ==, != are only operators inside [[ ]], otherwise they're words
            return context.bracket_depth > 0
        
        elif operator in ['<', '>']:
            # Inside [[ ]], < and > are comparison operators, not redirections
            if context.bracket_depth > 0:
                return False  # Don't recognize as redirect operators inside [[ ]]
            return True  # Outside [[ ]], they are normal redirections
        
        # Most operators are valid in any context
        return True
    
    def get_operator_type(self, operator: str) -> Optional[TokenType]:
        """Get the token type for a given operator string."""
        for length_dict in self.OPERATORS.values():
            if operator in length_dict:
                return length_dict[operator]
        return None