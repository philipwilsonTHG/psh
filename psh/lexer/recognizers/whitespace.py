"""Whitespace token recognizer."""

from typing import Optional, Tuple
from .base import TokenRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType
from ..unicode_support import is_whitespace


class WhitespaceRecognizer(TokenRecognizer):
    """Recognizes whitespace tokens."""
    
    @property
    def priority(self) -> int:
        """Low priority for whitespace."""
        return 30
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position is whitespace."""
        if pos >= len(input_text):
            return False
        
        char = input_text[pos]
        
        # Skip newlines (handled by operator recognizer)
        if char == '\n':
            return False
        
        # Check for whitespace (excluding newlines)
        return is_whitespace(char, posix_mode=context.posix_mode)
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize whitespace sequences."""
        if not self.can_recognize(input_text, pos, context):
            return None
        
        start_pos = pos
        whitespace = ""
        
        # Consume all consecutive whitespace (except newlines)
        while pos < len(input_text):
            char = input_text[pos]
            
            # Stop at newlines (handled separately)
            if char == '\n':
                break
            
            # Stop at non-whitespace
            if not is_whitespace(char, posix_mode=context.posix_mode):
                break
            
            whitespace += char
            pos += 1
        
        if not whitespace:
            return None
        
        # In most shell contexts, whitespace is not tokenized as separate tokens
        # Instead, it's skipped. However, we create a token for completeness
        # and let the lexer decide whether to emit it.
        token = Token(
            TokenType.WHITESPACE if hasattr(TokenType, 'WHITESPACE') else TokenType.WORD,
            whitespace,
            start_pos,
            pos
        )
        
        # Return None to indicate whitespace should be skipped
        # The lexer will handle advancing the position
        return None