"""Enhanced helper methods using pure functions.

This module provides helper methods that use the pure functions from pure_helpers.py,
maintaining the same interface while improving testability and modularity.
"""

from typing import List, Optional, Tuple
from ..token_types import TokenType
from .position import Position
from .token_parts import TokenPart
from .constants import OPERATORS_BY_LENGTH, DOUBLE_QUOTE_ESCAPES, SPECIAL_VARIABLES
from . import pure_helpers


class EnhancedLexerHelpers:
    """Mixin class providing helper methods using pure functions."""
    
    def read_until_char(self, target: str, escape: bool = False) -> str:
        """Read until target character (wrapper for pure function)."""
        content, new_pos = pure_helpers.read_until_char(
            self.input, 
            self.position, 
            target, 
            escape
        )
        self.position = new_pos
        return content
    
    def handle_escape_sequence(self, quote_context: Optional[str] = None) -> str:
        """
        Handle escape sequences based on context (wrapper for pure function).
        
        Args:
            quote_context: Current quote context ('"', "'", or None)
            
        Returns:
            The escaped character(s) to add to the output
        """
        escaped_str, new_pos = pure_helpers.handle_escape_sequence(
            self.input, self.position, quote_context
        )
        self.position = new_pos
        return escaped_str
    
    def read_balanced_parens(self) -> Tuple[str, bool]:
        """
        Read content until balanced parentheses.
        
        Returns:
            Tuple of (content, is_closed) where is_closed indicates if
            the parentheses were properly balanced.
        """
        start_pos = self.position
        end_pos, is_closed = pure_helpers.find_balanced_parentheses(
            self.input, self.position, track_quotes=True
        )
        
        # Extract the content (excluding the closing paren)
        if is_closed:
            content = self.input[start_pos:end_pos-1]
            self.position = end_pos
        else:
            content = self.input[start_pos:end_pos]
            self.position = end_pos
            
        # Error handling for strict mode
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
        start_pos = self.position
        end_pos, is_closed = pure_helpers.find_balanced_double_parentheses(
            self.input, self.position
        )
        
        # Extract the content (excluding the closing ))
        if is_closed:
            content = self.input[start_pos:end_pos-2]
            self.position = end_pos
        else:
            content = self.input[start_pos:end_pos]
            self.position = end_pos
            
        # Error handling for strict mode
        if not is_closed and self.config.strict_mode:
            self._error("Unclosed arithmetic expansion")
            
        return content, is_closed
    
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
        
        # Use pure function for operator matching
        result = pure_helpers.find_operator_match(
            self.input, self.position, OPERATORS_BY_LENGTH
        )
        
        if result:
            op, token_type, _ = result
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
        return pure_helpers.is_comment_start(self.input, self.position)
    
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
    
    def read_variable_name(self) -> str:
        """Read a simple variable name (after $) using pure functions."""
        var_name, new_pos = pure_helpers.extract_variable_name(
            self.input, 
            self.position, 
            SPECIAL_VARIABLES, 
            self.config.posix_mode
        )
        self.position = new_pos
        
        # Normalize the identifier if configured
        if var_name:
            from .unicode_support import normalize_identifier
            var_name = normalize_identifier(
                var_name, 
                posix_mode=self.config.posix_mode,
                case_sensitive=self.config.case_sensitive
            )
        
        return var_name
    
    def skip_whitespace(self) -> None:
        """Skip whitespace using pure function."""
        new_pos = pure_helpers.scan_whitespace(
            self.input, 
            self.position, 
            unicode_aware=not self.config.posix_mode
        )
        self.position = new_pos
    
    def read_quoted_string(self, quote_char: str) -> Tuple[str, bool]:
        """
        Read quoted string content using pure function.
        
        Args:
            quote_char: The quote character
            
        Returns:
            Tuple of (content, found_closing_quote)
        """
        content, new_pos, found_closing = pure_helpers.extract_quoted_content(
            self.input,
            self.position,
            quote_char,
            allow_escapes=(quote_char == '"')  # Only allow escapes in double quotes
        )
        self.position = new_pos
        return content, found_closing