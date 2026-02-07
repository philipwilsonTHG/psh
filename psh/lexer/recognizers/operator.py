"""Operator token recognizer."""

from typing import Optional, Set, Tuple

from ...token_types import Token, TokenType
from ..state_context import LexerContext
from .base import ContextualRecognizer


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
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '<': TokenType.REDIRECT_IN,
            '>': TokenType.REDIRECT_OUT,
            '!': TokenType.EXCLAMATION,
            '\n': TokenType.NEWLINE,  # Special handling for newlines
        }
    }

    # Characters that can start operators
    OPERATOR_START_CHARS: Set[str] = {
        '<', '>', '&', '|', ';', '(', ')', '{', '}', '[', ']', '!', '=', '2', '\n',
        '0', '1', '3', '4', '5', '6', '7', '8', '9'  # All digits for file descriptor duplication
    }

    def _try_fd_duplication(self, input_text: str, pos: int) -> bool:
        """Check if position starts a file descriptor duplication pattern."""
        # Check for patterns: >&N, <&N, N>&M, N<&M
        remaining = input_text[pos:]

        # Check for >&N or <&N
        if len(remaining) >= 3 and remaining[0] in '><' and remaining[1] == '&':
            return remaining[2].isdigit() or remaining[2] == '-'

        # Check for N>&M or N<&M (where we're at the digit)
        if remaining and remaining[0].isdigit():
            # Look ahead to see if this is N>&M pattern
            i = 1
            while i < len(remaining) and remaining[i].isdigit():
                i += 1
            if i < len(remaining) - 1 and remaining[i] in '><' and remaining[i+1] == '&':
                return True

        # Check for N>&M or N<&M (where we're at the > or <)
        if pos > 0 and input_text[pos-1].isdigit():
            if len(remaining) >= 2 and remaining[0] in '><' and remaining[1] == '&':
                return True

        return False

    def _parse_fd_duplication(self, input_text: str, pos: int) -> Optional[Tuple[Token, int]]:
        """Parse file descriptor duplication operators."""
        start_pos = pos

        # Check if we're starting at a digit (N>&M pattern)
        if pos < len(input_text) and input_text[pos].isdigit():
            # Parse the leading digit(s)
            while pos < len(input_text) and input_text[pos].isdigit():
                pos += 1

            # Must be followed by > or <
            if pos >= len(input_text) or input_text[pos] not in '><':
                return None

            pos += 1

            # Must be followed by &
            if pos >= len(input_text) or input_text[pos] != '&':
                return None
            pos += 1

            # Get the target fd or '-'
            if pos >= len(input_text):
                return None

            if input_text[pos] == '-':
                pos += 1
            elif input_text[pos].isdigit():
                while pos < len(input_text) and input_text[pos].isdigit():
                    pos += 1
            else:
                return None

            # Construct the full operator string
            op_string = input_text[start_pos:pos]

            # Create the appropriate token - use REDIRECT_DUP for file descriptor duplication
            token_type = TokenType.REDIRECT_DUP
            token = Token(token_type, op_string, start_pos, pos)

            return token, pos

        # Check if we have a leading digit (N>&M pattern where we're at > or <)
        if pos > 0 and input_text[pos-1].isdigit():
            # Need to backtrack to include the digit
            digit_start = pos - 1
            while digit_start > 0 and input_text[digit_start-1].isdigit():
                digit_start -= 1
            start_pos = digit_start

        # Now we're at > or <
        if pos >= len(input_text) or input_text[pos] not in '><':
            return None

        pos += 1

        # Must be followed by &
        if pos >= len(input_text) or input_text[pos] != '&':
            return None
        pos += 1

        # Get the target fd or '-'
        if pos >= len(input_text):
            return None

        if input_text[pos] == '-':
            pos += 1
        elif input_text[pos].isdigit():
            while pos < len(input_text) and input_text[pos].isdigit():
                pos += 1
        else:
            return None

        # Construct the full operator string
        op_string = input_text[start_pos:pos]

        # Create the appropriate token - use REDIRECT_DUP for file descriptor duplication
        token_type = TokenType.REDIRECT_DUP
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
        # This MUST come before regular operator matching to handle "2>&1" correctly
        if self._try_fd_duplication(input_text, pos):
            result = self._parse_fd_duplication(input_text, pos)
            if result is not None:
                return result

        # Try longest operators first for greedy matching
        for length in sorted(self.OPERATORS.keys(), reverse=True):
            if pos + length <= len(input_text):
                candidate = input_text[pos:pos + length]

                if candidate in self.OPERATORS[length]:
                    # Extglob: don't match ! as EXCLAMATION when followed by (
                    if (candidate == '!' and self.config
                            and self.config.enable_extglob
                            and pos + 1 < len(input_text)
                            and input_text[pos + 1] == '('):
                        return None

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

        elif operator == '[':
            # [ should be an operator in these contexts:
            # 1. Test command: [ expression ] (at command position with whitespace before)
            # 2. Array assignments: arr[index]=value (at command position after identifier)
            #
            # [ should NOT be an operator (should be part of word) in these contexts:
            # 3. Glob patterns in arguments: echo [abc]* (not at command position)
            # 4. Glob patterns in filenames: echo file[12].txt (not at command position)

            if not context.command_position:
                # Not at command position - must be argument/glob pattern
                return False

            # At command position - could be test command or array assignment
            # For now, allow both - let the parser determine which one it is
            return True

        elif operator == ']':
            # ] is only an operator in specific contexts:
            # 1. At command position (for test command)
            # 2. Inside [[ ]] (for closing conditional)
            # Otherwise it's part of a word (e.g., glob patterns like [abc]*)
            if context.command_position:
                return True
            if context.bracket_depth > 0:
                return True
            return False

        elif operator in ['=~', '==', '!=']:
            # =~, ==, != are only operators inside [[ ]], otherwise they're words
            return context.bracket_depth > 0

        elif operator in ['<', '>']:
            # Inside [[ ]], < and > are comparison operators, not redirections
            if context.bracket_depth > 0:
                return False  # Don't recognize as redirect operators inside [[ ]]
            return True  # Outside [[ ]], they are normal redirections

        elif operator == '))':
            # )) is only valid as DOUBLE_RPAREN when closing an arithmetic
            # context like (( expr )). Outside arithmetic, )) should be
            # tokenized as two separate RPAREN tokens (e.g., nested subshells:
            # (echo "outer"; (echo "inner")) ).
            return context.arithmetic_depth > 0

        # Most operators are valid in any context
        return True

    def get_operator_type(self, operator: str) -> Optional[TokenType]:
        """Get the token type for a given operator string."""
        for length_dict in self.OPERATORS.values():
            if operator in length_dict:
                return length_dict[operator]
        return None
