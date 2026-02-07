"""Keyword token recognizer."""

from typing import Optional, Tuple

from ...token_types import Token, TokenType
from ..constants import KEYWORDS
from ..state_context import LexerContext
from ..unicode_support import is_identifier_char, is_identifier_start
from .base import ContextualRecognizer


class KeywordRecognizer(ContextualRecognizer):
    """Recognizes shell keywords with context awareness."""

    # Keywords that require command position
    COMMAND_KEYWORDS = {
        'if', 'then', 'else', 'elif', 'fi',
        'for', 'while', 'until', 'do', 'done',
        'case', 'esac', 'select',
        'function', 'time', 'coproc',
        'declare', 'local', 'readonly', 'export',
        'unset', 'typeset'
    }

    # Keywords that have special context rules
    CONTEXTUAL_KEYWORDS = {
        'in': ['for', 'case', 'select'],  # 'in' after these keywords
        'esac': [';;', ';&', ';;&'],  # 'esac' after case patterns
    }

    @property
    def priority(self) -> int:
        """High priority for keywords, but lower than operators."""
        return 90

    def can_recognize(
        self,
        input_text: str,
        pos: int,
        context: LexerContext
    ) -> bool:
        """Check if current position might be a keyword."""
        if pos >= len(input_text):
            return False

        char = input_text[pos]

        # Keywords must start with identifier characters
        if not is_identifier_start(char):
            return False

        # Quick check: do we have a chance of matching a keyword?
        remaining = input_text[pos:]
        for keyword in KEYWORDS:
            if remaining.startswith(keyword):
                # Check if it's a complete word (not part of a larger identifier)
                end_pos = pos + len(keyword)
                if (end_pos >= len(input_text) or
                    not is_identifier_char(input_text[end_pos])):
                    return True

        return False

    def recognize(
        self,
        input_text: str,
        pos: int,
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize keywords with context awareness."""
        if not self.can_recognize(input_text, pos, context):
            return None

        # Find the longest matching keyword
        best_match = None
        best_length = 0

        for keyword in KEYWORDS:
            if (pos + len(keyword) <= len(input_text) and
                input_text[pos:pos + len(keyword)] == keyword):

                # Check if it's a complete word
                end_pos = pos + len(keyword)
                if (end_pos >= len(input_text) or
                    not is_identifier_char(input_text[end_pos])):

                    # Check if keyword is valid in current context
                    if self.is_valid_in_context(keyword, context):
                        if len(keyword) > best_length:
                            best_match = keyword
                            best_length = len(keyword)

        if best_match:
            # Convert keyword to token type
            token_type = getattr(TokenType, best_match.upper())
            token = Token(
                token_type,
                best_match,
                pos,
                pos + best_length
            )
            return token, pos + best_length

        return None

    def is_valid_in_context(
        self,
        keyword: str,
        context: LexerContext
    ) -> bool:
        """Check if keyword is valid in current context."""
        # Most keywords require command position
        if keyword in self.COMMAND_KEYWORDS:
            return context.command_position

        # Special contextual rules
        if keyword == 'in':
            # 'in' is valid after 'for variable', 'case expr', or 'select variable'
            return self._is_in_keyword_valid(context)

        elif keyword == 'esac':
            # 'esac' is valid after case pattern terminators or at command position
            return self._is_esac_keyword_valid(context)

        elif keyword == 'then':
            # 'then' can appear after 'if' or standalone
            return True

        elif keyword == 'else' or keyword == 'elif':
            # 'else'/'elif' can appear in if statements
            return True

        elif keyword == 'do':
            # 'do' can appear after 'for', 'while', 'until'
            return True

        elif keyword == 'done':
            # 'done' terminates loops
            return True

        elif keyword == 'fi':
            # 'fi' terminates if statements
            return True

        # Default: keyword is valid if we're at command position
        return context.command_position

    def _is_in_keyword_valid(self, context: LexerContext) -> bool:
        """Check if 'in' keyword is valid in current context."""
        # 'in' is valid as a keyword in these contexts:
        # 1. At command position (like any keyword)
        # 2. After 'for variable' (for loops)
        # 3. After 'case expression' (case statements)
        # 4. After 'select variable' (select statements)

        if context.command_position:
            return True

        # Check if we recently saw a control keyword that uses 'in'
        if context.recent_control_keyword in {'for', 'case', 'select'}:
            return True

        return False

    def _is_esac_keyword_valid(self, context: LexerContext) -> bool:
        """Check if 'esac' keyword is valid in current context."""
        # 'esac' can appear after case pattern terminators or at command position
        # Since we don't have access to previous tokens here, we'll allow it
        # and let the parser handle semantic validation
        return context.command_position

    def get_keyword_type(self, keyword: str) -> Optional[TokenType]:
        """Get the token type for a given keyword."""
        if keyword in KEYWORDS:
            return getattr(TokenType, keyword.upper())
        return None
