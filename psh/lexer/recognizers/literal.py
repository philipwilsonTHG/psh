"""Literal token recognizer for strings, numbers, and identifiers."""

from typing import Optional, Tuple, Set
from .base import ContextualRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType
from ..unicode_support import is_identifier_start, is_identifier_char, is_whitespace


class LiteralRecognizer(ContextualRecognizer):
    """Recognizes literal tokens: strings, numbers, identifiers."""
    
    # Characters that can terminate a word
    WORD_TERMINATORS = {
        ' ', '\t', '\n', '\r', '\f', '\v',  # Whitespace
        '|', '&', ';', '(', ')', '{', '}',       # Operators
        '<', '>', '!', '=', '+',                 # More operators  
        '$', '`', "'",  '"',                     # Special characters
    }
    
    @property
    def priority(self) -> int:
        """Medium priority for literals."""
        return 70
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position might be a literal."""
        if pos >= len(input_text):
            return False
        
        char = input_text[pos]
        
        # Skip whitespace and operators (handled by other recognizers)
        if char in self.WORD_TERMINATORS:
            return False
        
        # Skip quotes and expansions (handled by quote/expansion parsers)
        if char in ['$', '`', "'", '"']:
            return False
        
        # If we get here, it might be a literal
        return True
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize literal tokens."""
        if not self.can_recognize(input_text, pos, context):
            return None
        
        # Read until we hit a word terminator
        start_pos = pos
        value = ""
        
        while pos < len(input_text):
            char = input_text[pos]
            
            # Check for word terminators
            if self._is_word_terminator(char, context):
                # Special case: don't terminate on = if we just collected + for +=
                if char == '=' and value.endswith('+'):
                    # Include the = in +=
                    value += char
                    pos += 1
                    continue
                break
            
            # Check for quotes or expansions that would end the word
            if char in ['$', '`', "'", '"']:
                break
            
            # Check if # starts a comment (not part of word)
            if char == '#' and self._is_comment_start(input_text, pos, context):
                break
            
            # Handle escape sequences
            if char == '\\' and pos + 1 < len(input_text):
                # Include the escaped character
                value += char + input_text[pos + 1]
                pos += 2
                continue
            
            value += char
            pos += 1
        
        if not value:
            return None
        
        # Determine token type based on content
        token_type = self._classify_literal(value, context)
        
        token = Token(
            token_type,
            value,
            start_pos,
            pos
        )
        
        return token, pos
    
    def _is_comment_start(self, input_text: str, pos: int, context: LexerContext) -> bool:
        """Check if # at current position starts a comment."""
        if pos == 0:
            return True
        
        prev_char = input_text[pos - 1]
        
        # After whitespace
        if prev_char in [' ', '\t', '\n', '\r']:
            return True
        
        # After operators that can be followed by comments
        comment_preceding_ops = {'|', '&', ';', '(', '{'}
        if prev_char in comment_preceding_ops:
            return True
        
        return False
    
    def _is_word_terminator(self, char: str, context: LexerContext) -> bool:
        """Check if character terminates a word in current context."""
        # In arithmetic context, only semicolon and parentheses are terminators
        if context.arithmetic_depth > 0:
            # Only these characters terminate words in arithmetic
            if char in [';', '(', ')', '\n']:
                return True
            else:
                return False
        
        # Basic word terminators
        if char in self.WORD_TERMINATORS:
            return True
        
        # Context-specific terminators
        if context.bracket_depth > 0:
            # Inside [[ ]], some characters have special meaning
            if char in ['[', ']']:
                return True
        
        return False
    
    def _classify_literal(self, value: str, context: LexerContext) -> TokenType:
        """Classify a literal value into appropriate token type."""
        # Check if it's a number - for now, treat as WORD since NUMBER doesn't exist
        if self._is_number(value):
            return TokenType.WORD  # Could be TokenType.NUMBER if it existed
        
        # Check if it looks like a file descriptor (single digit)
        if len(value) == 1 and value.isdigit():
            # IO_NUMBER doesn't exist either, use WORD
            return TokenType.WORD
        
        # Check if it's a valid identifier
        if self._is_identifier(value):
            return TokenType.WORD
        
        # Default to word
        return TokenType.WORD
    
    def _is_number(self, value: str) -> bool:
        """Check if value is a number literal."""
        if not value:
            return False
        
        # Simple integer
        if value.isdigit():
            return True
        
        # Negative integer
        if value.startswith('-') and len(value) > 1 and value[1:].isdigit():
            return True
        
        # Hexadecimal (0x...)
        if (len(value) > 2 and 
            value.startswith('0x') and 
            all(c in '0123456789abcdefABCDEF' for c in value[2:])):
            return True
        
        # Octal (0...)
        if (len(value) > 1 and 
            value.startswith('0') and 
            all(c in '01234567' for c in value[1:])):
            return True
        
        return False
    
    def _is_identifier(self, value: str) -> bool:
        """Check if value is a valid identifier."""
        if not value:
            return False
        
        # Must start with valid identifier start character
        if not is_identifier_start(value[0]):
            return False
        
        # Rest must be valid identifier characters
        return all(is_identifier_char(c) for c in value[1:])
    
    def _contains_special_chars(self, value: str) -> bool:
        """Check if value contains shell special characters."""
        special_chars = {'*', '?', '[', ']', '{', '}', '~'}
        return any(c in special_chars for c in value)