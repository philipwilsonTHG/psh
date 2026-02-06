"""Comment token recognizer."""

from typing import Optional, Tuple
from .base import ContextualRecognizer
from ..state_context import LexerContext
from ...token_types import Token


class CommentRecognizer(ContextualRecognizer):
    """Recognizes shell comments."""
    
    @property
    def priority(self) -> int:
        """Medium priority for comments."""
        return 60
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position starts a comment."""
        if pos >= len(input_text):
            return False
        
        char = input_text[pos]
        
        # Comments start with #
        if char != '#':
            return False
        
        # Check if # is actually starting a comment (not part of a word)
        return self._is_comment_start(input_text, pos, context)
    
    def recognize(
        self,
        input_text: str,
        pos: int,
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Skip past comment, returning (None, new_pos)."""
        if not self.can_recognize(input_text, pos, context):
            return None

        # Advance past all characters until end of line
        while pos < len(input_text) and input_text[pos] != '\n':
            pos += 1

        # Return None token with new position to indicate skip
        return None, pos
    
    def _is_comment_start(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """
        Check if # at current position starts a comment.
        
        # starts a comment if:
        1. It's at the beginning of input
        2. It follows whitespace
        3. It follows certain operators (|, &, ;, etc.)
        """
        if pos == 0:
            return True
        
        prev_char = input_text[pos - 1]
        
        # After whitespace
        if prev_char in [' ', '\t', '\n', '\r']:
            return True
        
        # After operators/metacharacters that can precede comments
        comment_preceding_ops = {'|', '&', ';', '(', ')', '{', '}'}
        if prev_char in comment_preceding_ops:
            return True

        return False