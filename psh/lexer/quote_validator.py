"""Quote validation during lexing phase."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from ..token_enhanced import LexerError, LexerErrorType, Token
from .token_parts import TokenPart


class QuoteState(Enum):
    """State of quote processing."""
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"
    ESCAPED = "escaped"


@dataclass
class QuoteInfo:
    """Information about a quote in the text."""
    position: int
    quote_char: str
    is_opening: bool
    is_closing: bool
    is_escaped: bool
    matching_position: Optional[int] = None


@dataclass
class QuoteValidationResult:
    """Result of quote validation."""
    is_valid: bool
    errors: List[LexerError]
    warnings: List[LexerError]
    quote_info: List[QuoteInfo]


class QuoteValidator:
    """Validates quote pairing during lexing."""

    def __init__(self):
        self.quote_chars = {'"', "'"}
        # Characters that can escape quotes
        self.escape_chars = {'\\'}

    def validate_quotes_in_text(
        self,
        text: str,
        start_position: int = 0
    ) -> QuoteValidationResult:
        """Validate all quotes in a text string."""
        errors = []
        warnings = []
        quote_info = []

        quote_stack = []  # Stack of open quotes
        i = 0

        while i < len(text):
            char = text[i]

            if char in self.quote_chars:
                # Check if this quote is escaped
                is_escaped = self._is_escaped(text, i)

                if not is_escaped:
                    # Check if this closes an existing quote
                    if quote_stack and quote_stack[-1]['char'] == char:
                        # Closing quote
                        open_quote = quote_stack.pop()

                        # Create quote info for both opening and closing
                        opening_info = QuoteInfo(
                            position=start_position + open_quote['position'],
                            quote_char=char,
                            is_opening=True,
                            is_closing=False,
                            is_escaped=False,
                            matching_position=start_position + i
                        )

                        closing_info = QuoteInfo(
                            position=start_position + i,
                            quote_char=char,
                            is_opening=False,
                            is_closing=True,
                            is_escaped=False,
                            matching_position=start_position + open_quote['position']
                        )

                        quote_info.extend([opening_info, closing_info])

                    elif char == '"' and quote_stack and quote_stack[-1]['char'] == "'":
                        # Double quote inside single quotes - treat as literal
                        quote_info.append(QuoteInfo(
                            position=start_position + i,
                            quote_char=char,
                            is_opening=False,
                            is_closing=False,
                            is_escaped=True  # Effectively escaped by single quotes
                        ))

                    elif char == "'" and quote_stack and quote_stack[-1]['char'] == '"':
                        # Single quote inside double quotes - treat as literal
                        quote_info.append(QuoteInfo(
                            position=start_position + i,
                            quote_char=char,
                            is_opening=False,
                            is_closing=False,
                            is_escaped=True  # Effectively escaped by double quotes
                        ))

                    else:
                        # Opening quote
                        quote_stack.append({
                            'char': char,
                            'position': i
                        })

                else:
                    # Escaped quote
                    quote_info.append(QuoteInfo(
                        position=start_position + i,
                        quote_char=char,
                        is_opening=False,
                        is_closing=False,
                        is_escaped=True
                    ))

            i += 1

        # Check for unclosed quotes
        for open_quote in quote_stack:
            error = LexerError(
                error_type=LexerErrorType.UNCLOSED_QUOTE,
                message=f"Unclosed {open_quote['char']} quote",
                expected=open_quote['char'],
                suggestion=f"Add closing {open_quote['char']} quote"
            )
            errors.append(error)

            # Add quote info for unclosed quote
            quote_info.append(QuoteInfo(
                position=start_position + open_quote['position'],
                quote_char=open_quote['char'],
                is_opening=True,
                is_closing=False,
                is_escaped=False
            ))

        return QuoteValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            quote_info=quote_info
        )

    def validate_quotes_in_tokens(
        self,
        tokens: List[Token]
    ) -> QuoteValidationResult:
        """Validate quotes across a list of tokens."""
        errors = []
        warnings = []
        quote_info = []

        for token in tokens:
            # Check basic token quote_type
            if token.quote_type and hasattr(token, 'parts'):
                # Validate each part
                for part in token.parts:
                    if part.quote_type:
                        part_result = self._validate_token_part_quotes(token, part)
                        errors.extend(part_result.errors)
                        warnings.extend(part_result.warnings)
                        quote_info.extend(part_result.quote_info)

            # Also validate the token value directly for missed quotes
            token_result = self.validate_quotes_in_text(token.value, token.position)
            errors.extend(token_result.errors)
            warnings.extend(token_result.warnings)
            quote_info.extend(token_result.quote_info)

        return QuoteValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            quote_info=quote_info
        )

    def _validate_token_part_quotes(
        self,
        token: Token,
        part: TokenPart
    ) -> QuoteValidationResult:
        """Validate quotes in a specific token part."""
        errors = []
        warnings = []
        quote_info = []

        if not part.quote_type:
            return QuoteValidationResult(True, errors, warnings, quote_info)

        # Check if the part value has proper quote pairing
        value = part.value
        quote_char = part.quote_type

        # For string tokens, the quotes should be at the beginning and end
        if value.startswith(quote_char) and value.endswith(quote_char):
            # Check internal quote escaping
            internal_text = value[1:-1]  # Remove outer quotes
            internal_result = self.validate_quotes_in_text(
                internal_text,
                token.position + 1
            )

            # Filter errors - internal quotes of the same type should be escaped
            for error in internal_result.errors:
                if error.error_type == LexerErrorType.UNCLOSED_QUOTE:
                    # This might be okay if it's a different quote type
                    continue
                errors.append(error)

            warnings.extend(internal_result.warnings)
            quote_info.extend(internal_result.quote_info)

        elif value.startswith(quote_char) and not value.endswith(quote_char):
            # Opening quote without closing quote
            errors.append(LexerError(
                error_type=LexerErrorType.UNCLOSED_QUOTE,
                message=f"Unclosed {quote_char} quote in token",
                expected=quote_char,
                suggestion=f"Add closing {quote_char} quote"
            ))

        elif not value.startswith(quote_char) and value.endswith(quote_char):
            # Closing quote without opening quote (unusual but possible in some contexts)
            warnings.append(LexerError(
                error_type="unexpected_quote",
                message=f"Closing {quote_char} quote without opening quote",
                severity="warning"
            ))

        return QuoteValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            quote_info=quote_info
        )

    def _is_escaped(self, text: str, position: int) -> bool:
        """Check if a character at position is escaped."""
        if position == 0:
            return False

        # Count consecutive backslashes before this position
        escape_count = 0
        i = position - 1

        while i >= 0 and text[i] == '\\':
            escape_count += 1
            i -= 1

        # If odd number of backslashes, the character is escaped
        return escape_count % 2 == 1

    def extract_quoted_content(
        self,
        text: str,
        quote_char: str,
        start_position: int = 0
    ) -> Tuple[Optional[str], int, List[LexerError]]:
        """
        Extract quoted content from text starting at position.
        
        Returns:
            Tuple of (content, end_position, errors)
            content is None if quote is not properly closed
        """
        errors = []

        if start_position >= len(text) or text[start_position] != quote_char:
            return None, start_position, [LexerError(
                error_type="invalid_quote_start",
                message=f"Expected {quote_char} at position {start_position}"
            )]

        i = start_position + 1
        content_start = i

        while i < len(text):
            char = text[i]

            if char == quote_char:
                # Check if escaped
                if not self._is_escaped(text, i):
                    # Found closing quote
                    content = text[content_start:i]
                    return content, i + 1, errors

            i += 1

        # Reached end without finding closing quote
        errors.append(LexerError(
            error_type=LexerErrorType.UNCLOSED_QUOTE,
            message=f"Unclosed {quote_char} quote starting at position {start_position}",
            expected=quote_char,
            suggestion=f"Add closing {quote_char} quote"
        ))

        # Return partial content
        content = text[content_start:]
        return content, len(text), errors

    def find_quote_pairs(
        self,
        text: str
    ) -> List[Tuple[int, int, str]]:
        """
        Find all properly paired quotes in text.
        
        Returns:
            List of (start_pos, end_pos, quote_char) tuples
        """
        pairs = []
        result = self.validate_quotes_in_text(text)

        # Group quote info by matching positions
        paired_quotes = {}
        for info in result.quote_info:
            if info.matching_position is not None:
                if info.is_opening:
                    paired_quotes[info.position] = info.matching_position

        # Convert to list of tuples
        for start_pos, end_pos in paired_quotes.items():
            quote_char = text[start_pos]
            pairs.append((start_pos, end_pos, quote_char))

        return sorted(pairs)

    def is_inside_quotes(
        self,
        text: str,
        position: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a position is inside quotes.
        
        Returns:
            Tuple of (is_inside, quote_char)
        """
        if position >= len(text):
            return False, None

        # Find all quote pairs
        pairs = self.find_quote_pairs(text)

        for start_pos, end_pos, quote_char in pairs:
            if start_pos < position < end_pos:
                return True, quote_char

        return False, None
