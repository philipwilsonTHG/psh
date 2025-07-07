"""Enhanced core lexer implementation with unified state management."""

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
from .state_context import LexerContext
from .transitions import StateManager, TransitionTable

# Legacy pattern for compatibility
VARIABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class EnhancedStateMachineLexer(LexerHelpers, StateHandlers):
    """
    Enhanced state machine-based lexer with unified state management.
    
    This version uses LexerContext for unified state tracking and explicit
    state transitions, while maintaining backward compatibility with the
    existing interface.
    """
    
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        self.input = input_string
        self.config = config or LexerConfig()
        self.tokens: List[Token] = []
        
        # Unified state management
        self.state_manager = StateManager()
        self.context = self.state_manager.context
        
        # Position tracking
        self.position_tracker = PositionTracker(input_string)
        
        # Error handling
        self.error_handler = LexerErrorHandler(self.config)
        
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
    
    # Backward compatibility properties
    @property
    def state(self) -> LexerState:
        """Get current lexer state (backward compatibility)."""
        return self.context.state
    
    @state.setter
    def state(self, value: LexerState) -> None:
        """Set lexer state (backward compatibility)."""
        self.context.state = value
    
    @property
    def in_double_brackets(self) -> int:
        """Get double bracket depth (backward compatibility)."""
        return self.context.bracket_depth
    
    @in_double_brackets.setter
    def in_double_brackets(self, value: int) -> None:
        """Set double bracket depth (backward compatibility)."""
        self.context.bracket_depth = value
    
    @property
    def paren_depth(self) -> int:
        """Get parentheses depth (backward compatibility)."""
        return self.context.paren_depth
    
    @paren_depth.setter
    def paren_depth(self, value: int) -> None:
        """Set parentheses depth (backward compatibility)."""
        self.context.paren_depth = value
    
    @property
    def command_position(self) -> bool:
        """Get command position flag (backward compatibility)."""
        return self.context.command_position
    
    @command_position.setter
    def command_position(self, value: bool) -> None:
        """Set command position flag (backward compatibility)."""
        self.context.command_position = value
    
    @property
    def after_regex_match(self) -> bool:
        """Get after regex match flag (backward compatibility)."""
        return self.context.after_regex_match
    
    @after_regex_match.setter
    def after_regex_match(self, value: bool) -> None:
        """Set after regex match flag (backward compatibility)."""
        self.context.after_regex_match = value
    
    @property
    def current_parts(self) -> List[TokenPart]:
        """Get current token parts (backward compatibility)."""
        return self.context.current_token_parts
    
    @current_parts.setter
    def current_parts(self, value: List[TokenPart]) -> None:
        """Set current token parts (backward compatibility)."""
        self.context.current_token_parts = value
    
    @property
    def token_start_pos(self) -> Position:
        """Get token start position (backward compatibility)."""
        return self.position_tracker.get_position_at_offset(self.context.token_start_offset)
    
    @token_start_pos.setter
    def token_start_pos(self, value: Position) -> None:
        """Set token start position (backward compatibility)."""
        self.context.token_start_offset = value.offset
    
    @property
    def heredoc_delimiters(self) -> List[str]:
        """Get heredoc delimiters (backward compatibility)."""
        return self.context.heredoc_delimiters
    
    @heredoc_delimiters.setter
    def heredoc_delimiters(self, value: List[str]) -> None:
        """Set heredoc delimiters (backward compatibility)."""
        self.context.heredoc_delimiters = value
    
    # Position management
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
    
    # Enhanced state management methods
    def try_state_transition(self) -> bool:
        """
        Try to apply an automatic state transition based on current input.
        
        Returns:
            True if a transition was applied, False otherwise
        """
        current_char = self.current_char()
        if current_char is None:
            return False
        
        return self.state_manager.try_transition(
            current_char, self.position, self.input
        )
    
    def get_state_summary(self) -> str:
        """Get a human-readable summary of the current state."""
        return str(self.context)
    
    def get_nesting_info(self) -> dict:
        """Get information about current nesting levels."""
        return self.context.get_nesting_summary()
    
    def is_in_nested_context(self) -> bool:
        """Check if we're inside any nested structure."""
        return self.context.is_in_nested_structure()
    
    # Enhanced error handling with context
    def _error_with_context(self, message: str) -> bool:
        """Handle error with enhanced context information."""
        context_info = f" (context: {self.get_state_summary()})"
        return self.error_handler.handle_error(self, message + context_info)
    
    # Variable parsing with Unicode support (existing method)
    def parse_variable_or_expansion(self, quote_context: Optional[str] = None) -> TokenPart:
        """
        Parse a variable or expansion starting after the $.
        
        Args:
            quote_context: The quote type if inside quotes ('\"', \"'\", or None)
            
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
            
            # Update context for arithmetic
            self.context.enter_arithmetic()
            self.advance(2)  # Skip ((
            content, is_closed = self.read_balanced_double_parens()
            if is_closed:
                token_value = '$((' + content + '))'
                self.context.exit_arithmetic()
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
            
            # Update context for command substitution
            self.context.enter_parentheses()
            self.advance()  # Skip (
            content, is_closed = self.read_balanced_parens()
            if is_closed:
                token_value = '$(' + content + ')'
                self.context.exit_parentheses()
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
        
        # Update context for brace expansion
        self.context.enter_brace_expansion()
        self.advance()  # Skip {
        var_content = self.read_until_char('}')
        
        if self._validate_closing_character('}', "Unclosed variable expansion"):
            self.context.exit_brace_expansion()
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
    
    # Token emission with context awareness
    def emit_token(self, token_type: TokenType, value: str, start_pos: Optional[Position] = None,
                   quote_type: Optional[str] = None, end_pos: Optional[Position] = None) -> None:
        """Emit a token with current parts and context updates."""
        if start_pos is None:
            start_pos = self.token_start_pos
        if end_pos is None:
            end_pos = self.get_current_position()
            
        # Create and add the token
        token = self._create_token(token_type, value, start_pos, end_pos, quote_type)
        self.tokens.append(token)
        
        # Update parsing context using unified context
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
        Update command position tracking based on token type using unified context.
        
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
            self.context.set_command_position()
        elif token_type not in neutral_tokens:
            self.context.reset_command_position()
    
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
            # For now, skip automatic transitions and use existing handlers
            # TODO: Integrate automatic transitions in Phase 2
            # if not self.try_state_transition():
            
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