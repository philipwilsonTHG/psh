"""Helper methods for lexer operations."""

from typing import List, Optional, Tuple
from ..token_types import TokenType
from .position import Position
from .token_parts import TokenPart
from .constants import OPERATORS_BY_LENGTH, DOUBLE_QUOTE_ESCAPES


class LexerHelpers:
    """Mixin class providing helper methods for the lexer."""
    
    def read_until_char(self, target: str, escape: bool = False) -> str:
        """Read until a specific character is found."""
        content = ""
        while self.current_char() and self.current_char() != target:
            if escape and self.current_char() == '\\' and self.peek_char():
                self.advance()  # Skip backslash
                if self.current_char():
                    content += self.current_char()
                    self.advance()
            else:
                content += self.current_char()
                self.advance()
        return content
    
    def handle_escape_sequence(self, quote_context: Optional[str] = None) -> str:
        """
        Handle escape sequences based on context.
        
        Args:
            quote_context: Current quote context ('"', "'", or None)
            
        Returns:
            The escaped character(s) to add to the output
        """
        if not self.peek_char():
            return '\\'
        
        self.advance()  # Skip backslash
        next_char = self.current_char()
        
        if quote_context == '"':
            # In double quotes
            if next_char == '\n':
                # Escaped newline is a line continuation - remove it
                self.advance()  # Skip the newline
                return ''  # Return empty string to continue the line
            elif next_char in '"\\`':
                self.advance()  # Skip the escaped character
                return next_char
            elif next_char == '$':
                # Special case: \$ preserves the backslash in double quotes
                self.advance()  # Skip the escaped character
                return '\\$'
            elif next_char in DOUBLE_QUOTE_ESCAPES:
                self.advance()  # Skip the escaped character
                return DOUBLE_QUOTE_ESCAPES[next_char]
            else:
                # Other characters keep the backslash
                self.advance()  # Skip the escaped character
                return '\\' + next_char
        elif quote_context is None:
            # Outside quotes - backslash escapes everything
            if next_char == '\n':
                # Escaped newline is a line continuation - remove it
                self.advance()  # Skip the newline
                return ''  # Return empty string to continue the line
            self.advance()  # Skip the escaped character
            if next_char == '$':
                # Use a special marker for escaped dollar to prevent variable expansion
                return '\x00$'  # NULL character followed by $
            return next_char
        else:
            # Single quotes - no escaping
            self.advance()  # Skip the escaped character
            return '\\' + next_char
    
    def read_balanced_parens(self) -> Tuple[str, bool]:
        """
        Read content until balanced parentheses.
        
        Returns:
            Tuple of (content, is_closed) where is_closed indicates if
            the parentheses were properly balanced.
        """
        content = ""
        depth = 1
        
        while self.current_char() and depth > 0:
            char = self.current_char()
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    self.advance()
                    break
            content += char
            self.advance()
        
        is_closed = (depth == 0)
        
        # If we hit EOF with unbalanced parentheses, we still need to error
        # for batch mode, but allow the lexer to handle it gracefully for
        # interactive mode through the end-of-input state checks.
        if not is_closed and self.config.strict_mode:
            self._error("Unclosed parenthesis")
            
        return content, is_closed
    
    def read_balanced_double_parens(self) -> Tuple[str, bool]:
        """
        Read content until balanced double parentheses for arithmetic.
        
        Returns:
            Tuple of (content, is_closed) where is_closed indicates if
            the double parentheses were properly closed.
        """
        content = ""
        depth = 0  # Track individual parens, not pairs
        found_closing = False
        
        while self.current_char():
            char = self.current_char()
            next_char = self.peek_char()
            
            # Check for )) when depth is exactly 2 (from initial $(( )
            if char == ')' and next_char == ')' and depth == 0:
                # This is the closing )) for the arithmetic expansion
                self.advance()  # Skip first )
                self.advance()  # Skip second )
                found_closing = True
                break
            
            # Track depth with individual parens
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                
            content += char
            self.advance()
        
        # If we hit EOF without finding closing )), error in strict mode but
        # allow the lexer to handle it gracefully in interactive mode.
        if not found_closing and self.config.strict_mode:
            self._error("Unclosed arithmetic expansion")
            
        return content, found_closing
    
    def _check_for_operator(self) -> Optional[Tuple[str, TokenType]]:
        """Check if current position starts an operator."""
        # Special handling for != (should be a single word token for test command)
        if self.peek_string(2) == '!=':
            return None  # Let it be handled as a word
        
        # If we're after =~, treat [ and ] as regular characters for regex patterns
        if self.after_regex_match and self.current_char() in '[]':
            return None  # Let it be handled as part of the word
        
        # Check for [[ first (before single [)
        if self.peek_string(2) == '[[' and self.command_position:
            return ('[[', TokenType.DOUBLE_LBRACKET)
        
        # Special handling for [ and ]
        # [ should be a word at command position or after whitespace
        # [ should be LBRACKET when immediately after a word (for array subscripts)
        if self.current_char() == '[':
            # Check if we're at command position or after whitespace
            if self.command_position or self.position == 0:
                return None  # Let it be handled as a word
            # Check if previous character is whitespace or operator
            if self.position > 0:
                prev_char = self.input[self.position - 1]
                if prev_char in ' \t\n|;&(){}':
                    return None  # Let it be handled as a word
            # Otherwise, it's an array subscript
            return ('[', TokenType.LBRACKET)
        
        # ] is always treated as RBRACKET when it's an operator context
        # But let the word handler deal with it when part of a word
        
        
        # Check operators from longest to shortest
        for length in sorted(OPERATORS_BY_LENGTH.keys(), reverse=True):
            if length > len(self.input) - self.position:
                continue
            
            op = self.peek_string(length)
            if op in OPERATORS_BY_LENGTH[length]:
                token_type = OPERATORS_BY_LENGTH[length][op]
                # Only return if operator is enabled in configuration
                if self._is_operator_enabled(op, token_type):
                    return (op, token_type)
        
        return None
    
    def _is_operator_enabled(self, op: str, token_type: TokenType) -> bool:
        """
        Check if an operator is enabled in the current configuration.
        
        Args:
            op: The operator string
            token_type: The token type
            
        Returns:
            True if the operator should be processed, False otherwise
        """
        # Pipe operations
        if token_type == TokenType.PIPE:
            return self.config.enable_pipes
            
        # Redirection operators
        if token_type in (TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
                         TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
                         TokenType.REDIRECT_ERR_APPEND):
            return self.config.enable_redirections
            
        # Heredoc operators
        if token_type in (TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING):
            return self.config.enable_heredocs
            
        # Background operator
        if token_type == TokenType.AMPERSAND:
            return self.config.enable_background
            
        # Logical operators
        if token_type in (TokenType.AND_AND, TokenType.OR_OR):
            return self.config.enable_logical_operators
            
        # Compound command operators
        if token_type in (TokenType.DOUBLE_LPAREN, TokenType.DOUBLE_LBRACKET, TokenType.DOUBLE_RBRACKET):
            return self.config.enable_compound_commands
            
        # Process substitution
        if token_type in (TokenType.PROCESS_SUB_IN, TokenType.PROCESS_SUB_OUT):
            return self.config.enable_process_substitution
            
        # Regex match operator
        if token_type == TokenType.REGEX_MATCH:
            return self.config.enable_regex_operators
            
        # Default: allow other operators (basic shell operators like semicolon, parens, etc.)
        return True
    
    def _build_token_value(self, parts: List[TokenPart]) -> str:
        """Build complete token value from parts."""
        full_value = ""
        for part in parts:
            if part.is_variable:
                full_value += '$' + part.value
            elif part.is_expansion:
                full_value += part.value
            else:
                full_value += part.value
        return full_value
    
    def _get_word_terminators(self) -> set:
        """Get the set of word terminator characters based on configuration."""
        # Start with basic ASCII terminators (always included)
        terminators = {' ', '\t', '\n'}
        
        # Add quote characters that are enabled
        if self.config.enable_single_quotes:
            terminators.add("'")
        if self.config.enable_double_quotes:
            terminators.add('"')
        if self.config.enable_backtick_quotes:
            terminators.add('`')
        
        # Add operators that are enabled
        if self.config.enable_pipes:
            terminators.add('|')
        if self.config.enable_redirections:
            terminators.update('<', '>')
        if self.config.enable_background:
            terminators.add('&')
        
        # Always include basic shell operators
        terminators.update(';', '(', ')', '{', '}')
        
        return terminators
    
    def _is_word_terminator_char(self, char: str) -> bool:
        """
        Check if a character terminates a word, including Unicode whitespace.
        
        Args:
            char: Character to check
            
        Returns:
            True if character terminates a word
        """
        # Import here to avoid circular imports
        from .unicode_support import is_whitespace
        
        # Check Unicode whitespace first
        if is_whitespace(char, self.config.posix_mode):
            return True
            
        # Check static terminators
        terminators = self._get_word_terminators()
        return char in terminators
    
    def _is_word_terminator(self, char: str) -> bool:
        """Check if character terminates a word in current context."""
        # Special handling for [ and ]
        if char == '[':
            # If we're parsing a regex pattern, [ is part of the pattern
            if self.after_regex_match:
                return False
            # [ terminates a word only if we're building a word (for array subscripts)
            # If we're at the start of a word, [ is part of the word
            if self.state.name == 'IN_WORD' and self.position > self.token_start_pos.offset:
                return True
            return False
        elif char == ']':
            # ] always terminates a word, unless we're parsing a regex pattern
            if self.after_regex_match:
                return False
            return True
        
        # Use Unicode-aware word terminator check
        if self.in_double_brackets > 0:
            # In double brackets, use similar logic but check terminators
            if self._is_word_terminator_char(char):
                return True
            if char == ']' and self.peek_char() == ']':
                return True
        else:
            return self._is_word_terminator_char(char)
        return False
    
    def _is_comment_start(self) -> bool:
        """Check if # at current position starts a comment."""
        return self.position == 0 or self.input[self.position - 1] in ' \t\n;'
    
    def _validate_input_bounds(self) -> bool:
        """
        Validate that current position is within input bounds.
        
        Returns:
            True if position is valid, False if at EOF
        """
        return self.position < len(self.input)
    
    def _validate_closing_character(self, expected_char: str, error_message: str) -> bool:
        """
        Validate and consume an expected closing character.
        
        Args:
            expected_char: The character we expect to find
            error_message: Error message if character is not found
            
        Returns:
            True if character was found and consumed, False otherwise
        """
        if self.current_char() == expected_char:
            self.advance()
            return True
        else:
            self._error(error_message)
            return False
    
    def _create_error_recovery_part(self, start_pos: Position, quote_context: Optional[str]) -> TokenPart:
        """
        Create an empty TokenPart for error recovery.
        
        Args:
            start_pos: Starting position
            quote_context: Quote context if any
            
        Returns:
            Empty TokenPart for recovery
        """
        return TokenPart(
            value='',
            quote_type=quote_context,
            is_variable=False,
            is_expansion=False,
            start_pos=start_pos,
            end_pos=self.get_current_position()
        )
    
    def _can_start_variable_with_char(self, char: Optional[str]) -> bool:
        """Check if the given character can start a variable name."""
        if not char:
            # At end of input, $ should be treated as literal
            return False
        
        # Import here to avoid circular imports
        from .unicode_support import is_identifier_start
        from .constants import SPECIAL_VARIABLES
        
        # Check special variables (single character)
        if char in SPECIAL_VARIABLES:
            return True
        
        # Check if it's a valid identifier start
        if is_identifier_start(char, self.config.posix_mode):
            return True
        
        # For characters that can't start a variable, we still want to attempt
        # variable parsing if the character could be part of a word.
        # Only treat $ as literal if the next character is definitely a word terminator.
        return not self._is_word_terminator_char(char)