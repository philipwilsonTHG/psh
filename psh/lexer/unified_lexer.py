"""Unified lexer using quote and expansion parsers."""

import re
from typing import List, Optional, Tuple
from ..token_types import Token, TokenType
from .position import (
    LexerConfig, LexerState, PositionTracker, LexerErrorHandler, Position
)
from .constants import KEYWORDS, SPECIAL_VARIABLES
from .unicode_support import normalize_identifier
from .helpers import LexerHelpers
from .enhanced_state_handlers import EnhancedStateHandlers
from .token_parts import TokenPart, RichToken
from .state_context import LexerContext
from .transitions import StateManager, TransitionTable
from .quote_parser import UnifiedQuoteParser, QuoteParsingContext
from .expansion_parser import ExpansionParser, ExpansionContext

# Legacy pattern for compatibility
VARIABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


class UnifiedLexer(LexerHelpers):
    """
    Unified lexer using quote and expansion parsers.
    
    This lexer uses the unified quote and expansion parsers to handle
    all forms of shell quoting and expansion in a consistent manner.
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
        
        # Unified parsers
        self.expansion_parser = ExpansionParser(self.config)
        self.quote_parser = UnifiedQuoteParser(self.expansion_parser)
        
        # Parsing contexts
        self.quote_context = QuoteParsingContext(
            input_string, self.position_tracker, self.config
        )
        self.expansion_context = ExpansionContext(
            input_string, self.config, self.position_tracker
        )
        
        # Enhanced state handlers
        self.state_handlers_enhanced = EnhancedStateHandlers()
        self.state_handlers_enhanced.setup_parsers(self)
        
        # State handler dispatch table for O(1) lookup
        self.state_handlers = {
            LexerState.NORMAL: self.state_handlers_enhanced.handle_normal_state,
            LexerState.IN_WORD: self.state_handlers_enhanced.handle_word_state,
            LexerState.IN_DOUBLE_QUOTE: lambda: self.state_handlers_enhanced.handle_quote_state(self, '"'),
            LexerState.IN_SINGLE_QUOTE: lambda: self.state_handlers_enhanced.handle_quote_state(self, "'"),
            LexerState.IN_BACKTICK: lambda: self.state_handlers_enhanced.handle_quote_state(self, '`'),
            LexerState.IN_COMMENT: self.state_handlers_enhanced.handle_comment_state,
            # Legacy handlers for compatibility
            LexerState.IN_VARIABLE: self.handle_variable_state,
            LexerState.IN_BRACE_VAR: self.handle_brace_var_state,
            LexerState.IN_COMMAND_SUB: self.handle_command_sub_state,
            LexerState.IN_ARITHMETIC: self.handle_arithmetic_state,
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
    
    # Legacy state handlers for compatibility
    def handle_variable_state(self) -> None:
        """Handle reading a simple variable name (legacy compatibility)."""
        # Use expansion parser
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            self.position - 1  # Back up to include the $
        )
        
        self.position = new_pos
        
        if expansion_part.value:
            self.emit_token(TokenType.VARIABLE, expansion_part.value, self.token_start_pos)
        else:
            # Empty variable
            self.emit_token(TokenType.VARIABLE, '', self.token_start_pos)
        
        self.state = LexerState.NORMAL
    
    def handle_brace_var_state(self) -> None:
        """Handle reading ${...} variable (legacy compatibility)."""
        # Use expansion parser for consistency
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            self.position - 2  # Back up to include the ${
        )
        
        self.position = new_pos
        self.emit_token(TokenType.VARIABLE, expansion_part.value, self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_command_sub_state(self) -> None:
        """Handle reading $(...) command substitution (legacy compatibility)."""
        # Use expansion parser for consistency
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            self.position - 2  # Back up to include the $(
        )
        
        self.position = new_pos
        self.emit_token(TokenType.COMMAND_SUB, expansion_part.value, self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_arithmetic_state(self) -> None:
        """Handle reading $((...)) arithmetic expansion (legacy compatibility)."""
        # Use expansion parser for consistency
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            self.position - 3  # Back up to include the $((
        )
        
        self.position = new_pos
        self.emit_token(TokenType.ARITH_EXPANSION, expansion_part.value, self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_process_substitution(self) -> None:
        """Handle <(...) or >(...) process substitution."""
        token_type = TokenType.PROCESS_SUB_IN if self.current_char() == '<' else TokenType.PROCESS_SUB_OUT
        start_pos = self.get_current_position()
        prefix = self.current_char()  # < or >
        
        self.advance()  # Skip < or >
        self.advance()  # Skip (
        
        content, is_closed = self.read_balanced_parens()
        # Include the full syntax in the token value
        if is_closed:
            token_value = prefix + '(' + content + ')'
        else:
            token_value = prefix + '(' + content
        self.emit_token(token_type, token_value, start_pos)
    
    def _handle_operator(self, operator: Tuple[str, TokenType]) -> None:
        """Handle an operator token with special cases."""
        op, token_type = operator
        
        # Special handling for [[ and ]]
        if op == '[[' and self.command_position:
            self.context.bracket_depth += 1
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(token_type, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
        elif op == ']]' and self.context.bracket_depth > 0:
            self.context.bracket_depth -= 1
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(token_type, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
        elif op == '=~':
            if self.context.bracket_depth > 0:
                # =~ is only an operator inside [[ ]]
                current_pos = self.get_current_position()
                end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
                self.emit_token(token_type, op, current_pos, end_pos=end_pos)
                self.advance(len(op))
                self.context.after_regex_match = True  # Set flag for regex pattern parsing
            else:
                # Outside [[ ]], treat as word
                self.context.token_start_offset = self.position
                self.state = LexerState.IN_WORD
        elif op in ('<', '>') and self.context.bracket_depth > 0:
            # Inside [[ ]], < and > are comparison operators, not redirections
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(TokenType.WORD, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
        else:
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(token_type, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
    
    # Token emission and parsing context management
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
        """Create a token, potentially with parts."""
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
        """Update command position tracking based on token type."""
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
    
    def is_keyword_context(self, word: str) -> bool:
        """Check if a word should be treated as a keyword based on context."""
        # Additional context checks for specific keywords
        if word == 'in':
            # 'in' is definitely a keyword after 'for variable' or 'case expr'
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
        
        # 'esac' can appear after ;; or at start of line
        if word == 'esac':
            if len(self.tokens) > 0:
                last_token = self.tokens[-1]
                if last_token.type in (TokenType.DOUBLE_SEMICOLON, TokenType.SEMICOLON_AMP, 
                                     TokenType.AMP_SEMICOLON, TokenType.NEWLINE):
                    return True
            return self.command_position
        
        # Other keywords are only recognized at command position
        if not self.command_position:
            return False
        
        return True
    
    def tokenize(self) -> List[Token]:
        """Main tokenization method using unified parsers."""
        while self.position < len(self.input) or self.state != LexerState.NORMAL:
            # Use dispatch table for O(1) state handler lookup
            handler = self.state_handlers.get(self.state)
            if handler:
                if self.state in (LexerState.NORMAL, LexerState.IN_WORD, LexerState.IN_COMMENT):
                    handler(self)
                else:
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