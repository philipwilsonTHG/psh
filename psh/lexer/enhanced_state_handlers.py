"""Enhanced state handlers using unified quote and expansion parsers."""

from typing import List, Optional, Tuple
from ..token_types import TokenType
from .position import LexerState, Position
from .token_parts import TokenPart
from .quote_parser import UnifiedQuoteParser, QuoteParsingContext, QUOTE_RULES
from .expansion_parser import ExpansionParser, ExpansionContext
from .unicode_support import is_whitespace


class EnhancedStateHandlers:
    """Enhanced state handlers using unified parsers."""
    
    def __init__(self):
        """Initialize with unified parsers."""
        self.quote_parser = UnifiedQuoteParser()
        self.expansion_parser = ExpansionParser()
        self.quote_context = None
        self.expansion_context = None
    
    def setup_parsers(self, lexer: 'StateMachineLexer') -> None:
        """Set up parsers with lexer context."""
        # Create expansion parser with lexer config
        self.expansion_parser = ExpansionParser(lexer.config)
        
        # Create quote parser with expansion parser
        self.quote_parser = UnifiedQuoteParser(self.expansion_parser)
        
        # Create parsing contexts
        self.quote_context = QuoteParsingContext(
            lexer.input,
            lexer.position_tracker,
            lexer.config
        )
        self.expansion_context = ExpansionContext(
            lexer.input,
            lexer.config,
            lexer.position_tracker
        )
    
    def handle_normal_state(self, lexer: 'StateMachineLexer') -> None:
        """Handle tokenization in normal state using unified parsers."""
        char = lexer.current_char()
        
        # Check for process substitution first (before other operators)
        if char in '<>' and lexer.peek_char() == '(':
            lexer.handle_process_substitution()
            return
        
        # Check for operators (including newline before general whitespace)
        operator = lexer._check_for_operator()
        if operator:
            lexer._handle_operator(operator)
            return
        
        # Skip whitespace (Unicode-aware) - but only non-operator whitespace
        if char and is_whitespace(char, lexer.config.posix_mode):
            # Skip all consecutive whitespace
            while lexer.current_char() and is_whitespace(lexer.current_char(), lexer.config.posix_mode):
                lexer.advance()
            return
        
        # Handle backticks using unified expansion parser (before quotes)
        if char == '`' and self.expansion_context.is_expansion_start(lexer.position):
            self._handle_backtick_start(lexer)
            return
        
        # Handle variables using unified expansion parser
        if char == '$' and self.expansion_context.is_expansion_start(lexer.position):
            self._handle_expansion_start(lexer)
            return
        
        # Handle quotes using unified parser (but exclude backticks which are expansions)
        if char in ['"', "'"] and self.quote_context.is_quote_character(char):
            self._handle_quote_start(lexer, char)
            return
        
        # Handle comments
        if char == '#' and lexer._is_comment_start():
            lexer.state = LexerState.IN_COMMENT
            lexer.advance()
            return
        
        # Start reading a word
        lexer.token_start_pos = lexer.get_current_position()
        lexer.state = LexerState.IN_WORD
    
    def handle_word_state(self, lexer: 'StateMachineLexer') -> None:
        """Handle reading a word using unified parsers."""
        parts = self._read_word_parts_unified(lexer, quote_context=None)
        
        # Build complete word value
        full_value = lexer._build_token_value(parts)
        
        # Check if it's a keyword
        from .constants import KEYWORDS
        token_type = TokenType.WORD
        if full_value in KEYWORDS and lexer.is_keyword_context(full_value):
            token_type = getattr(TokenType, full_value.upper())
        
        # Store parts for later use
        lexer.current_parts = parts
        
        # Emit token
        lexer.emit_token(token_type, full_value, lexer.token_start_pos)
        lexer.state = LexerState.NORMAL
        
        # Reset after_regex_match flag after consuming the regex pattern
        if lexer.after_regex_match:
            lexer.after_regex_match = False
    
    def handle_quote_state(self, lexer: 'StateMachineLexer', quote_char: str) -> None:
        """Handle quoted string parsing using unified parser."""
        # Get quote rules for this character
        from .quote_parser import QUOTE_RULES
        rules = QUOTE_RULES.get(quote_char)
        if not rules:
            # Unknown quote type - create basic rules
            from .quote_parser import QuoteRules
            rules = QuoteRules(quote_char, False, {})
        
        # Parse the quoted string content using unified parser with expansion support
        parts, new_pos, found_closing = self.quote_parser.parse_quoted_string(
            lexer.input,
            lexer.position,  # Current position (after opening quote)
            rules,
            lexer.position_tracker
        )
        
        # Update lexer position
        lexer.position = new_pos
        
        # Check for unclosed quotes
        if not found_closing:
            error_msg = f"Unclosed {'double' if quote_char == '\"' else 'single'} quote"
            lexer._error(error_msg)
        
        # Build complete string value
        full_value = ''.join(part.value for part in parts)
        
        # Store parts for later use
        lexer.current_parts = parts
        
        # Emit token
        lexer.emit_token(TokenType.STRING, full_value, lexer.token_start_pos, quote_char)
        lexer.state = LexerState.NORMAL
    
    def _handle_quote_start(self, lexer: 'StateMachineLexer', quote_char: str) -> None:
        """Handle the start of a quoted string."""
        lexer.token_start_pos = lexer.get_current_position()
        lexer.advance()  # Skip opening quote
        
        # Use unified parser to handle the quote
        self.handle_quote_state(lexer, quote_char)
    
    def _handle_expansion_start(self, lexer: 'StateMachineLexer') -> None:
        """Handle the start of an expansion."""
        lexer.token_start_pos = lexer.get_current_position()
        
        # Parse the expansion
        expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
            lexer.position
        )
        
        # Update position
        lexer.position = new_pos
        
        # Emit token based on expansion type
        if expansion_part.is_variable:
            if expansion_part.expansion_type == 'parameter':
                token_type = TokenType.VARIABLE
                # Strip the $ but keep the {} wrapper for parameter expansion
                value = expansion_part.value[1:] if expansion_part.value.startswith('$') else expansion_part.value
            else:
                token_type = TokenType.VARIABLE
                # For simple variables, the value should already be just the variable name
                value = expansion_part.value
        else:
            # Command substitution or arithmetic
            if expansion_part.expansion_type == 'arithmetic':
                token_type = TokenType.ARITH_EXPANSION
            else:
                token_type = TokenType.COMMAND_SUB
            value = expansion_part.value
        
        lexer.emit_token(token_type, value, lexer.token_start_pos)
        lexer.state = LexerState.NORMAL
    
    def _handle_backtick_start(self, lexer: 'StateMachineLexer') -> None:
        """Handle the start of backtick command substitution."""
        lexer.token_start_pos = lexer.get_current_position()
        
        # Parse the backtick substitution
        backtick_part, new_pos = self.expansion_parser.parse_backtick_substitution(
            lexer.input, lexer.position
        )
        
        # Update position
        lexer.position = new_pos
        
        # Check for unclosed backticks
        if backtick_part.expansion_type == 'backtick_unclosed':
            lexer._error("Unclosed backtick command substitution")
        
        # Emit token
        lexer.emit_token(TokenType.COMMAND_SUB_BACKTICK, backtick_part.value, lexer.token_start_pos)
        lexer.state = LexerState.NORMAL
    
    def _read_word_parts_unified(
        self, 
        lexer: 'StateMachineLexer',
        quote_context: Optional[str]
    ) -> List[TokenPart]:
        """Read parts of a word using unified parsers."""
        parts: List[TokenPart] = []
        word_start_pos = lexer.get_current_position()
        current_value = ""
        
        while lexer.current_char():
            char = lexer.current_char()
            
            # Check for word terminators
            if lexer._is_word_terminator(char):
                break
            
            # Check for embedded expansion
            if self.expansion_context.is_expansion_start(lexer.position):
                # Save current word part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_context,
                        is_variable=False,
                        start_pos=word_start_pos,
                        end_pos=lexer.get_current_position()
                    ))
                    current_value = ""
                
                # Parse the expansion
                expansion_part, new_pos = self.expansion_context.parse_expansion_at_position(
                    lexer.position, quote_context
                )
                parts.append(expansion_part)
                lexer.position = new_pos
                word_start_pos = lexer.get_current_position()
                continue
            
            # Check for embedded quotes
            if self.quote_context.is_quote_character(char):
                # Save current word part if any
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=quote_context,
                        is_variable=False,
                        start_pos=word_start_pos,
                        end_pos=lexer.get_current_position()
                    ))
                    current_value = ""
                
                # Parse the quoted part
                quote_parts, new_pos, found_closing = self.quote_context.parse_quote_at_position(
                    lexer.position, char
                )
                parts.extend(quote_parts)
                lexer.position = new_pos
                
                if not found_closing:
                    lexer._error(f"Unclosed {char} quote in word")
                
                word_start_pos = lexer.get_current_position()
                continue
            
            # Check for backslash escapes
            if char == '\\' and lexer.peek_char():
                from . import pure_helpers
                escaped, new_pos = pure_helpers.handle_escape_sequence(
                    lexer.input, lexer.position, quote_context
                )
                current_value += escaped
                lexer.position = new_pos
                continue
            
            # Regular character
            current_value += char
            lexer.advance()
        
        # Save final part if any
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=quote_context,
                is_variable=False,
                start_pos=word_start_pos,
                end_pos=lexer.get_current_position()
            ))
        
        return parts
    
    def handle_comment_state(self, lexer: 'StateMachineLexer') -> None:
        """Handle reading a comment."""
        while lexer.current_char() and lexer.current_char() != '\n':
            lexer.advance()
        lexer.state = LexerState.NORMAL