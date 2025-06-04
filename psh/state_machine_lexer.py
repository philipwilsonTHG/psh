#!/usr/bin/env python3
"""
State machine-based lexer for PSH - drop-in replacement for tokenizer.py

This lexer uses a state machine approach to solve tokenization issues:
- Preserves quote information for proper variable expansion
- Handles embedded variables in words (pre$x)
- Maintains context for operators and keywords
- Provides rich token metadata for the parser
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple, Callable
import re
import string

# Import token types
from .token_types import TokenType, Token

# Constants for character sets
VARIABLE_START_CHARS = set(string.ascii_letters + '_')
VARIABLE_CHARS = set(string.ascii_letters + string.digits + '_')
SPECIAL_VARIABLES = set('?$!#@*') | set(string.digits)
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
WORD_TERMINATORS = set(' \t\n|<>;&(){}\'"\n')
WORD_TERMINATORS_IN_BRACKETS = set(' \t\n|<>;&(){}\'"\n')  # ] handled specially


class LexerState(Enum):
    """States for the lexer state machine."""
    NORMAL = auto()
    IN_WORD = auto()
    IN_SINGLE_QUOTE = auto()
    IN_DOUBLE_QUOTE = auto()
    IN_VARIABLE = auto()
    IN_COMMAND_SUB = auto()
    IN_ARITHMETIC = auto()
    IN_COMMENT = auto()
    IN_BACKTICK = auto()
    IN_BRACE_VAR = auto()  # Inside ${...}


@dataclass
class TokenPart:
    """Represents a part of a composite token with metadata."""
    value: str
    quote_type: Optional[str] = None  # None, "'", or '"'
    is_variable: bool = False
    is_expansion: bool = False
    start_pos: int = 0
    end_pos: int = 0


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
        'function',
        'break', 'continue'
    }
    
    def __init__(self, input_string: str):
        self.input = input_string
        self.position = 0
        self.tokens: List[Token] = []
        self.state = LexerState.NORMAL
        
        # Context tracking
        self.in_double_brackets = 0
        self.paren_depth = 0
        self.command_position = True
        
        # Buffer for current token being built
        self.current_parts: List[TokenPart] = []
        self.token_start = 0
        
        # Heredoc tracking
        self.heredoc_delimiters: List[str] = []
        
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
        self.position = min(self.position + count, len(self.input))
    
    
    def parse_variable_or_expansion(self, quote_context: Optional[str] = None) -> TokenPart:
        """
        Parse a variable or expansion starting after the $.
        
        Args:
            quote_context: The quote type if inside quotes ('"', "'", or None)
            
        Returns:
            TokenPart representing the parsed variable or expansion
        """
        start_pos = self.position - 1  # Include the $ in position
        
        if self.current_char() == '(':
            # Command substitution or arithmetic expansion
            if self.peek_char() == '(':
                # Arithmetic expansion $((
                self.advance(2)  # Skip ((
                content = self.read_balanced_double_parens()
                return TokenPart(
                    value='$((' + content + '))',
                    quote_type=quote_context,
                    is_expansion=True,
                    start_pos=start_pos,
                    end_pos=self.position
                )
            else:
                # Command substitution $(
                self.advance()  # Skip (
                content = self.read_balanced_parens()
                return TokenPart(
                    value='$(' + content + ')',
                    quote_type=quote_context,
                    is_expansion=True,
                    start_pos=start_pos,
                    end_pos=self.position
                )
        elif self.current_char() == '{':
            # Brace variable ${
            self.advance()  # Skip {
            var_content = self.read_until_char('}')
            if self.current_char() == '}':
                self.advance()  # Skip }
                return TokenPart(
                    value='{' + var_content + '}',
                    quote_type=quote_context,
                    is_variable=True,
                    start_pos=start_pos,
                    end_pos=self.position
                )
            else:
                raise SyntaxError(self._format_error("Unclosed variable expansion", start_pos))
        else:
            # Simple variable
            var_name = self.read_variable_name()
            return TokenPart(
                value=var_name,
                quote_type=quote_context,
                is_variable=True,
                start_pos=start_pos,
                end_pos=self.position
            )
    
    def read_variable_name(self) -> str:
        """Read a simple variable name (after $)."""
        var_name = ""
        
        # Special single-character variables
        if self.current_char() in SPECIAL_VARIABLES:
            var_name = self.current_char()
            self.advance()
            return var_name
        
        # Regular variable names
        while self.current_char() and (
            self.current_char() in VARIABLE_CHARS or 
            (not var_name and self.current_char() in VARIABLE_START_CHARS)
        ):
            var_name += self.current_char()
            self.advance()
        
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
            if next_char in '"\\`':
                return next_char
            elif next_char == '$':
                # Special case: \$ preserves the backslash in double quotes
                return '\\$'
            elif next_char in DOUBLE_QUOTE_ESCAPES:
                return DOUBLE_QUOTE_ESCAPES[next_char]
            else:
                # Other characters keep the backslash
                return '\\' + next_char
        elif quote_context is None:
            # Outside quotes - backslash escapes everything
            return next_char
        else:
            # Single quotes - no escaping
            return '\\' + next_char
    
    def emit_token(self, token_type: TokenType, value: str, start_pos: Optional[int] = None,
                   quote_type: Optional[str] = None) -> None:
        """Emit a token with current parts."""
        if start_pos is None:
            start_pos = self.token_start
            
        # Create basic token
        token = Token(token_type, value, start_pos, self.position, quote_type)
        
        # Convert to RichToken if we have parts
        if self.current_parts:
            rich_token = RichToken.from_token(token, self.current_parts)
            self.tokens.append(rich_token)
            self.current_parts = []
        else:
            self.tokens.append(token)
            
        # Update command position context
        if token_type in (TokenType.SEMICOLON, TokenType.AND_AND, TokenType.OR_OR,
                         TokenType.PIPE, TokenType.LPAREN, TokenType.NEWLINE,
                         TokenType.IF, TokenType.WHILE, TokenType.FOR, TokenType.CASE,
                         TokenType.THEN, TokenType.DO, TokenType.ELSE, TokenType.ELIF):
            self.command_position = True
        elif token_type not in (TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                               TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
                               TokenType.REDIRECT_ERR_APPEND, TokenType.HEREDOC,
                               TokenType.HEREDOC_STRIP, TokenType.HERE_STRING):
            self.command_position = False
    
    def handle_normal_state(self) -> None:
        """Handle tokenization in normal state."""
        char = self.current_char()
        
        # Skip whitespace
        if char in ' \t':
            self.advance()
            return
        
        # Check for process substitution first (before other operators)
        if char in '<>' and self.peek_char() == '(':
            self.handle_process_substitution()
            return
        
        # Check for operators
        operator = self._check_for_operator()
        if operator:
            self._handle_operator(operator)
            return
        
        # Handle quotes
        if char in '"\'':
            self.token_start = self.position
            self.state = LexerState.IN_DOUBLE_QUOTE if char == '"' else LexerState.IN_SINGLE_QUOTE
            self.advance()  # Skip opening quote
            return
        
        # Handle variables
        if char == '$':
            self.handle_dollar()
            return
        
        # Handle comments
        if char == '#' and self._is_comment_start():
            self.state = LexerState.IN_COMMENT
            self.advance()
            return
        
        # Handle backticks
        if char == '`':
            self.token_start = self.position
            self.state = LexerState.IN_BACKTICK
            self.advance()
            return
        
        # Start reading a word
        self.token_start = self.position
        self.state = LexerState.IN_WORD
    
    def _check_for_operator(self) -> Optional[Tuple[str, TokenType]]:
        """Check if current position starts an operator."""
        # Special handling for != (should be a single word token for test command)
        if self.peek_string(2) == '!=':
            return None  # Let it be handled as a word
        
        # Check operators from longest to shortest
        for length in sorted(self.OPERATORS_BY_LENGTH.keys(), reverse=True):
            if length > len(self.input) - self.position:
                continue
            
            op = self.peek_string(length)
            if op in self.OPERATORS_BY_LENGTH[length]:
                return (op, self.OPERATORS_BY_LENGTH[length][op])
        
        return None
    
    def _handle_operator(self, operator: Tuple[str, TokenType]) -> None:
        """Handle an operator token with special cases."""
        op, token_type = operator
        
        # Special handling for [[ and ]]
        if op == '[[' and self.command_position:
            self.in_double_brackets += 1
            self.emit_token(token_type, op, self.position)
            self.advance(len(op))
        elif op == ']]' and self.in_double_brackets > 0:
            self.in_double_brackets -= 1
            self.emit_token(token_type, op, self.position)
            self.advance(len(op))
        elif op == '=~':
            if self.in_double_brackets > 0:
                # =~ is only an operator inside [[ ]]
                self.emit_token(token_type, op, self.position)
                self.advance(len(op))
            else:
                # Outside [[ ]], treat as word
                self.token_start = self.position
                self.state = LexerState.IN_WORD
        elif op in ('<', '>') and self.in_double_brackets > 0:
            # Inside [[ ]], < and > are comparison operators, not redirections
            self.emit_token(TokenType.WORD, op, self.position)
            self.advance(len(op))
        else:
            self.emit_token(token_type, op, self.position)
            self.advance(len(op))
    
    def _is_comment_start(self) -> bool:
        """Check if # at current position starts a comment."""
        return self.position == 0 or self.input[self.position - 1] in ' \t\n;'
    
    def _format_error(self, message: str, position: int) -> str:
        """Format an error message with context from the input."""
        # Extract a snippet around the error position
        start = max(0, position - 20)
        end = min(len(self.input), position + 20)
        snippet = self.input[start:end]
        
        # Calculate where the error is in the snippet
        error_pos = position - start
        
        # Build the error message
        lines = [
            message,
            f"Position {position}:",
            snippet,
            " " * error_pos + "^"
        ]
        
        return "\n".join(lines)
    
    def handle_dollar(self) -> None:
        """Handle $ character - variables, command sub, arithmetic."""
        start_pos = self.position
        self.advance()  # Skip $
        
        if self.current_char() == '(':
            if self.peek_char() == '(':
                # Arithmetic expansion $((
                self.token_start = start_pos
                self.advance(2)  # Skip ((
                self.state = LexerState.IN_ARITHMETIC
                self.paren_depth = 2
            else:
                # Command substitution $(
                self.token_start = start_pos
                self.advance()  # Skip (
                self.state = LexerState.IN_COMMAND_SUB
                self.paren_depth = 1
        elif self.current_char() == '{':
            # Brace variable ${
            self.token_start = start_pos
            self.advance()  # Skip {
            self.state = LexerState.IN_BRACE_VAR
        else:
            # Simple variable
            self.token_start = start_pos
            self.state = LexerState.IN_VARIABLE
    
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
        self.emit_token(token_type, full_value, self.token_start)
        self.state = LexerState.NORMAL
    
    def _read_word_parts(self, quote_context: Optional[str]) -> List[TokenPart]:
        """Read parts of a word, handling embedded variables and expansions."""
        parts: List[TokenPart] = []
        word_start = self.position
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
                        start_pos=word_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                # Parse the variable/expansion
                self.advance()  # Skip $
                part = self.parse_variable_or_expansion(quote_context)
                parts.append(part)
                word_start = self.position
            
            # Check for backslash escapes
            elif char == '\\' and self.peek_char():
                escaped = self.handle_escape_sequence(quote_context)
                current_value += escaped
                self.advance()  # handle_escape_sequence already advanced past backslash
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=quote_context,
                is_variable=False,
                start_pos=word_start,
                end_pos=self.position
            ))
        
        return parts
    
    def _is_word_terminator(self, char: str) -> bool:
        """Check if character terminates a word in current context."""
        if self.in_double_brackets > 0:
            if char in WORD_TERMINATORS_IN_BRACKETS:
                return True
            if char == ']' and self.peek_char() == ']':
                return True
        else:
            return char in WORD_TERMINATORS
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
    
    def handle_double_quote_state(self) -> None:
        """Handle reading inside double quotes with variable expansion."""
        parts = self._read_quoted_parts('"')
        
        # Skip closing quote if present
        quote_closed = False
        if self.current_char() == '"':
            self.advance()
            quote_closed = True
        
        # Check if quote was closed
        if not quote_closed:
            raise SyntaxError(self._format_error("Unclosed double quote", self.token_start))
        
        # Build complete string value
        full_value = self._build_token_value(parts)
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(TokenType.STRING, full_value, self.token_start, '"')
        self.state = LexerState.NORMAL
    
    def _read_quoted_parts(self, quote_char: str) -> List[TokenPart]:
        """Read parts inside quotes, handling expansions in double quotes."""
        parts: List[TokenPart] = []
        quote_start = self.position
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
                        start_pos=quote_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                # Parse the variable/expansion
                self.advance()  # Skip $
                part = self.parse_variable_or_expansion(quote_char)
                parts.append(part)
                quote_start = self.position
            
            # Backslash escapes
            elif char == '\\' and self.peek_char():
                escaped = self.handle_escape_sequence(quote_char)
                current_value += escaped
                self.advance()  # handle_escape_sequence already advanced
            
            # Backtick command substitution (only in double quotes)
            elif quote_char == '"' and char == '`':
                # Save current part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_char,
                        is_variable=False,
                        start_pos=quote_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                # Parse backtick substitution
                backtick_part = self._parse_backtick_substitution(quote_char)
                parts.append(backtick_part)
                quote_start = self.position
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=quote_char,
                is_variable=False,
                start_pos=quote_start,
                end_pos=self.position
            ))
        
        return parts
    
    def _parse_backtick_substitution(self, quote_context: Optional[str]) -> TokenPart:
        """Parse backtick command substitution."""
        start_pos = self.position
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
            raise SyntaxError(self._format_error("Unclosed backtick command substitution", start_pos))
        
        return TokenPart(
            value='`' + content + '`',
            quote_type=quote_context,
            is_expansion=True,
            start_pos=start_pos,
            end_pos=self.position
        )
    
    def handle_single_quote_state(self) -> None:
        """Handle reading inside single quotes (no expansion)."""
        value = ""
        quote_closed = False
        
        while self.current_char() and self.current_char() != "'":
            value += self.current_char()
            self.advance()
        
        # Skip closing quote if present
        if self.current_char() == "'":
            self.advance()
            quote_closed = True
        
        # Check if quote was closed
        if not quote_closed:
            raise SyntaxError(self._format_error("Unclosed single quote", self.token_start))
        
        # Single quotes preserve everything literally
        self.current_parts = [TokenPart(
            value=value,
            quote_type="'",
            is_variable=False,
            start_pos=self.token_start + 1,
            end_pos=self.position - 1
        )]
        
        self.emit_token(TokenType.STRING, value, self.token_start, "'")
        self.state = LexerState.NORMAL
    
    def handle_variable_state(self) -> None:
        """Handle reading a simple variable name."""
        var_name = ""
        
        # Read variable name
        while self.current_char() and (self.current_char().isalnum() or self.current_char() in '_?$!#@*0123456789'):
            var_name += self.current_char()
            self.advance()
        
        self.emit_token(TokenType.VARIABLE, var_name, self.token_start)
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
            raise SyntaxError(self._format_error("Unclosed brace expansion", self.token_start))
        
        self.emit_token(TokenType.VARIABLE, '{' + var_content + '}', self.token_start)
        self.state = LexerState.NORMAL
    
    def handle_command_sub_state(self) -> None:
        """Handle reading $(...) command substitution."""
        content = self.read_balanced_parens()
        # Include the $( and ) in the token value to match original tokenizer
        self.emit_token(TokenType.COMMAND_SUB, '$(' + content + ')', self.token_start)
        self.state = LexerState.NORMAL
    
    def handle_arithmetic_state(self) -> None:
        """Handle reading $((...)) arithmetic expansion."""
        content = self.read_balanced_double_parens()
        # Include the $(( and )) in the token value to match original tokenizer
        self.emit_token(TokenType.ARITH_EXPANSION, '$((' + content + '))', self.token_start)
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
            raise SyntaxError(self._format_error("Unclosed backtick command substitution", self.token_start))
        
        # Include the backticks in the token value to match original tokenizer
        self.emit_token(TokenType.COMMAND_SUB_BACKTICK, '`' + value + '`', self.token_start)
        self.state = LexerState.NORMAL
    
    def handle_comment_state(self) -> None:
        """Handle reading a comment."""
        while self.current_char() and self.current_char() != '\n':
            self.advance()
        self.state = LexerState.NORMAL
    
    def handle_process_substitution(self) -> None:
        """Handle <(...) or >(...) process substitution."""
        token_type = TokenType.PROCESS_SUB_IN if self.current_char() == '<' else TokenType.PROCESS_SUB_OUT
        start_pos = self.position
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
            raise SyntaxError(self._format_error("Unclosed parenthesis", self.token_start))
            
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
            raise SyntaxError(self._format_error("Unclosed arithmetic expansion", self.token_start))
            
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
        while self.position < len(self.input):
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
            raise SyntaxError(self._format_error("Unclosed single quote", self.token_start))
        elif self.state == LexerState.IN_DOUBLE_QUOTE:
            raise SyntaxError(self._format_error("Unclosed double quote", self.token_start))
        elif self.state == LexerState.IN_BACKTICK:
            raise SyntaxError(self._format_error("Unclosed backtick command substitution", self.token_start))
        elif self.state in (LexerState.IN_COMMAND_SUB, LexerState.IN_ARITHMETIC):
            raise SyntaxError(self._format_error("Unclosed expansion", self.token_start))
        
        # Add EOF token
        self.emit_token(TokenType.EOF, '', self.position)
        
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