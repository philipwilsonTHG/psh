"""Bracket pairing tracker for enhanced lexer validation."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from ..token_enhanced import LexerError, LexerErrorType
from ..token_types import Token, TokenType


class BracketType(Enum):
    """Types of brackets to track."""
    PAREN = "paren"
    BRACE = "brace"
    BRACKET = "bracket"
    DOUBLE_PAREN = "double_paren"
    DOUBLE_BRACKET = "double_bracket"


@dataclass
class BracketPair:
    """Information about a bracket pair."""
    open_type: TokenType
    close_type: TokenType
    bracket_type: BracketType
    open_index: int
    close_index: Optional[int] = None
    context: Optional[str] = None  # e.g., "arithmetic", "test", "subshell"


@dataclass
class BracketValidationResult:
    """Result of bracket validation."""
    is_valid: bool
    errors: List[LexerError]
    warnings: List[LexerError]
    pairs: List[BracketPair]
    unmatched_opens: List[BracketPair]


class BracketTracker:
    """Tracks bracket pairing during tokenization."""

    # Mapping of opening to closing brackets
    BRACKET_PAIRS = {
        TokenType.LPAREN: (TokenType.RPAREN, BracketType.PAREN),
        TokenType.LBRACE: (TokenType.RBRACE, BracketType.BRACE),
        TokenType.LBRACKET: (TokenType.RBRACKET, BracketType.BRACKET),
        TokenType.DOUBLE_LPAREN: (TokenType.DOUBLE_RPAREN, BracketType.DOUBLE_PAREN),
        TokenType.DOUBLE_LBRACKET: (TokenType.DOUBLE_RBRACKET, BracketType.DOUBLE_BRACKET),
    }

    # Reverse mapping for closing brackets
    CLOSING_BRACKETS = {
        close: (open_type, bracket_type)
        for open_type, (close, bracket_type) in BRACKET_PAIRS.items()
    }

    # Context mapping for special constructs
    CONTEXT_MAPPING = {
        TokenType.DOUBLE_LPAREN: "arithmetic",
        TokenType.DOUBLE_LBRACKET: "test",
        TokenType.LPAREN: "subshell",
        TokenType.LBRACE: "brace_group",
        TokenType.LBRACKET: "array_index"
    }

    def __init__(self):
        self.stack: List[BracketPair] = []
        self.pairs: List[BracketPair] = []
        self.errors: List[LexerError] = []
        self.warnings: List[LexerError] = []

    def process_token(self, token: Token, index: int):
        """Process a token for bracket pairing."""
        if token.type in self.BRACKET_PAIRS:
            # Opening bracket
            close_type, bracket_type = self.BRACKET_PAIRS[token.type]
            context = self.CONTEXT_MAPPING.get(token.type)

            pair = BracketPair(
                open_type=token.type,
                close_type=close_type,
                bracket_type=bracket_type,
                open_index=index,
                context=context
            )

            self.stack.append(pair)

            # Set metadata on token
            token.metadata.paired_with = None  # Will be set when closed
            token.metadata.expansion_depth = len(self.stack)

        elif token.type in self.CLOSING_BRACKETS:
            # Closing bracket
            expected_open, bracket_type = self.CLOSING_BRACKETS[token.type]

            if self.stack:
                # Find matching opener
                matching_pair = None
                stack_index = -1

                # Look for exact match first (LIFO)
                for i in range(len(self.stack) - 1, -1, -1):
                    if self.stack[i].close_type == token.type:
                        matching_pair = self.stack.pop(i)
                        stack_index = i
                        break

                if matching_pair:
                    # Found matching opener
                    matching_pair.close_index = index
                    self.pairs.append(matching_pair)

                    # Update metadata
                    token.metadata.paired_with = matching_pair.open_index
                    token.metadata.expansion_depth = len(self.stack)

                    # Check for mismatched but valid nesting
                    if stack_index < len(self.stack):
                        # We closed a bracket that had others inside it
                        # This might indicate a problem
                        self._check_nesting_validity(matching_pair, stack_index)

                else:
                    # No matching opener found
                    self._create_unmatched_error(token, index, "closing")
                    token.metadata.expansion_depth = len(self.stack)

            else:
                # No openers at all
                self._create_unmatched_error(token, index, "closing")
                token.metadata.expansion_depth = 0

    def finalize(self, tokens: List[Token]) -> BracketValidationResult:
        """Finalize bracket tracking and return validation results."""
        # Update opener metadata for completed pairs
        for pair in self.pairs:
            if pair.close_index is not None and pair.open_index < len(tokens):
                tokens[pair.open_index].metadata.paired_with = pair.close_index

        # Report unclosed brackets
        unmatched_opens = []
        for pair in self.stack:
            if pair.open_index < len(tokens):
                token = tokens[pair.open_index]
                error = self._create_unclosed_error(pair, token)
                self.errors.append(error)
                token.metadata.error_info = error
                unmatched_opens.append(pair)

        return BracketValidationResult(
            is_valid=not self.errors,
            errors=self.errors,
            warnings=self.warnings,
            pairs=self.pairs,
            unmatched_opens=unmatched_opens
        )

    def _create_unmatched_error(
        self,
        token: Token,
        index: int,
        bracket_position: str
    ):
        """Create error for unmatched bracket."""
        error = LexerError(
            error_type=LexerErrorType.UNMATCHED_BRACKET,
            message=f"Unmatched {bracket_position} {token.type.name.lower()}",
            suggestion=self._get_bracket_suggestion(token.type, bracket_position)
        )
        self.errors.append(error)
        token.metadata.error_info = error

    def _create_unclosed_error(
        self,
        pair: BracketPair,
        token: Token
    ) -> LexerError:
        """Create error for unclosed bracket."""
        return LexerError(
            error_type=LexerErrorType.UNMATCHED_BRACKET,
            message=f"Unclosed {pair.open_type.name.lower()}",
            expected=pair.close_type.name.lower(),
            suggestion=self._get_closing_suggestion(pair)
        )

    def _check_nesting_validity(self, closed_pair: BracketPair, stack_index: int):
        """Check if bracket nesting is valid."""
        # Some bracket combinations are suspicious
        if closed_pair.bracket_type == BracketType.DOUBLE_PAREN:
            # Arithmetic expressions shouldn't typically contain other constructs
            for i in range(stack_index, len(self.stack)):
                inner_pair = self.stack[i]
                if inner_pair.bracket_type == BracketType.DOUBLE_BRACKET:
                    # Test expression inside arithmetic - unusual
                    self.warnings.append(LexerError(
                        error_type="suspicious_nesting",
                        message="Test expression [[ ]] inside arithmetic (( ))",
                        severity="warning",
                        suggestion="Consider restructuring the expression"
                    ))

    def _get_bracket_suggestion(self, token_type: TokenType, position: str) -> str:
        """Get suggestion for bracket error."""
        if position == "closing":
            if token_type in self.CLOSING_BRACKETS:
                expected_open, _ = self.CLOSING_BRACKETS[token_type]
                return f"Add matching {expected_open.name.lower()} or remove this {token_type.name.lower()}"
            else:
                return f"Remove this unexpected {token_type.name.lower()}"
        else:
            return "Remove this bracket or add matching opener"

    def _get_closing_suggestion(self, pair: BracketPair) -> str:
        """Get suggestion for unclosed bracket."""
        context_hints = {
            "arithmetic": " to complete arithmetic expression",
            "test": " to complete test expression",
            "subshell": " to complete subshell",
            "brace_group": " to complete brace group",
            "array_index": " to complete array index"
        }

        hint = context_hints.get(pair.context, "")
        return f"Add closing {pair.close_type.name.lower()}{hint}"

    def get_nesting_depth(self) -> int:
        """Get current nesting depth."""
        return len(self.stack)

    def get_current_context(self) -> Optional[str]:
        """Get current bracket context."""
        if not self.stack:
            return None

        return self.stack[-1].context

    def is_inside_context(self, context: str) -> bool:
        """Check if currently inside a specific context."""
        return any(pair.context == context for pair in self.stack)

    def get_context_stack(self) -> List[str]:
        """Get stack of current contexts."""
        return [pair.context for pair in self.stack if pair.context]

    def find_matching_bracket(
        self,
        tokens: List[Token],
        start_index: int
    ) -> Optional[int]:
        """Find matching bracket for token at start_index."""
        if start_index >= len(tokens):
            return None

        token = tokens[start_index]
        if hasattr(token.metadata, 'paired_with') and token.metadata.paired_with is not None:
            return token.metadata.paired_with

        # Search through completed pairs
        for pair in self.pairs:
            if pair.open_index == start_index:
                return pair.close_index
            elif pair.close_index == start_index:
                return pair.open_index

        return None

    def validate_bracket_balance(
        self,
        text: str
    ) -> BracketValidationResult:
        """Validate bracket balance in raw text (for quick checks)."""
        bracket_chars = {
            '(': ')', '[': ']', '{': '}',
            # Note: (( and [[ are handled as tokens, not character pairs
        }

        stack = []
        errors = []

        i = 0
        while i < len(text):
            char = text[i]

            # Skip quoted sections
            if char in '"\'':
                quote_char = char
                i += 1
                while i < len(text) and text[i] != quote_char:
                    if text[i] == '\\' and i + 1 < len(text):
                        i += 1  # Skip escaped character
                    i += 1
                i += 1
                continue

            # Check for bracket characters
            if char in bracket_chars:
                stack.append((char, i))
            elif char in bracket_chars.values():
                # Find matching opening bracket
                expected_open = None
                for open_char, close_char in bracket_chars.items():
                    if close_char == char:
                        expected_open = open_char
                        break

                if stack and stack[-1][0] == expected_open:
                    stack.pop()
                else:
                    errors.append(LexerError(
                        error_type=LexerErrorType.UNMATCHED_BRACKET,
                        message=f"Unmatched '{char}' at position {i}",
                        suggestion=f"Add matching '{expected_open}' or remove '{char}'"
                    ))

            i += 1

        # Check for unclosed brackets
        for open_char, position in stack:
            close_char = bracket_chars[open_char]
            errors.append(LexerError(
                error_type=LexerErrorType.UNMATCHED_BRACKET,
                message=f"Unclosed '{open_char}' at position {position}",
                expected=close_char,
                suggestion=f"Add closing '{close_char}'"
            ))

        return BracketValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=[],
            pairs=[],
            unmatched_opens=[]
        )
