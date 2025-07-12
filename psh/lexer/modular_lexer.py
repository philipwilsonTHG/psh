"""Modular lexer using the token recognizer system."""

from typing import List, Optional, Tuple
from ..token_types import Token, TokenType
from .position import LexerConfig, LexerState, PositionTracker, Position
from .state_context import LexerContext
from .transitions import StateManager
from .token_parts import TokenPart, RichToken
from .recognizers import RecognizerRegistry, setup_default_recognizers
from .quote_parser import UnifiedQuoteParser, QuoteParsingContext
from .expansion_parser import ExpansionParser, ExpansionContext


class ModularLexer:
    """
    Modular lexer using pluggable token recognizers.
    
    This lexer combines the unified quote/expansion parsing from Phase 3
    with the modular token recognition system from Phase 4.
    """
    
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        """
        Initialize the modular lexer.
        
        Args:
            input_string: The input string to tokenize
            config: Optional lexer configuration
        """
        self.input = input_string
        self.config = config or LexerConfig()
        self.tokens: List[Token] = []
        
        # Position tracking
        self.position_tracker = PositionTracker(input_string)
        
        # State management
        self.state_manager = StateManager()
        self.context = self.state_manager.context
        
        # Set posix_mode in context from config
        self.context.posix_mode = self.config.posix_mode
        
        # Token recognizer system
        self.registry = RecognizerRegistry()
        self._setup_recognizers()
        
        # Unified parsers for quotes and expansions
        self.expansion_parser = ExpansionParser(self.config)
        self.quote_parser = UnifiedQuoteParser(self.expansion_parser)
        
        # Parsing contexts
        self.quote_context = QuoteParsingContext(
            input_string, self.position_tracker, self.config
        )
        self.expansion_context = ExpansionContext(
            input_string, self.config, self.position_tracker
        )
        
        # Current token parts for composite tokens
        self.current_parts: List[TokenPart] = []
    
    def _setup_recognizers(self) -> None:
        """Set up the token recognizers based on configuration."""
        from .recognizers.operator import OperatorRecognizer
        from .recognizers.keyword import KeywordRecognizer
        from .recognizers.literal import LiteralRecognizer
        from .recognizers.whitespace import WhitespaceRecognizer
        from .recognizers.comment import CommentRecognizer
        from .recognizers.process_sub import ProcessSubstitutionRecognizer
        
        # Always add these core recognizers
        self.registry.register(WhitespaceRecognizer())
        self.registry.register(CommentRecognizer())
        
        # Create a custom operator recognizer that respects config
        operator_recognizer = OperatorRecognizer()
        operator_recognizer.config = self.config  # Pass config to recognizer
        self.registry.register(operator_recognizer)
        
        # Add other recognizers
        self.registry.register(KeywordRecognizer())
        
        # Create a custom literal recognizer that respects config
        literal_recognizer = LiteralRecognizer()
        literal_recognizer.config = self.config  # Pass config to recognizer
        self.registry.register(literal_recognizer)
        
        # Process substitution (if enabled in config)
        if self.config.enable_process_substitution:
            self.registry.register(ProcessSubstitutionRecognizer())
    
    # Position management
    @property
    def position(self) -> int:
        """Get current absolute position."""
        return self.position_tracker.position
    
    @position.setter
    def position(self, value: int) -> None:
        """Set absolute position."""
        diff = value - self.position_tracker.position
        if diff > 0:
            self.position_tracker.advance(diff)
        elif diff < 0:
            # Reset and advance to target
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
    
    def advance(self, count: int = 1) -> None:
        """Move position forward."""
        self.position_tracker.advance(count)
    
    def get_current_position(self) -> Position:
        """Get current position as a Position object."""
        return self.position_tracker.get_current_position()
    
    # State management
    @property
    def state(self) -> LexerState:
        """Get current lexer state."""
        return self.context.state
    
    @state.setter
    def state(self, value: LexerState) -> None:
        """Set lexer state."""
        self.context.state = value
    
    # Backward compatibility properties
    @property
    def command_position(self) -> bool:
        """Get command position flag."""
        return self.context.command_position
    
    @command_position.setter
    def command_position(self, value: bool) -> None:
        """Set command position flag."""
        self.context.command_position = value
    
    @property
    def in_double_brackets(self) -> int:
        """Get double bracket depth."""
        return self.context.bracket_depth
    
    @in_double_brackets.setter
    def in_double_brackets(self, value: int) -> None:
        """Set double bracket depth."""
        self.context.bracket_depth = value
    
    # Token emission
    def emit_token(
        self, 
        token_type: TokenType, 
        value: str, 
        start_pos: Optional[Position] = None,
        quote_type: Optional[str] = None, 
        end_pos: Optional[Position] = None
    ) -> None:
        """Emit a token with current parts and context updates."""
        if start_pos is None:
            start_pos = self.get_current_position()
        if end_pos is None:
            end_pos = self.get_current_position()
        
        # Create token
        start_offset = start_pos.offset if isinstance(start_pos, Position) else start_pos
        end_offset = end_pos.offset if isinstance(end_pos, Position) else end_pos
        
        # Extract line/column information if we have Position objects
        line = start_pos.line if isinstance(start_pos, Position) else None
        column = start_pos.column if isinstance(start_pos, Position) else None
        
        token = Token(token_type, value, start_offset, end_offset, quote_type, line, column)
        
        # Convert to RichToken if we have parts
        if self.current_parts:
            rich_token = RichToken.from_token(token, self.current_parts)
            self.current_parts = []  # Clear parts after use
            self.tokens.append(rich_token)
        else:
            self.tokens.append(token)
        
        # Update command position context
        self._update_command_position_context(token_type)
    
    def _build_token_value(self, parts: List[TokenPart]) -> str:
        """Build complete token value from parts."""
        full_value = ""
        for part in parts:
            if part.is_variable and not part.value.startswith('$'):
                # Only add $ if it's not already there (simple variables)
                full_value += '$' + part.value
            else:
                # For expansions and literals, use value as-is
                full_value += part.value
        return full_value
    
    def _update_context_for_token(self, token_type: TokenType) -> None:
        """Update lexer context based on recognized token."""
        # Update bracket depth for [[ and ]]
        if token_type == TokenType.DOUBLE_LBRACKET:
            self.context.enter_double_brackets()
        elif token_type == TokenType.DOUBLE_RBRACKET:
            self.context.exit_double_brackets()
        elif token_type == TokenType.DOUBLE_LPAREN:
            self.context.enter_arithmetic()
        elif token_type == TokenType.DOUBLE_RPAREN:
            self.context.exit_arithmetic()
        
        # Track control keywords for context-sensitive parsing
        elif token_type == TokenType.FOR:
            self.context.recent_control_keyword = 'for'
        elif token_type == TokenType.CASE:
            self.context.recent_control_keyword = 'case'
        elif token_type == TokenType.SELECT:
            self.context.recent_control_keyword = 'select'
        elif token_type in {TokenType.SEMICOLON, TokenType.DO, TokenType.THEN}:
            # Clear recent control keyword when we move to the body
            self.context.recent_control_keyword = None
    
    def _update_command_position_context(self, token_type: TokenType) -> None:
        """Update command position tracking based on token type."""
        command_starting_tokens = {
            TokenType.SEMICOLON, TokenType.AND_AND, TokenType.OR_OR,
            TokenType.PIPE, TokenType.LPAREN, TokenType.NEWLINE,
            TokenType.IF, TokenType.WHILE, TokenType.FOR, TokenType.CASE,
            TokenType.THEN, TokenType.DO, TokenType.ELSE, TokenType.ELIF,
            TokenType.LBRACE
        }
        
        neutral_tokens = {
            TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
            TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
            TokenType.REDIRECT_ERR_APPEND, TokenType.HEREDOC,
            TokenType.HEREDOC_STRIP, TokenType.HERE_STRING
        }
        
        # Update bracket depth for [[ and ]]
        if token_type == TokenType.DOUBLE_LBRACKET:
            self.context.bracket_depth += 1
        elif token_type == TokenType.DOUBLE_RBRACKET:
            self.context.bracket_depth -= 1
        elif token_type == TokenType.DOUBLE_LPAREN:
            self.context.enter_arithmetic()
        elif token_type == TokenType.DOUBLE_RPAREN:
            self.context.exit_arithmetic()
        
        if token_type in command_starting_tokens:
            self.context.set_command_position()
        elif token_type not in neutral_tokens:
            self.context.reset_command_position()
    
    # Main tokenization
    def tokenize(self) -> List[Token]:
        """Main tokenization method using modular recognizers."""
        while self.position < len(self.input):
            # Skip whitespace
            if self._skip_whitespace():
                continue
            
            # Check for end of input
            if self.position >= len(self.input):
                break
            
            # Try quotes and expansions first (from Phase 3)
            if self._try_quotes_and_expansions():
                continue
            
            # Try modular recognizers
            if self._try_recognizers():
                continue
            
            # Fallback: treat as word
            if self._handle_fallback_word():
                continue
            
            # If nothing worked, advance to avoid infinite loop
            self.advance()
        
        # Add EOF token
        self.emit_token(TokenType.EOF, '', self.get_current_position())
        
        return self.tokens
    
    def _skip_whitespace(self) -> bool:
        """Skip whitespace and return True if any was skipped."""
        start_pos = self.position
        
        while self.position < len(self.input):
            char = self.current_char()
            if not char or char == '\n':  # Stop at newlines
                break
            
            from .unicode_support import is_whitespace
            if not is_whitespace(char, self.config.posix_mode):
                break
            
            self.advance()
        
        return self.position > start_pos
    
    def _try_quotes_and_expansions(self) -> bool:
        """Try to handle quotes and expansions using unified parsers."""
        char = self.current_char()
        if not char:
            return False
        
        # Check for ANSI-C quoting $'...'
        if (char == '$' and self.position + 1 < len(self.input) and 
            self.input[self.position + 1] == "'"):
            return self._handle_ansi_c_quote()
        
        # Handle expansions (only if enabled and not in array assignment context)
        if (char == '$' and self.config.enable_variable_expansion and 
            self.expansion_context.is_expansion_start(self.position)):
            # Check if we're inside a potential array assignment - if so, let literal recognizer handle it
            if self._is_inside_potential_array_assignment():
                return False
            return self._handle_expansion()
        
        # Handle backticks (command substitution, only if enabled)
        if (char == '`' and self.config.enable_command_substitution and 
            self.expansion_context.is_expansion_start(self.position)):
            return self._handle_backtick()
        
        # Handle quotes (only if enabled)
        if char == '"' and self.config.enable_double_quotes and self.quote_context.is_quote_character(char):
            return self._handle_quote(char)
        if char == "'" and self.config.enable_single_quotes and self.quote_context.is_quote_character(char):
            return self._handle_quote(char)
        
        return False
    
    def _is_inside_potential_array_assignment(self) -> bool:
        """Check if current position is inside a potential array assignment pattern."""
        # Look backwards to see if we're inside arr[...] pattern that could be array assignment
        
        # Find the most recent unmatched opening bracket before current position
        bracket_pos = -1
        bracket_count = 0
        
        for i in range(self.position - 1, -1, -1):
            char = self.input[i]
            if char == ']':
                bracket_count += 1
            elif char == '[':
                bracket_count -= 1
                if bracket_count < 0:
                    # Found unmatched opening bracket
                    bracket_pos = i
                    break
            elif char in [' ', '\t', '\n', '\r', ';', '|', '&', '(', ')']:
                # Word boundary - stop searching
                break
        
        if bracket_pos == -1:
            return False  # No unmatched opening bracket found
        
        # Check if text before [ looks like a valid variable name
        var_start = bracket_pos - 1
        while var_start >= 0:
            char = self.input[var_start]
            if char in [' ', '\t', '\n', '\r', ';', '|', '&', '(', ')']:
                var_start += 1
                break
            var_start -= 1
        else:
            var_start = 0
        
        if var_start >= bracket_pos:
            return False  # No variable name before [
        
        var_name = self.input[var_start:bracket_pos]
        
        # Check if it's a valid variable name
        if not var_name or not var_name[0].isalpha() and var_name[0] != '_':
            return False
        if not all(c.isalnum() or c == '_' for c in var_name):
            return False
        
        # Look ahead from current position to see if this could end with ]=... pattern
        ahead_pos = self.position
        bracket_count = 1  # We're inside brackets already
        
        while ahead_pos < len(self.input):
            char = self.input[ahead_pos]
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    # Found closing bracket - check if followed by =
                    if (ahead_pos + 1 < len(self.input) and 
                        self.input[ahead_pos + 1] == '='):
                        return True
                    elif (ahead_pos + 2 < len(self.input) and 
                          self.input[ahead_pos + 1:ahead_pos + 3] == '+='):
                        return True
                    return False
            elif char in [' ', '\t', '\n', '\r']:
                return False  # Whitespace breaks the pattern
            ahead_pos += 1
        
        return False
    
    def _handle_expansion(self) -> bool:
        """Handle variable/command/arithmetic expansion."""
        start_pos = self.get_current_position()
        
        # Parse the expansion
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            self.position
        )
        
        # If it's not actually an expansion (just a literal), let other recognizers handle it
        if not expansion_part.is_expansion:
            return False
        
        # Update position
        self.position = new_pos
        
        # Emit token based on expansion type
        if expansion_part.is_variable:
            if expansion_part.expansion_type == 'parameter':
                # Strip the $ but keep the {} wrapper for parameter expansion
                value = expansion_part.value[1:] if expansion_part.value.startswith('$') else expansion_part.value
            else:
                # For simple variables, the value should already be just the variable name
                value = expansion_part.value
            self.emit_token(TokenType.VARIABLE, value, start_pos)
        else:
            # Command substitution or arithmetic
            if expansion_part.expansion_type == 'arithmetic':
                token_type = TokenType.ARITH_EXPANSION
            else:
                token_type = TokenType.COMMAND_SUB
            self.emit_token(token_type, expansion_part.value, start_pos)
        
        return True
    
    def _handle_backtick(self) -> bool:
        """Handle backtick command substitution."""
        start_pos = self.get_current_position()
        
        # Parse the backtick substitution
        backtick_part, new_pos = self.expansion_parser.parse_backtick_substitution(
            self.input, self.position
        )
        
        # Update position
        self.position = new_pos
        
        # Check for unclosed backticks
        if backtick_part.expansion_type == 'backtick_unclosed':
            # Handle error
            pass
        
        # Emit token
        self.emit_token(TokenType.COMMAND_SUB_BACKTICK, backtick_part.value, start_pos)
        return True
    
    def _handle_quote(self, quote_char: str) -> bool:
        """Handle quoted string."""
        start_pos = self.get_current_position()
        
        # Skip opening quote
        self.advance()
        
        # Get quote rules
        from .quote_parser import QUOTE_RULES
        rules = QUOTE_RULES.get(quote_char)
        if not rules:
            return False
        
        # Parse the quoted string content using unified parser
        parts, new_pos, found_closing = self.quote_parser.parse_quoted_string(
            self.input,
            self.position,  # Current position (after opening quote)
            rules,
            self.position_tracker
        )
        
        # Check if quote was closed
        if not found_closing:
            raise SyntaxError(f"Unclosed {quote_char} quote at position {start_pos}")
        
        # Update position
        self.position = new_pos
        
        # Build complete string value
        full_value = self._build_token_value(parts)
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(TokenType.STRING, full_value, start_pos, quote_char)
        return True
    
    def _handle_ansi_c_quote(self) -> bool:
        """Handle ANSI-C quoted string $'...'."""
        start_pos = self.get_current_position()
        
        # Skip $'
        self.advance()  # Skip $
        self.advance()  # Skip '
        
        # Get ANSI-C quote rules
        from .quote_parser import QUOTE_RULES
        rules = QUOTE_RULES.get("$'")
        if not rules:
            return False
        
        # Parse the ANSI-C quoted string content
        parts, new_pos, found_closing = self.quote_parser.parse_quoted_string(
            self.input,
            self.position,  # Current position (after $')
            rules,
            self.position_tracker,
            quote_type="$'"  # Pass quote type for proper escape handling
        )
        
        # Check if quote was closed
        if not found_closing:
            raise SyntaxError(f"Unclosed $' quote at position {start_pos}")
        
        # Update position
        self.position = new_pos
        
        # Build complete string value
        full_value = self._build_token_value(parts)
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token - ANSI-C quotes produce STRING tokens
        self.emit_token(TokenType.STRING, full_value, start_pos, "$'")
        return True
    
    def _try_recognizers(self) -> bool:
        """Try modular recognizers."""
        result = self.registry.recognize(self.input, self.position, self.context)
        
        if result is not None:
            token, new_pos, recognizer = result
            
            # Handle special cases where recognizers return None
            # (e.g., whitespace and comments that should be skipped)
            if token is None:
                self.position = new_pos
                return True
            
            # Update position
            old_pos = self.position
            self.position = new_pos
            
            # Add line/column information to token if missing
            if token.line is None or token.column is None:
                # Get position at token start
                start_position = self.position_tracker.get_position_at_offset(token.position)
                token.line = start_position.line
                token.column = start_position.column
            
            # Add token
            self.tokens.append(token)
            
            # Update context immediately for bracket tracking
            self._update_context_for_token(token.type)
            
            # Update command position context
            self._update_command_position_context(token.type)
            
            return True
        
        return False
    
    def _handle_fallback_word(self) -> bool:
        """Handle fallback word tokenization."""
        if self.position >= len(self.input):
            return False
        
        start_pos = self.get_current_position()
        value = ""
        
        # Read until whitespace or special character
        while self.position < len(self.input):
            char = self.current_char()
            
            # Stop at whitespace
            from .unicode_support import is_whitespace
            if is_whitespace(char, self.config.posix_mode):
                break
            
            # Stop at operators
            if char in '<>&|;(){}!':
                break
            
            # Stop at quotes and expansions
            if char in ['$', '`', '"', "'"]:
                break
            
            value += char
            self.advance()
        
        if value:
            self.emit_token(TokenType.WORD, value, start_pos)
            return True
        
        return False