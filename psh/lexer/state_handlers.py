"""State handler methods for the lexer state machine."""

from typing import List, Optional, Tuple
from ..token_types import TokenType
from .position import LexerState, Position
from .token_parts import TokenPart
from .unicode_support import is_whitespace


class StateHandlers:
    """Mixin class providing state handler methods for the lexer."""
    
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
        elif char == "'" and self.config.enable_single_quotes:
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
    
    def handle_word_state(self) -> None:
        """Handle reading a word, which may contain embedded variables."""
        parts = self._read_word_parts(quote_context=None)
        
        # Build complete word value
        full_value = self._build_token_value(parts)
        
        # Check if it's a keyword
        from .constants import KEYWORDS
        token_type = TokenType.WORD
        if full_value in KEYWORDS and self.is_keyword_context(full_value):
            token_type = getattr(TokenType, full_value.upper())
        
        # Store parts for later use
        self.current_parts = parts
        
        # Emit token
        self.emit_token(token_type, full_value, self.token_start_pos)
        self.state = LexerState.NORMAL
        
        # Reset after_regex_match flag after consuming the regex pattern
        if self.after_regex_match:
            self.after_regex_match = False
    
    def handle_double_quote_state(self) -> None:
        """Handle reading inside double quotes with variable expansion."""
        self._process_quoted_string('"', allow_expansions=True)
    
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