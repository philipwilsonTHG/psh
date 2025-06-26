"""Core lexer implementation."""

import re
from typing import List, Optional
from ..token_types import Token, TokenType
from .position import (
    LexerConfig, LexerState, PositionTracker, LexerErrorHandler, Position
)
from .constants import KEYWORDS, SPECIAL_VARIABLES
from .unicode_support import normalize_identifier
from .helpers import LexerHelpers
from .state_handlers import StateHandlers
from .token_parts import TokenPart, RichToken

# Legacy pattern for compatibility
VARIABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class StateMachineLexer(LexerHelpers, StateHandlers):
    """State machine-based lexer for shell tokenization."""
    
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        self.input = input_string
        self.config = config or LexerConfig()
        self.tokens: List[Token] = []
        self.state = LexerState.NORMAL
        
        # Position tracking
        self.position_tracker = PositionTracker(input_string)
        
        # Error handling
        self.error_handler = LexerErrorHandler(self.config)
        
        # Context tracking
        self.in_double_brackets = 0
        self.paren_depth = 0
        self.command_position = True
        self.after_regex_match = False  # Track if we just saw =~
        
        # Buffer for current token being built
        self.current_parts: List[TokenPart] = []
        self.token_start_pos = Position(0, 1, 1)
        
        # Heredoc tracking
        self.heredoc_delimiters: List[str] = []
        
        # State handler dispatch table for O(1) lookup (optimization from v0.58.3)
        # Replaces O(n) if-elif chain with dictionary lookup for better performance
        self.state_handlers = {
            LexerState.NORMAL: self.handle_normal_state,
            LexerState.IN_WORD: self.handle_word_state,
            LexerState.IN_DOUBLE_QUOTE: self.handle_double_quote_state,
            LexerState.IN_SINGLE_QUOTE: self.handle_single_quote_state,
            LexerState.IN_VARIABLE: self.handle_variable_state,
            LexerState.IN_BRACE_VAR: self.handle_brace_var_state,
            LexerState.IN_COMMAND_SUB: self.handle_command_sub_state,
            LexerState.IN_ARITHMETIC: self.handle_arithmetic_state,
            LexerState.IN_BACKTICK: self.handle_backtick_state,
            LexerState.IN_COMMENT: self.handle_comment_state,
        }
    
    @property
    def position(self) -> int:
        """Get current absolute position."""
        return self.position_tracker.position
    
    @position.setter
    def position(self, value: int) -> None:
        """Set absolute position (used by error recovery)."""
        # Calculate how much to advance/retreat
        diff = value - self.position_tracker.position
        if diff > 0:
            self.position_tracker.advance(diff)
        elif diff < 0:
            # For retreat, we need to reset and advance to target
            self.position_tracker = PositionTracker(self.input)
            self.position_tracker.advance(value)
    
    def current_char(self) -> Optional[str]:
        """Get character at current position."""
        if self.position >= len(self.input):
            return None
        return self.input[self.position]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Look ahead at character."""
        pos = self.position + offset
        if pos >= len(self.input):
            return None
        return self.input[pos]
    
    def peek_string(self, length: int) -> str:
        """Look ahead at multiple characters."""
        return self.input[self.position:self.position + length]
    
    def advance(self, count: int = 1) -> None:
        """Move position forward."""
        self.position_tracker.advance(count)
    
    def get_current_position(self) -> Position:
        """Get current position as a Position object."""
        return self.position_tracker.get_current_position()
    
    def parse_variable_or_expansion(self, quote_context: Optional[str] = None) -> TokenPart:
        """
        Parse a variable or expansion starting after the $.
        
        Args:
            quote_context: The quote type if inside quotes ('"', "'", or None)
            
        Returns:
            TokenPart representing the parsed variable or expansion
        """
        start_pos = self.position_tracker.get_position_at_offset(self.position - 1)  # Include the $ in position
        
        if self.current_char() == '(':
            return self._parse_command_or_arithmetic_expansion(start_pos, quote_context)
        elif self.current_char() == '{':
            return self._parse_brace_variable_expansion(start_pos, quote_context)
        else:
            return self._parse_simple_variable(start_pos, quote_context)
    
    def _parse_command_or_arithmetic_expansion(self, start_pos: Position, quote_context: Optional[str]) -> TokenPart:
        """
        Parse command substitution $(...) or arithmetic expansion $((...)).
        
        Args:
            start_pos: Starting position (includes the $)
            quote_context: Quote context if any
            
        Returns:
            TokenPart for the expansion
        """
        if self.peek_char() == '(':
            # Arithmetic expansion $((
            if not self.config.enable_arithmetic_expansion:
                self._error("Arithmetic expansion disabled in configuration")
                return self._create_error_recovery_part(start_pos, quote_context)
                
            self.advance(2)  # Skip ((
            content, is_closed = self.read_balanced_double_parens()
            if is_closed:
                token_value = '$((' + content + '))'
            else:
                token_value = '$((' + content
            return TokenPart(
                value=token_value,
                quote_type=quote_context,
                is_expansion=True,
                start_pos=start_pos,
                end_pos=self.get_current_position()
            )
        else:
            # Command substitution $(
            if not self.config.enable_command_substitution:
                self._error("Command substitution disabled in configuration")
                return self._create_error_recovery_part(start_pos, quote_context)
                
            self.advance()  # Skip (
            content, is_closed = self.read_balanced_parens()
            if is_closed:
                token_value = '$(' + content + ')'
            else:
                token_value = '$(' + content
            return TokenPart(
                value=token_value,
                quote_type=quote_context,
                is_expansion=True,
                start_pos=start_pos,
                end_pos=self.get_current_position()
            )
    
    def _parse_brace_variable_expansion(self, start_pos: Position, quote_context: Optional[str]) -> TokenPart:
        """
        Parse brace variable expansion ${...}.
        
        Args:
            start_pos: Starting position (includes the $)
            quote_context: Quote context if any
            
        Returns:
            TokenPart for the variable expansion
        """
        if not self.config.enable_parameter_expansion:
            self._error("Parameter expansion disabled in configuration")
            return self._create_error_recovery_part(start_pos, quote_context)
            
        self.advance()  # Skip {
        var_content = self.read_until_char('}')
        
        if self._validate_closing_character('}', "Unclosed variable expansion"):
            return TokenPart(
                value='{' + var_content + '}',
                quote_type=quote_context,
                is_variable=True,
                start_pos=start_pos,
                end_pos=self.get_current_position()
            )
        else:
            # Return empty part for error recovery
            return TokenPart(
                value='',
                quote_type=quote_context,
                is_variable=True,
                start_pos=start_pos,
                end_pos=self.get_current_position()
            )
    
    def _parse_simple_variable(self, start_pos: Position, quote_context: Optional[str]) -> TokenPart:
        """
        Parse simple variable $VAR.
        
        Args:
            start_pos: Starting position (includes the $)
            quote_context: Quote context if any
            
        Returns:
            TokenPart for the variable
        """
        var_name = self.read_variable_name()
        return TokenPart(
            value=var_name,
            quote_type=quote_context,
            is_variable=True,
            start_pos=start_pos,
            end_pos=self.get_current_position()
        )

    def read_variable_name(self) -> str:
        """Read a simple variable name (after $) with Unicode support."""
        from .unicode_support import is_identifier_start, is_identifier_char
        
        var_name = ""
        
        # Special single-character variables (always ASCII)
        if self.current_char() in SPECIAL_VARIABLES:
            var_name = self.current_char()
            self.advance()
            return var_name
        
        # Regular variable names - use Unicode-aware functions
        posix_mode = self.config.posix_mode
        
        # First character must be valid identifier start
        if self.current_char() and is_identifier_start(self.current_char(), posix_mode):
            var_name += self.current_char()
            self.advance()
            
            # Subsequent characters can be identifier characters
            while self.current_char() and is_identifier_char(self.current_char(), posix_mode):
                var_name += self.current_char()
                self.advance()
        
        # Normalize the identifier if configured
        if var_name:
            var_name = normalize_identifier(
                var_name, 
                posix_mode=posix_mode,
                case_sensitive=self.config.case_sensitive
            )
        
        return var_name
    
    def emit_token(self, token_type: TokenType, value: str, start_pos: Optional[Position] = None,
                   quote_type: Optional[str] = None, end_pos: Optional[Position] = None) -> None:
        """Emit a token with current parts."""
        if start_pos is None:
            start_pos = self.token_start_pos
        if end_pos is None:
            end_pos = self.get_current_position()
            
        # Create and add the token
        token = self._create_token(token_type, value, start_pos, end_pos, quote_type)
        self.tokens.append(token)
        
        # Update parsing context
        self._update_command_position_context(token_type)
    
    def _create_token(self, token_type: TokenType, value: str, start_pos: Position, 
                     end_pos: Position, quote_type: Optional[str] = None) -> Token:
        """
        Create a token, potentially with parts.
        
        Args:
            token_type: Type of token to create
            value: Token value
            start_pos: Starting position
            end_pos: Ending position
            quote_type: Quote type if applicable
            
        Returns:
            Token or RichToken with parts
        """
        # Convert Position to int for compatibility
        start_offset = start_pos.offset if isinstance(start_pos, Position) else start_pos
        end_offset = end_pos.offset if isinstance(end_pos, Position) else end_pos
        token = Token(token_type, value, start_offset, end_offset, quote_type)
        
        # Convert to RichToken if we have parts
        if self.current_parts:
            rich_token = RichToken.from_token(token, self.current_parts)
            self.current_parts = []  # Clear parts after use
            return rich_token
        else:
            return token
    
    def _update_command_position_context(self, token_type: TokenType) -> None:
        """
        Update command position tracking based on token type.
        
        Args:
            token_type: The type of token that was just emitted
        """
        # Tokens that start a new command context
        command_starting_tokens = {
            TokenType.SEMICOLON, TokenType.AND_AND, TokenType.OR_OR,
            TokenType.PIPE, TokenType.LPAREN, TokenType.NEWLINE,
            TokenType.IF, TokenType.WHILE, TokenType.FOR, TokenType.CASE,
            TokenType.THEN, TokenType.DO, TokenType.ELSE, TokenType.ELIF,
            TokenType.LBRACE  # Enable keywords after {
        }
        
        # Tokens that don't affect command position (redirections)
        neutral_tokens = {
            TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
            TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
            TokenType.REDIRECT_ERR_APPEND, TokenType.HEREDOC,
            TokenType.HEREDOC_STRIP, TokenType.HERE_STRING
        }
        
        if token_type in command_starting_tokens:
            self.command_position = True
        elif token_type not in neutral_tokens:
            self.command_position = False
    
    def _error(self, message: str) -> bool:
        """Handle error with current position."""
        return self.error_handler.handle_error(self, message)
        
    def _format_error(self, message: str, position: int) -> str:
        """Format an error message with context from the input (legacy compatibility)."""
        from .position import LexerError
        pos_obj = self.position_tracker.get_position_at_offset(position)
        error = LexerError(message, pos_obj, self.input)
        return str(error)
    
    def is_keyword_context(self, word: str) -> bool:
        """Check if a word should be treated as a keyword based on context."""
        # Additional context checks for specific keywords
        if word == 'in':
            # 'in' is definitely a keyword after 'for variable' or 'case expr'
            # This requires looking back at previous tokens
            if len(self.tokens) >= 2:
                # After 'for variable'
                if (self.tokens[-2].type == TokenType.FOR and 
                    self.tokens[-1].type == TokenType.WORD):
                    return True
                # After 'select variable'
                if (self.tokens[-2].type == TokenType.SELECT and 
                    self.tokens[-1].type == TokenType.WORD):
                    return True
                # After 'case expr' 
                if self.tokens[-2].type == TokenType.CASE:
                    return True
            # Don't return False here - let it fall through to the general check
        
        # 'esac' can appear after ;; or at start of line
        if word == 'esac':
            if len(self.tokens) > 0:
                last_token = self.tokens[-1]
                if last_token.type in (TokenType.DOUBLE_SEMICOLON, TokenType.SEMICOLON_AMP, 
                                     TokenType.AMP_SEMICOLON, TokenType.NEWLINE):
                    return True
            return self.command_position
        
        # 'do' and 'done' should only be keywords in loop contexts
        # For now, use command_position as a simple heuristic
        if word in ('do', 'done'):
            return self.command_position
        
        # 'in' is handled specially above, but as a fallback
        if word == 'in':
            return self.command_position
            
        # Other keywords are only recognized at command position
        if not self.command_position:
            return False
        
        return True
    
    def tokenize(self) -> List[Token]:
        """Main tokenization method - interface compatible with existing tokenizer."""
        while self.position < len(self.input) or self.state != LexerState.NORMAL:
            # Use dispatch table for O(1) state handler lookup (v0.58.3 optimization)
            # This replaces the previous if-elif chain for better performance
            handler = self.state_handlers.get(self.state)
            if handler:
                handler()
            else:
                # Unknown state - advance and reset to normal for recovery
                self.advance()
                self.state = LexerState.NORMAL
        
        # Check for unclosed quotes or other incomplete states
        if self.state == LexerState.IN_SINGLE_QUOTE:
            self._error("Unclosed single quote")
        elif self.state == LexerState.IN_DOUBLE_QUOTE:
            self._error("Unclosed double quote")
        elif self.state == LexerState.IN_BACKTICK:
            self._error("Unclosed backtick command substitution")
        elif self.state in (LexerState.IN_COMMAND_SUB, LexerState.IN_ARITHMETIC):
            self._error("Unclosed expansion")
        
        # Add EOF token
        self.emit_token(TokenType.EOF, '', self.get_current_position())
        
        return self.tokens