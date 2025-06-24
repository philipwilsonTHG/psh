#!/usr/bin/env python3
"""
State machine-based lexer for PSH - drop-in replacement for tokenizer.py

This lexer uses a state machine approach to solve tokenization issues:
- Preserves quote information for proper variable expansion
- Handles embedded variables in words (pre$x)
- Maintains context for operators and keywords
- Provides rich token metadata for the parser
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple, Callable
import re
import string
import unicodedata

# Import token types and new position tracking
from .token_types import TokenType, Token
from .lexer_position import (
    Position, LexerState, LexerError, RecoverableLexerError, 
    LexerConfig, LexerErrorHandler, PositionTracker
)

# Constants for character sets
VARIABLE_START_CHARS = set(string.ascii_letters + '_')
VARIABLE_CHARS = set(string.ascii_letters + string.digits + '_')
SPECIAL_VARIABLES = set('?$!#@*-') | set(string.digits)
VARIABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Escape sequences in different contexts
DOUBLE_QUOTE_ESCAPES = {
    '"': '"',
    '\\': '\\',
    '`': '`',
    'n': '\n',
    't': '\t',
    'r': '\r',
}

# Terminal characters for word boundaries
WORD_TERMINATORS = set(' \t\n|<>;&(){}\'"\n')  # [ and ] removed - handled specially
WORD_TERMINATORS_IN_BRACKETS = set(' \t\n|<>;&(){}\'"\n')  # ] handled specially


# Unicode-aware character classification functions
def is_identifier_start(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character can start an identifier (variable name).
    
    Args:
        char: Character to check
        posix_mode: If True, restrict to POSIX ASCII characters
        
    Returns:
        True if character can start an identifier
    """
    if posix_mode:
        # POSIX mode: ASCII letters and underscore only
        return char in string.ascii_letters or char == '_'
    else:
        # Unicode mode: Unicode letters and underscore
        if char == '_':
            return True
        if len(char) != 1:
            return False
        # Check if it's a Unicode letter
        category = unicodedata.category(char)
        return category.startswith('L')  # L* categories are letters


def is_identifier_char(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character can be part of an identifier (after the first character).
    
    Args:
        char: Character to check  
        posix_mode: If True, restrict to POSIX ASCII characters
        
    Returns:
        True if character can be part of an identifier
    """
    if posix_mode:
        # POSIX mode: ASCII letters, digits, and underscore
        return char in string.ascii_letters or char in string.digits or char == '_'
    else:
        # Unicode mode: Unicode letters, numbers, marks, and underscore
        if char == '_':
            return True
        if len(char) != 1:
            return False
        # Check Unicode categories
        category = unicodedata.category(char)
        return (category.startswith('L') or    # Letters
                category.startswith('N') or    # Numbers  
                category.startswith('M'))      # Marks (combining characters)


def is_whitespace(char: str, posix_mode: bool = False) -> bool:
    """
    Check if character is whitespace.
    
    Args:
        char: Character to check
        posix_mode: If True, restrict to ASCII whitespace
        
    Returns:
        True if character is whitespace
    """
    if posix_mode:
        # POSIX mode: ASCII whitespace only
        return char in ' \t\n\r\f\v'
    else:
        # Unicode mode: Unicode whitespace
        if len(char) != 1:
            return False
        # Use Unicode whitespace classification
        category = unicodedata.category(char)
        return category.startswith('Z') or char in '\t\n\r\f\v'


def normalize_identifier(name: str, posix_mode: bool = False, case_sensitive: bool = True) -> str:
    """
    Normalize an identifier name according to configuration.
    
    Args:
        name: Identifier name to normalize
        posix_mode: If True, don't apply Unicode normalization
        case_sensitive: If False, convert to lowercase
        
    Returns:
        Normalized identifier name
    """
    if not posix_mode:
        # Apply Unicode normalization (NFC - Canonical Composition)
        name = unicodedata.normalize('NFC', name)
    
    if not case_sensitive:
        name = name.lower()
        
    return name


def validate_identifier(name: str, posix_mode: bool = False) -> bool:
    """
    Validate that a string is a valid identifier.
    
    Args:
        name: Identifier name to validate
        posix_mode: If True, use POSIX validation rules
        
    Returns:
        True if the name is a valid identifier
    """
    if not name:
        return False
        
    # Check first character
    if not is_identifier_start(name[0], posix_mode):
        return False
        
    # Check remaining characters  
    for char in name[1:]:
        if not is_identifier_char(char, posix_mode):
            return False
            
    return True


@dataclass
class TokenPart:
    """Represents a part of a composite token with metadata."""
    value: str
    quote_type: Optional[str] = None  # None, "'", or '"'
    is_variable: bool = False
    is_expansion: bool = False
    start_pos: Position = field(default_factory=lambda: Position(0, 1, 1))
    end_pos: Position = field(default_factory=lambda: Position(0, 1, 1))


@dataclass
class RichToken(Token):
    """Enhanced token with metadata about its parts."""
    parts: List[TokenPart] = field(default_factory=list)
    is_composite: bool = False
    
    @classmethod
    def from_token(cls, token: Token, parts: Optional[List[TokenPart]] = None) -> 'RichToken':
        """Create RichToken from regular Token."""
        return cls(
            type=token.type,
            value=token.value,
            position=token.position,
            end_position=token.end_position,
            quote_type=token.quote_type,
            parts=parts or [],
            is_composite=bool(parts and len(parts) > 1)
        )


class StateMachineLexer:
    """State machine-based lexer for shell tokenization."""
    
    # Operators organized by length for efficient lookup
    OPERATORS_BY_LENGTH = {
        4: {'2>&1': TokenType.REDIRECT_DUP},
        3: {
            '<<<': TokenType.HERE_STRING,
            '2>>': TokenType.REDIRECT_ERR_APPEND,
            ';;&': TokenType.AMP_SEMICOLON,
            '<<-': TokenType.HEREDOC_STRIP,
        },
        2: {
            '((': TokenType.DOUBLE_LPAREN,
            '[[': TokenType.DOUBLE_LBRACKET,
            ']]': TokenType.DOUBLE_RBRACKET,
            '<<': TokenType.HEREDOC,
            '>>': TokenType.REDIRECT_APPEND,
            '&&': TokenType.AND_AND,
            '||': TokenType.OR_OR,
            ';;': TokenType.DOUBLE_SEMICOLON,
            ';&': TokenType.SEMICOLON_AMP,
            '=~': TokenType.REGEX_MATCH,
            '>&': TokenType.REDIRECT_DUP,
            '2>': TokenType.REDIRECT_ERR,
        },
        1: {
            '|': TokenType.PIPE,
            '<': TokenType.REDIRECT_IN,
            '>': TokenType.REDIRECT_OUT,
            ';': TokenType.SEMICOLON,
            '&': TokenType.AMPERSAND,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '!': TokenType.EXCLAMATION,
            '\n': TokenType.NEWLINE,
        }
    }
    
    # Keywords that need context checking
    KEYWORDS = {
        'if', 'then', 'else', 'elif', 'fi',
        'while', 'do', 'done',
        'for', 'in',
        'case', 'esac',
        'select',
        'function',
        'break', 'continue'
    }
    
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
            content = self.read_balanced_double_parens()
            return TokenPart(
                value='$((' + content + '))',
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
            content = self.read_balanced_parens()
            return TokenPart(
                value='$(' + content + ')',
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
    
    def handle_normal_state(self) -> None:
        """Handle tokenization in normal state."""
        char = self.current_char()
        
        # Check for process substitution first (before other operators)
        if char in '<>' and self.peek_char() == '(':
            self.handle_process_substitution()
            return
        
        # Check for operators (including newline before general whitespace)
        operator = self._check_for_operator()
        if operator:
            self._handle_operator(operator)
            return
        
        # Skip whitespace (Unicode-aware) - but only non-operator whitespace
        if char and is_whitespace(char, self.config.posix_mode):
            # Skip all consecutive whitespace
            while self.current_char() and is_whitespace(self.current_char(), self.config.posix_mode):
                self.advance()
            return
        
        # Handle quotes (if enabled)
        if char == '"' and self.config.enable_double_quotes:
            self.token_start_pos = self.get_current_position()
            self.state = LexerState.IN_DOUBLE_QUOTE
            self.advance()  # Skip opening quote
            return
        elif char == '\'' and self.config.enable_single_quotes:
            self.token_start_pos = self.get_current_position()
            self.state = LexerState.IN_SINGLE_QUOTE
            self.advance()  # Skip opening quote
            return
        
        # Handle variables (if enabled)
        if char == '$' and self.config.enable_variable_expansion:
            self.handle_dollar()
            return
        
        # Handle comments
        if char == '#' and self._is_comment_start():
            self.state = LexerState.IN_COMMENT
            self.advance()
            return
        
        # Handle backticks (if enabled)
        if char == '`' and self.config.enable_backtick_quotes:
            self.token_start_pos = self.get_current_position()
            self.state = LexerState.IN_BACKTICK
            self.advance()
            return
        
        # Start reading a word
        self.token_start_pos = self.get_current_position()
        self.state = LexerState.IN_WORD
    
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
        for length in sorted(self.OPERATORS_BY_LENGTH.keys(), reverse=True):
            if length > len(self.input) - self.position:
                continue
            
            op = self.peek_string(length)
            if op in self.OPERATORS_BY_LENGTH[length]:
                token_type = self.OPERATORS_BY_LENGTH[length][op]
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
    
    def _handle_operator(self, operator: Tuple[str, TokenType]) -> None:
        """Handle an operator token with special cases."""
        op, token_type = operator
        
        # Special handling for [[ and ]]
        if op == '[[' and self.command_position:
            self.in_double_brackets += 1
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(token_type, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
        elif op == ']]' and self.in_double_brackets > 0:
            self.in_double_brackets -= 1
            current_pos = self.get_current_position()
            end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
            self.emit_token(token_type, op, current_pos, end_pos=end_pos)
            self.advance(len(op))
        elif op == '=~':
            if self.in_double_brackets > 0:
                # =~ is only an operator inside [[ ]]
                current_pos = self.get_current_position()
                end_pos = Position(current_pos.offset + len(op), current_pos.line, current_pos.column + len(op))
                self.emit_token(token_type, op, current_pos, end_pos=end_pos)
                self.advance(len(op))
                self.after_regex_match = True  # Set flag for regex pattern parsing
            else:
                # Outside [[ ]], treat as word
                self.token_start_pos = self.get_current_position()
                self.state = LexerState.IN_WORD
        elif op in ('<', '>') and self.in_double_brackets > 0:
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
    
    def _is_comment_start(self) -> bool:
        """Check if # at current position starts a comment."""
        return self.position == 0 or self.input[self.position - 1] in ' \t\n;'
    
    def _error(self, message: str) -> bool:
        """Handle error with current position."""
        return self.error_handler.handle_error(self, message)
        
    def _format_error(self, message: str, position: int) -> str:
        """Format an error message with context from the input (legacy compatibility)."""
        pos_obj = self.position_tracker.get_position_at_offset(position)
        error = LexerError(message, pos_obj, self.input)
        return str(error)
    
    def handle_dollar(self) -> None:
        """Handle $ character - variables, command sub, arithmetic."""
        start_pos = self.get_current_position()
        
        # Look ahead to determine what follows the $
        next_char = self.peek_char()
        
        if next_char == '(':
            if self.peek_char(2) == '(':
                # Arithmetic expansion $((
                self.token_start_pos = start_pos
                self.advance(3)  # Skip $((
                self.state = LexerState.IN_ARITHMETIC
                self.paren_depth = 2
            else:
                # Command substitution $(
                self.token_start_pos = start_pos
                self.advance(2)  # Skip $(
                self.state = LexerState.IN_COMMAND_SUB
                self.paren_depth = 1
        elif next_char == '{':
            # Brace variable ${
            self.token_start_pos = start_pos
            self.advance(2)  # Skip ${
            self.state = LexerState.IN_BRACE_VAR
        elif self._can_start_variable_with_char(next_char):
            # Simple variable - only if next char can start a variable
            self.token_start_pos = start_pos
            self.advance()  # Skip $
            self.state = LexerState.IN_VARIABLE
        else:
            # Not a valid variable, treat $ as literal word
            self.token_start_pos = start_pos
            self.state = LexerState.IN_WORD
    
    def _can_start_variable_with_char(self, char: Optional[str]) -> bool:
        """Check if the given character can start a variable name."""
        if not char:
            # At end of input, $ should be treated as literal
            return False
        
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
    
    def handle_word_state(self) -> None:
        """Handle reading a word, which may contain embedded variables."""
        parts = self._read_word_parts(quote_context=None)
        
        # Build complete word value
        full_value = self._build_token_value(parts)
        
        # Check if it's a keyword
        token_type = TokenType.WORD
        if full_value in self.KEYWORDS and self.is_keyword_context(full_value):
            token_type = getattr(TokenType, full_value.upper())
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(token_type, full_value, self.token_start_pos)
        self.state = LexerState.NORMAL
        
        # Reset after_regex_match flag after consuming the regex pattern
        if self.after_regex_match:
            self.after_regex_match = False
    
    def _read_word_parts(self, quote_context: Optional[str]) -> List[TokenPart]:
        """Read parts of a word, handling embedded variables and expansions."""
        parts: List[TokenPart] = []
        word_start_pos = self.get_current_position()
        current_value = ""
        
        while self.current_char():
            char = self.current_char()
            
            # Check for word terminators
            if self._is_word_terminator(char):
                break
            
            # Check for embedded variable or expansion
            if char == '$':
                # Save current word part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_context,
                        is_variable=False,
                        start_pos=word_start_pos,
                        end_pos=self.get_current_position()
                    ))
                    current_value = ""
                
                # Parse the variable/expansion
                self.advance()  # Skip $
                part = self.parse_variable_or_expansion(quote_context)
                parts.append(part)
                word_start_pos = self.get_current_position()
            
            # Check for backslash escapes
            elif char == '\\' and self.peek_char():
                escaped = self.handle_escape_sequence(quote_context)
                current_value += escaped
                # Note: handle_escape_sequence already advanced past both backslash and escaped char
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=quote_context,
                is_variable=False,
                start_pos=word_start_pos,
                end_pos=self.get_current_position()
            ))
        
        return parts
    
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
            if self.state == LexerState.IN_WORD and self.position > self.token_start_pos.offset:
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
    
    def _process_quoted_string(self, quote_char: str, allow_expansions: bool) -> None:
        """
        Unified helper for processing quoted strings.
        
        Args:
            quote_char: The quote character ('"' or "'")
            allow_expansions: Whether to process variable/command expansions
        """
        if allow_expansions:
            # Use complex parsing for double quotes
            parts = self._read_quoted_parts(quote_char)
        else:
            # Simple literal parsing for single quotes
            parts = self._read_literal_quoted_content(quote_char)
        
        # Ensure closing quote is present
        error_msg = f"Unclosed {'double' if quote_char == '\"' else 'single'} quote"
        self._validate_closing_character(quote_char, error_msg)
        
        # Build complete string value
        full_value = self._build_token_value(parts)
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(TokenType.STRING, full_value, self.token_start_pos, quote_char)
        self.state = LexerState.NORMAL

    def handle_double_quote_state(self) -> None:
        """Handle reading inside double quotes with variable expansion."""
        self._process_quoted_string('"', allow_expansions=True)
    
    def _read_quoted_parts(self, quote_char: str) -> List[TokenPart]:
        """Read parts inside quotes, handling expansions in double quotes."""
        parts: List[TokenPart] = []
        quote_start_pos = self.get_current_position()
        current_value = ""
        
        while self.current_char() and self.current_char() != quote_char:
            char = self.current_char()
            
            # Variable expansion only in double quotes
            if quote_char == '"' and char == '$':
                # Save current part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_char,
                        is_variable=False,
                        start_pos=quote_start_pos,
                        end_pos=self.get_current_position()
                    ))
                    current_value = ""
                
                # Parse the variable/expansion
                self.advance()  # Skip $
                part = self.parse_variable_or_expansion(quote_char)
                parts.append(part)
                quote_start_pos = self.get_current_position()
            
            # Backslash escapes
            elif char == '\\' and self.peek_char():
                escaped = self.handle_escape_sequence(quote_char)
                current_value += escaped
                # Note: handle_escape_sequence already advanced past both backslash and escaped char
            
            # Backtick command substitution (only in double quotes)
            elif quote_char == '"' and char == '`':
                # Save current part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_char,
                        is_variable=False,
                        start_pos=quote_start_pos,
                        end_pos=self.get_current_position()
                    ))
                    current_value = ""
                
                # Parse backtick substitution
                backtick_part = self._parse_backtick_substitution(quote_char)
                parts.append(backtick_part)
                quote_start_pos = self.get_current_position()
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=quote_char,
                is_variable=False,
                start_pos=quote_start_pos,
                end_pos=self.get_current_position()
            ))
        
        return parts
    
    def _read_literal_quoted_content(self, quote_char: str) -> List[TokenPart]:
        """
        Read literal content inside quotes (for single quotes).
        
        Args:
            quote_char: The quote character
            
        Returns:
            List containing a single TokenPart with the literal content
        """
        value = ""
        start_pos = Position(
            self.token_start_pos.offset + 1,  # Skip opening quote
            self.token_start_pos.line,
            self.token_start_pos.column + 1
        )
        
        while self.current_char() and self.current_char() != quote_char:
            value += self.current_char()
            self.advance()
        
        end_pos = self.get_current_position()
        
        return [TokenPart(
            value=value,
            quote_type=quote_char,
            is_variable=False,
            is_expansion=False,
            start_pos=start_pos,
            end_pos=end_pos
        )]
    
    def _parse_backtick_substitution(self, quote_context: Optional[str]) -> TokenPart:
        """Parse backtick command substitution."""
        start_pos = self.get_current_position()
        self.advance()  # Skip opening `
        
        content = ""
        while self.current_char() and self.current_char() != '`':
            if self.current_char() == '\\' and self.peek_char() in '`$\\':
                self.advance()  # Skip backslash
            if self.current_char():
                content += self.current_char()
                self.advance()
        
        if self.current_char() == '`':
            self.advance()  # Skip closing `
        else:
            self._error("Unclosed backtick command substitution")
        
        return TokenPart(
            value='`' + content + '`',
            quote_type=quote_context,
            is_expansion=True,
            start_pos=start_pos,
            end_pos=self.get_current_position()
        )
    
    def handle_single_quote_state(self) -> None:
        """Handle reading inside single quotes (no expansion)."""
        self._process_quoted_string("'", allow_expansions=False)
    
    def handle_variable_state(self) -> None:
        """Handle reading a simple variable name with Unicode support."""
        var_name = self.read_variable_name()
        
        # If no valid variable name found, we have an isolated $
        # This could happen in POSIX mode with Unicode chars
        if not var_name:
            # Emit empty variable for now (TODO: improve to treat $ as literal)
            self.emit_token(TokenType.VARIABLE, '', self.token_start_pos)
        else:
            self.emit_token(TokenType.VARIABLE, var_name, self.token_start_pos)
            
        self.state = LexerState.NORMAL
    
    def handle_brace_var_state(self) -> None:
        """Handle reading ${...} variable."""
        var_content = ""
        brace_closed = False
        
        while self.current_char() and self.current_char() != '}':
            var_content += self.current_char()
            self.advance()
        
        if self.current_char() == '}':
            self.advance()
            brace_closed = True
        
        # Check if brace was closed
        if not brace_closed:
            self._error("Unclosed brace expansion")
        
        self.emit_token(TokenType.VARIABLE, '{' + var_content + '}', self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_command_sub_state(self) -> None:
        """Handle reading $(...) command substitution."""
        content = self.read_balanced_parens()
        # Include the $( and ) in the token value to match original tokenizer
        self.emit_token(TokenType.COMMAND_SUB, '$(' + content + ')', self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_arithmetic_state(self) -> None:
        """Handle reading $((...)) arithmetic expansion."""
        content = self.read_balanced_double_parens()
        # Include the $(( and )) in the token value to match original tokenizer
        self.emit_token(TokenType.ARITH_EXPANSION, '$((' + content + '))', self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_backtick_state(self) -> None:
        """Handle reading `...` backtick substitution."""
        value = ""
        backtick_closed = False
        
        while self.current_char() and self.current_char() != '`':
            if self.current_char() == '\\' and self.peek_char() in '`$\\':
                self.advance()  # Skip backslash
            if self.current_char():
                value += self.current_char()
                self.advance()
        
        # Skip closing backtick
        if self.current_char() == '`':
            self.advance()
            backtick_closed = True
        
        # Check if backtick was closed
        if not backtick_closed:
            self._error("Unclosed backtick command substitution")
        
        # Include the backticks in the token value to match original tokenizer
        self.emit_token(TokenType.COMMAND_SUB_BACKTICK, '`' + value + '`', self.token_start_pos)
        self.state = LexerState.NORMAL
    
    def handle_comment_state(self) -> None:
        """Handle reading a comment."""
        while self.current_char() and self.current_char() != '\n':
            self.advance()
        self.state = LexerState.NORMAL
    
    def handle_process_substitution(self) -> None:
        """Handle <(...) or >(...) process substitution."""
        token_type = TokenType.PROCESS_SUB_IN if self.current_char() == '<' else TokenType.PROCESS_SUB_OUT
        start_pos = self.get_current_position()
        prefix = self.current_char()  # < or >
        
        self.advance()  # Skip < or >
        self.advance()  # Skip (
        
        content = self.read_balanced_parens()
        # Include the full syntax in the token value to match original tokenizer
        self.emit_token(token_type, prefix + '(' + content + ')', start_pos)
    
    def read_balanced_parens(self) -> str:
        """Read content until balanced parentheses."""
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
        
        # Check if we hit EOF with unbalanced parens
        if depth > 0:
            self._error("Unclosed parenthesis")
            
        return content
    
    def read_balanced_double_parens(self) -> str:
        """Read content until balanced double parentheses for arithmetic."""
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
        
        # Check if we found the closing )) or hit EOF
        if not found_closing:
            self._error("Unclosed arithmetic expansion")
            
        return content
    
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
            # Dispatch based on current state
            if self.state == LexerState.NORMAL:
                self.handle_normal_state()
            elif self.state == LexerState.IN_WORD:
                self.handle_word_state()
            elif self.state == LexerState.IN_DOUBLE_QUOTE:
                self.handle_double_quote_state()
            elif self.state == LexerState.IN_SINGLE_QUOTE:
                self.handle_single_quote_state()
            elif self.state == LexerState.IN_VARIABLE:
                self.handle_variable_state()
            elif self.state == LexerState.IN_BRACE_VAR:
                self.handle_brace_var_state()
            elif self.state == LexerState.IN_COMMAND_SUB:
                self.handle_command_sub_state()
            elif self.state == LexerState.IN_ARITHMETIC:
                self.handle_arithmetic_state()
            elif self.state == LexerState.IN_BACKTICK:
                self.handle_backtick_state()
            elif self.state == LexerState.IN_COMMENT:
                self.handle_comment_state()
            else:
                # Shouldn't happen, but recover
                self.advance()
        
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


def tokenize(input_string: str) -> List[Token]:
    """
    Drop-in replacement for the existing tokenize function.
    
    This maintains the same interface but uses the state machine lexer
    for better tokenization with preserved context.
    """
    from .brace_expansion import BraceExpander, BraceExpansionError
    from .token_transformer import TokenTransformer
    
    try:
        # Expand braces first (same as original)
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError as e:
        # If brace expansion fails, use original string
        lexer = StateMachineLexer(input_string)
        tokens = lexer.tokenize()
    else:
        # Run state machine lexer on expanded string
        lexer = StateMachineLexer(expanded_string)
        tokens = lexer.tokenize()
    
    # Apply token transformations (same as original)
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)
    
    return tokens