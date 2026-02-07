"""Expansion validation during lexing phase."""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..token_enhanced import LexerErrorType


@dataclass
class ExpansionValidationResult:
    """Result of expansion validation."""
    is_valid: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    expected_close: Optional[str] = None
    suggestion: Optional[str] = None
    end_position: Optional[int] = None
    expansion_type: Optional[str] = None


class ExpansionValidator:
    """Validates shell expansions during lexing."""

    def __init__(self):
        # Pattern for parameter expansion modifiers
        self.param_modifiers = re.compile(r'[-=?+#%/^,~]')

        # Valid arithmetic operators
        self.arith_operators = {
            '+', '-', '*', '/', '%', '**',
            '<<', '>>', '&', '|', '^', '~',
            '==', '!=', '<', '>', '<=', '>=',
            '&&', '||', '!', '++', '--',
            '=', '+=', '-=', '*=', '/=', '%=',
            '&=', '|=', '^=', '<<=', '>>='
        }

    def validate_parameter_expansion(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate ${...} expansions."""
        if not text[start:].startswith('${'):
            return ExpansionValidationResult(is_valid=False)

        return self._validate_braced_expansion(
            text, start + 1, '{', '}',  # start + 1 to skip the $
            "parameter expansion",
            self._validate_parameter_content
        )

    def validate_command_substitution(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate $(...) substitutions."""
        if not text[start:].startswith('$('):
            return ExpansionValidationResult(is_valid=False)

        return self._validate_braced_expansion(
            text, start + 1, '(', ')',  # start + 1 to skip the $
            "command substitution",
            self._validate_command_content
        )

    def validate_arithmetic_expansion(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate $((...)) expansions."""
        if not text[start:].startswith('$(('):
            return ExpansionValidationResult(is_valid=False)

        # Find closing ))
        i = start + 3
        paren_depth = 2  # Start with 2 open parens
        quote_char = None
        in_quotes = False

        while i < len(text) and paren_depth > 0:
            char = text[i]

            # Handle quotes
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and text[i-1] != '\\':
                    in_quotes = False
                    quote_char = None

            # Handle parens outside quotes
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1

            i += 1

        if paren_depth != 0:
            # Unclosed arithmetic expansion
            partial = text[start:min(start + 50, len(text))]
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message=f"Unclosed arithmetic expansion: {partial}...",
                expected_close='))',
                suggestion="Add closing '))' to complete the arithmetic expansion",
                expansion_type="arithmetic"
            )

        # Validate arithmetic content
        content = text[start + 3:i - 2]  # Extract content between $(( and ))
        content_validation = self._validate_arithmetic_content(content, start + 3)

        if not content_validation.is_valid:
            return content_validation

        return ExpansionValidationResult(
            is_valid=True,
            end_position=i,
            expansion_type="arithmetic"
        )

    def validate_backtick_substitution(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate `...` substitutions."""
        if not text[start:].startswith('`'):
            return ExpansionValidationResult(is_valid=False)

        # Find closing backtick
        i = start + 1
        escaped = False

        while i < len(text):
            char = text[i]

            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '`':
                # Found closing backtick
                content = text[start + 1:i]
                content_validation = self._validate_command_content(content, start + 1)

                if not content_validation.is_valid:
                    return content_validation

                return ExpansionValidationResult(
                    is_valid=True,
                    end_position=i + 1,
                    expansion_type="command_backtick"
                )

            i += 1

        # Unclosed backtick
        partial = text[start:min(start + 50, len(text))]
        return ExpansionValidationResult(
            is_valid=False,
            error_type=LexerErrorType.UNCLOSED_EXPANSION,
            error_message=f"Unclosed backtick substitution: {partial}...",
            expected_close='`',
            suggestion="Add closing '`' to complete the command substitution",
            expansion_type="command_backtick"
        )

    def validate_process_substitution(
        self,
        text: str,
        start: int
    ) -> ExpansionValidationResult:
        """Validate <(...) and >(...) process substitutions."""
        if start >= len(text) or text[start] not in '<>':
            return ExpansionValidationResult(is_valid=False)

        if start + 1 >= len(text) or text[start + 1] != '(':
            return ExpansionValidationResult(is_valid=False)

        direction = text[start]  # < or >

        return self._validate_braced_expansion(
            text, start + 1, '(', ')',
            f"process substitution ({direction}(...))",
            self._validate_command_content
        )

    def _validate_braced_expansion(
        self,
        text: str,
        start: int,
        open_char: str,
        close_char: str,
        expansion_name: str,
        content_validator
    ) -> ExpansionValidationResult:
        """Generic validation for braced expansions."""
        if not text[start:].startswith(open_char):
            return ExpansionValidationResult(is_valid=False)

        # Find closing character, handling nesting
        depth = 1
        i = start + 1
        in_quotes = False
        quote_char = None

        while i < len(text) and depth > 0:
            char = text[i]

            # Handle quotes
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and text[i-1] != '\\':
                    in_quotes = False
                    quote_char = None

            # Handle braces outside quotes
            elif not in_quotes:
                if char == open_char:
                    depth += 1
                elif char == close_char:
                    depth -= 1

            i += 1

        if depth != 0:
            # Unclosed expansion
            partial = text[start:min(start + 50, len(text))]
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message=f"Unclosed {expansion_name}: {partial}...",
                expected_close=close_char,
                suggestion=f"Add closing '{close_char}' to complete the {expansion_name}",
                expansion_type=expansion_name.split()[0]  # First word
            )

        # Validate content
        content = text[start + 1:i - 1]
        content_validation = content_validator(content, start + 1)

        if not content_validation.is_valid:
            return content_validation

        return ExpansionValidationResult(
            is_valid=True,
            end_position=i,
            expansion_type=expansion_name.split()[0]
        )

    def _validate_parameter_content(
        self,
        content: str,
        position: int
    ) -> ExpansionValidationResult:
        """Validate content of parameter expansion."""
        if not content:
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message="Empty parameter expansion",
                suggestion="Add parameter name inside ${}"
            )

        # Check for valid parameter name or expansion
        # This is a simplified check - full validation would be quite complex

        # Check for special parameters
        if len(content) == 1 and content in '@*#?$!0123456789':
            return ExpansionValidationResult(is_valid=True)

        # Check for simple variable name
        if content.isidentifier():
            return ExpansionValidationResult(is_valid=True)

        # Check for parameter expansion with modifiers
        # Format: ${parameter[:]modifier[word]}
        # This is a simplified check
        if any(op in content for op in ':-=?+#%/^,~'):
            return ExpansionValidationResult(is_valid=True)

        # Check for array access
        if '[' in content and ']' in content:
            return ExpansionValidationResult(is_valid=True)

        # Check for indirection
        if content.startswith('!'):
            return ExpansionValidationResult(is_valid=True)

        # If we can't validate it, assume it's valid
        # Full validation would require parsing the parameter expansion grammar
        return ExpansionValidationResult(is_valid=True)

    def _validate_command_content(
        self,
        content: str,
        position: int
    ) -> ExpansionValidationResult:
        """Validate content of command substitution."""
        if not content.strip():
            # Empty command substitution is valid (results in empty string)
            return ExpansionValidationResult(is_valid=True)

        # Basic syntax checks for common errors
        # Full validation would require parsing the command

        # Check for unclosed quotes in the command
        quote_chars = ["'", '"']
        for quote_char in quote_chars:
            count = content.count(quote_char)
            # Count escaped quotes
            escaped_count = content.count(f'\\{quote_char}')
            actual_count = count - escaped_count

            if actual_count % 2 != 0:
                return ExpansionValidationResult(
                    is_valid=False,
                    error_type=LexerErrorType.UNCLOSED_QUOTE,
                    error_message=f"Unclosed {quote_char} quote in command substitution",
                    suggestion=f"Add closing {quote_char} quote"
                )

        return ExpansionValidationResult(is_valid=True)

    def _validate_arithmetic_content(
        self,
        content: str,
        position: int
    ) -> ExpansionValidationResult:
        """Validate content of arithmetic expansion."""
        if not content.strip():
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNCLOSED_EXPANSION,
                error_message="Empty arithmetic expression",
                suggestion="Add arithmetic expression inside $(())"
            )

        # Basic validation - check for balanced parentheses
        paren_depth = 0
        for char in content:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth < 0:
                    return ExpansionValidationResult(
                        is_valid=False,
                        error_type=LexerErrorType.UNMATCHED_BRACKET,
                        error_message="Unmatched ')' in arithmetic expression",
                        suggestion="Remove extra ')' or add matching '('"
                    )

        if paren_depth != 0:
            return ExpansionValidationResult(
                is_valid=False,
                error_type=LexerErrorType.UNMATCHED_BRACKET,
                error_message="Unmatched '(' in arithmetic expression",
                suggestion="Add closing ')' or remove extra '('"
            )

        return ExpansionValidationResult(is_valid=True)

    def validate_expansion_at_position(
        self,
        text: str,
        position: int
    ) -> ExpansionValidationResult:
        """Validate any expansion starting at the given position."""
        if position >= len(text):
            return ExpansionValidationResult(is_valid=False)

        # Check for ${ parameter expansion
        if text[position:].startswith('${'):
            return self.validate_parameter_expansion(text, position)

        # Check for $(( arithmetic expansion
        elif text[position:].startswith('$(('):
            return self.validate_arithmetic_expansion(text, position)

        # Check for $( command substitution
        elif text[position:].startswith('$('):
            return self.validate_command_substitution(text, position)

        # Check for backtick command substitution
        elif text[position:].startswith('`'):
            return self.validate_backtick_substitution(text, position)

        # Check for process substitution
        elif position + 1 < len(text) and text[position] in '<>' and text[position + 1] == '(':
            return self.validate_process_substitution(text, position)

        return ExpansionValidationResult(is_valid=False)

    def find_all_expansions(
        self,
        text: str
    ) -> List[Tuple[int, ExpansionValidationResult]]:
        """Find and validate all expansions in text."""
        expansions = []
        i = 0

        while i < len(text):
            # Look for expansion start
            if text[i] == '$':
                result = self.validate_expansion_at_position(text, i)
                if result.error_type:  # Found an expansion (even if invalid)
                    expansions.append((i, result))
                    # Skip past this expansion
                    if result.end_position:
                        i = result.end_position
                    else:
                        i += 1
                else:
                    i += 1
            elif text[i] == '`':
                result = self.validate_backtick_substitution(text, i)
                if result.error_type:
                    expansions.append((i, result))
                    if result.end_position:
                        i = result.end_position
                    else:
                        i += 1
                else:
                    i += 1
            elif text[i] in '<>' and i + 1 < len(text) and text[i + 1] == '(':
                result = self.validate_process_substitution(text, i)
                if result.error_type:
                    expansions.append((i, result))
                    if result.end_position:
                        i = result.end_position
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1

        return expansions
