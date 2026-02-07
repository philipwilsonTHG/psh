"""Arithmetic content recognizer for ((...)) contexts."""

from typing import Optional, Tuple

from ...token_types import Token, TokenType
from ..state_context import LexerContext
from .base import ContextualRecognizer


class ArithmeticContentRecognizer(ContextualRecognizer):
    """Recognizes content inside arithmetic ((...)) contexts."""

    @property
    def priority(self) -> int:
        """Very high priority when in arithmetic context."""
        return 200  # Higher than any other recognizer

    def can_recognize(
        self,
        input_text: str,
        pos: int,
        context: LexerContext
    ) -> bool:
        """Only active inside arithmetic contexts."""
        # We're in arithmetic context if arithmetic_depth > 0
        return context.arithmetic_depth > 0 and pos < len(input_text)

    def recognize(
        self,
        input_text: str,
        pos: int,
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize arithmetic content until we find the closing ))."""
        if not self.can_recognize(input_text, pos, context):
            return None

        start_pos = pos
        content_parts = []
        paren_count = 0

        while pos < len(input_text):
            char = input_text[pos]
            next_char = input_text[pos + 1] if pos + 1 < len(input_text) else ''

            # Check for )) that would close the arithmetic expression
            if char == ')' and next_char == ')' and paren_count == 0:
                # We've found the end of the arithmetic expression
                break

            # Track nested parentheses
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1

            # Add character to content
            content_parts.append(char)
            pos += 1

        if pos == start_pos:
            # No content found
            return None

        # Create a single WORD token with the arithmetic content
        content = ''.join(content_parts)
        token = Token(
            TokenType.WORD,
            content.strip(),
            start_pos,
            pos
        )

        return token, pos
