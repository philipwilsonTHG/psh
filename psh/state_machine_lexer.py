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
from typing import List, Optional, Dict, Set, Tuple
import re

# Import existing TokenType and Token from tokenizer.py
from .tokenizer import TokenType, Token


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
    IN_HEREDOC = auto()
    IN_BACKTICK = auto()
    IN_PROCESS_SUB = auto()
    IN_BRACE_VAR = auto()  # Inside ${...}
    AFTER_DOLLAR = auto()
    AFTER_REDIRECT = auto()
    IN_DOUBLE_BRACKETS = auto()  # Inside [[ ]]


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
    
    # Operator precedence for trie-based recognition
    OPERATORS = {
        # Four-character operators (check first)
        '2>&1': TokenType.REDIRECT_DUP,
        # Three-character operators
        '<<<': TokenType.HERE_STRING,
        '2>>': TokenType.REDIRECT_ERR_APPEND,
        ';;&': TokenType.AMP_SEMICOLON,
        '<<-': TokenType.HEREDOC_STRIP,
        # Two-character operators
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
        # Single-character operators
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
        self.state_stack: List[LexerState] = []
        
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
    
    def push_state(self, new_state: LexerState) -> None:
        """Push current state and enter new state."""
        self.state_stack.append(self.state)
        self.state = new_state
    
    def pop_state(self) -> None:
        """Return to previous state."""
        if self.state_stack:
            self.state = self.state_stack.pop()
    
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
        
        # Check for multi-character operators first
        # Special handling for != (should be a single word token for test command)
        if self.peek_string(2) == '!=':
            self.emit_token(TokenType.WORD, '!=', self.position)
            self.advance(2)
            return
            
        for length in (4, 3, 2, 1):
            op = self.peek_string(length)
            if op in self.OPERATORS:
                # Special handling for [[ and ]]
                if op == '[[' and self.command_position:
                    self.in_double_brackets += 1
                    self.emit_token(self.OPERATORS[op], op, self.position)
                    self.advance(length)
                elif op == ']]' and self.in_double_brackets > 0:
                    self.in_double_brackets -= 1
                    self.emit_token(self.OPERATORS[op], op, self.position)
                    self.advance(length)
                elif op == '=~' and self.in_double_brackets > 0:
                    # =~ is only an operator inside [[ ]]
                    self.emit_token(self.OPERATORS[op], op, self.position)
                    self.advance(length)
                elif op == '=~' and self.in_double_brackets == 0:
                    # Outside [[ ]], treat = and ~ as separate
                    self.token_start = self.position
                    self.state = LexerState.IN_WORD
                elif op in ('<', '>') and self.in_double_brackets > 0:
                    # Inside [[ ]], < and > are comparison operators, not redirections
                    self.emit_token(TokenType.WORD, op, self.position)
                    self.advance(length)
                else:
                    self.emit_token(self.OPERATORS[op], op, self.position)
                    self.advance(length)
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
        if char == '#' and (self.position == 0 or self.input[self.position - 1] in ' \t\n;'):
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
        parts: List[TokenPart] = []
        word_start = self.position
        current_value = ""
        
        while self.current_char():
            char = self.current_char()
            
            # Check for word terminators
            # Inside [[ ]], ] is part of patterns unless it's ]]
            if self.in_double_brackets > 0:
                if char in ' \t\n|<>;&(){}\'"\n':
                    break
                if char == ']' and self.peek_char() == ']':
                    break  # Stop at ]]
            else:
                if char in ' \t\n|<>;&(){}\'"\n':
                    break
            
            # Check for embedded variable or expansion
            if char == '$':
                # Save current word part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=None,
                        is_variable=False,
                        start_pos=word_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                # Check what follows the $
                var_start = self.position
                self.advance()  # Skip $
                
                if self.current_char() == '(':
                    # Command substitution or arithmetic expansion
                    if self.peek_char() == '(':
                        # Arithmetic expansion $((...))
                        self.advance(2)  # Skip ((
                        arith_content = self.read_balanced_double_parens()
                        parts.append(TokenPart(
                            value='$((' + arith_content + '))',
                            quote_type=None,
                            is_expansion=True,
                            start_pos=var_start,
                            end_pos=self.position
                        ))
                    else:
                        # Command substitution $(...)
                        self.advance()  # Skip (
                        cmd_content = self.read_balanced_parens()
                        parts.append(TokenPart(
                            value='$(' + cmd_content + ')',
                            quote_type=None,
                            is_expansion=True,
                            start_pos=var_start,
                            end_pos=self.position
                        ))
                    word_start = self.position
                elif self.current_char() == '{':
                    # ${var} format
                    self.advance()  # Skip {
                    var_name = '{'
                    while self.current_char() and self.current_char() != '}':
                        var_name += self.current_char()
                        self.advance()
                    if self.current_char() == '}':
                        var_name += '}'
                        self.advance()
                    parts.append(TokenPart(
                        value=var_name,
                        quote_type=None,
                        is_variable=True,
                        start_pos=var_start,
                        end_pos=self.position
                    ))
                    word_start = self.position
                else:
                    # $var format
                    var_name = ''
                    while self.current_char() and (self.current_char().isalnum() or self.current_char() in '_?$!#@*0123456789'):
                        var_name += self.current_char()
                        self.advance()
                    parts.append(TokenPart(
                        value=var_name,
                        quote_type=None,
                        is_variable=True,
                        start_pos=var_start,
                        end_pos=self.position
                    ))
                    word_start = self.position
            
            # Check for backslash escapes
            elif char == '\\' and self.peek_char():
                self.advance()  # Skip backslash
                if self.current_char():
                    # Add the escaped character directly
                    current_value += self.current_char()
                    self.advance()
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=None,
                is_variable=False,
                start_pos=word_start,
                end_pos=self.position
            ))
        
        # Build complete word value
        full_value = ""
        for part in parts:
            if part.is_variable:
                full_value += '$' + part.value
            elif part.is_expansion:
                full_value += part.value
            else:
                full_value += part.value
        
        # Check if it's a keyword
        token_type = TokenType.WORD
        if full_value in self.KEYWORDS and self.is_keyword_context(full_value):
            token_type = getattr(TokenType, full_value.upper())
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(token_type, full_value, self.token_start)
        self.state = LexerState.NORMAL
    
    def handle_double_quote_state(self) -> None:
        """Handle reading inside double quotes with variable expansion."""
        parts: List[TokenPart] = []
        quote_start = self.position
        current_value = ""
        
        while self.current_char() and self.current_char() != '"':
            char = self.current_char()
            
            if char == '$':
                # Save current part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type='"',
                        is_variable=False,
                        start_pos=quote_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                # Handle variable/expansion
                var_start = self.position
                self.advance()  # Skip $
                
                if self.current_char() == '(':
                    if self.peek_char() == '(':
                        # Arithmetic expansion in quotes
                        self.advance(2)  # Skip ((
                        arith_content = self.read_balanced_double_parens()
                        parts.append(TokenPart(
                            value='$((' + arith_content + '))',
                            quote_type='"',
                            is_expansion=True,
                            start_pos=var_start,
                            end_pos=self.position
                        ))
                    else:
                        # Command substitution in quotes
                        self.advance()  # Skip (
                        cmd_content = self.read_balanced_parens()
                        parts.append(TokenPart(
                            value='$(' + cmd_content + ')',
                            quote_type='"',
                            is_expansion=True,
                            start_pos=var_start,
                            end_pos=self.position
                        ))
                elif self.current_char() == '{':
                    # ${var} in quotes
                    self.advance()  # Skip {
                    var_name = '{'
                    while self.current_char() and self.current_char() != '}':
                        var_name += self.current_char()
                        self.advance()
                    if self.current_char() == '}':
                        var_name += '}'
                        self.advance()
                    parts.append(TokenPart(
                        value=var_name,
                        quote_type='"',
                        is_variable=True,
                        start_pos=var_start,
                        end_pos=self.position
                    ))
                else:
                    # $var in quotes
                    var_name = ''
                    while self.current_char() and (self.current_char().isalnum() or self.current_char() in '_?$!#@*0123456789'):
                        var_name += self.current_char()
                        self.advance()
                    parts.append(TokenPart(
                        value=var_name,
                        quote_type='"',
                        is_variable=True,
                        start_pos=var_start,
                        end_pos=self.position
                    ))
                quote_start = self.position
            
            elif char == '\\' and self.peek_char():
                # Handle escape sequences
                self.advance()
                next_char = self.current_char()
                if next_char in '"\\`':
                    # Standard escapes: these characters lose the backslash
                    current_value += next_char
                elif next_char == 'n':
                    # \n becomes newline
                    current_value += '\n'
                elif next_char == '$':
                    # Special case: preserve \$ in double quotes (bash compatibility)
                    current_value += '\\$'
                else:
                    # Other characters keep the backslash
                    current_value += '\\' + next_char
                self.advance()
            
            elif char == '`':
                # Backtick command substitution in quotes
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type='"',
                        is_variable=False,
                        start_pos=quote_start,
                        end_pos=self.position
                    ))
                    current_value = ""
                
                backtick_start = self.position
                self.advance()  # Skip `
                backtick_content = ''
                while self.current_char() and self.current_char() != '`':
                    if self.current_char() == '\\' and self.peek_char() in '`$\\':
                        self.advance()
                    backtick_content += self.current_char()
                    self.advance()
                if self.current_char() == '`':
                    self.advance()
                    
                parts.append(TokenPart(
                    value='`' + backtick_content + '`',
                    quote_type='"',
                    is_expansion=True,
                    start_pos=backtick_start,
                    end_pos=self.position
                ))
                quote_start = self.position
            
            else:
                current_value += char
                self.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type='"',
                is_variable=False,
                start_pos=quote_start,
                end_pos=self.position
            ))
        
        # Skip closing quote if present
        quote_closed = False
        if self.current_char() == '"':
            self.advance()
            quote_closed = True
        
        # Check if quote was closed
        if not quote_closed:
            raise SyntaxError(f"Unclosed quote at position {self.token_start}")
        
        # Build complete string value
        full_value = ""
        for part in parts:
            if part.is_variable:
                full_value += '$' + part.value
            elif part.is_expansion:
                full_value += part.value
            else:
                full_value += part.value
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(TokenType.STRING, full_value, self.token_start, '"')
        self.state = LexerState.NORMAL
    
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
            raise SyntaxError(f"Unclosed quote at position {self.token_start}")
        
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
            raise SyntaxError(f"Unclosed brace expansion at position {self.token_start}")
        
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
            raise SyntaxError(f"Unclosed backtick at position {self.token_start}")
        
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
            raise SyntaxError(f"Unclosed parenthesis at position {self.token_start}")
            
        return content
    
    def read_balanced_double_parens(self) -> str:
        """Read content until balanced double parentheses for arithmetic."""
        content = ""
        depth = 2
        found_closing = False
        
        while self.current_char() and depth > 0:
            char = self.current_char()
            if char == '(' and self.peek_char() == '(':
                content += char
                self.advance()
                content += self.current_char()  # Add the second (
                self.advance()
                depth += 2
            elif char == ')' and self.peek_char() == ')':
                if depth == 2:
                    # Found closing ))
                    self.advance()  # Skip first )
                    self.advance()  # Skip second )
                    found_closing = True
                    break
                else:
                    content += char
                    self.advance()
                    content += self.current_char()  # Add the second )
                    self.advance()
                    depth -= 2
            else:
                content += char
                self.advance()
        
        # Check if we found the closing )) or hit EOF
        if not found_closing:
            raise SyntaxError(f"Unclosed arithmetic expansion at position {self.token_start}")
            
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
            elif self.state == LexerState.IN_DOUBLE_BRACKETS:
                self.handle_normal_state()  # Use normal handling but with context
            else:
                # Shouldn't happen, but recover
                self.advance()
        
        # Check for unclosed quotes or other incomplete states
        if self.state == LexerState.IN_SINGLE_QUOTE:
            raise SyntaxError(f"Unclosed quote at position {self.token_start}")
        elif self.state == LexerState.IN_DOUBLE_QUOTE:
            raise SyntaxError(f"Unclosed quote at position {self.token_start}")
        elif self.state == LexerState.IN_BACKTICK:
            raise SyntaxError(f"Unclosed backtick at position {self.token_start}")
        elif self.state in (LexerState.IN_COMMAND_SUB, LexerState.IN_ARITHMETIC, LexerState.IN_PROCESS_SUB):
            raise SyntaxError(f"Unclosed expansion at position {self.token_start}")
        
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