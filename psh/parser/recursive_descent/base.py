"""Base parser class with common functionality."""

from typing import List, Optional, Set, Tuple
from ...token_types import Token, TokenType
from ...lexer.keyword_defs import matches_keyword_type
from .helpers import ParseContext, ErrorContext, ParseError, TokenGroups


class BaseParser:
    """Base parser with token management and common utilities."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
        self.context = ParseContext()
    
    # === Token Management ===
    
    def peek(self) -> Token:
        """Look at the current token without consuming it."""
        if self.current < len(self.tokens):
            return self.tokens[self.current]
        return self.tokens[-1]  # Return EOF token
    
    def peek_ahead(self, n: int = 1) -> Optional[Token]:
        """Look ahead n tokens without consuming."""
        pos = self.current + n
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None
    
    def advance(self) -> Token:
        """Consume and return the current token."""
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token
    
    def expect(self, token_type: TokenType, message: Optional[str] = None) -> Token:
        """Consume a token of the expected type or raise an error."""
        token = self.peek()
        
        if not matches_keyword_type(token, token_type):
            expected = self._token_type_to_string(token_type)
            error_context = ErrorContext(
                token=token,
                expected=[expected],
                position=token.position,
                message=message
            )
            
            # Add smart error suggestions
            self._enhance_error_context(error_context, token_type)
            
            raise ParseError(error_context)
        return self.advance()
    
    def expect_with_recovery(self, token_type: TokenType, 
                           recovery_hint: Optional[str] = None) -> Token:
        """Expect token with smart error recovery and suggestions."""
        try:
            return self.expect(token_type)
        except ParseError as e:
            # Try to provide helpful suggestion based on context
            self._add_contextual_suggestions(e.error_context, token_type, recovery_hint)
            raise e
    
    def expect_one_of(self, *token_types: TokenType) -> Token:
        """Expect one of several token types."""
        token = self.peek()
        if token.type not in token_types:
            expected = [self._token_type_to_string(tt) for tt in token_types]
            error_context = ErrorContext(
                token=token,
                expected=expected,
                position=token.position
            )
            raise ParseError(error_context)
        return self.advance()
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        token = self.peek()
        
        if token.type in token_types:
            return True
        return any(matches_keyword_type(token, tt) for tt in token_types)
    
    def match_any(self, token_set: Set[TokenType]) -> bool:
        """Check if current token is in the given set."""
        return self.peek().type in token_set
    
    def consume_if_match(self, *token_types: TokenType) -> Optional[Token]:
        """Consume and return token if it matches any of the given types."""
        if self.match(*token_types):
            return self.advance()
        return None
    
    # === Helper Methods ===
    
    def skip_newlines(self) -> None:
        """Skip any newline tokens."""
        while self.match(TokenType.NEWLINE):
            self.advance()
    
    def skip_separators(self) -> None:
        """Skip semicolons and newlines."""
        while self.match_any(TokenGroups.STATEMENT_SEPARATORS):
            self.advance()
    
    def at_end(self) -> bool:
        """Check if we've reached the end of input."""
        return self.peek().type == TokenType.EOF
    
    def save_position(self) -> int:
        """Save current parser position."""
        return self.current
    
    def restore_position(self, position: int) -> None:
        """Restore parser to saved position."""
        self.current = position
    
    def synchronize(self, sync_tokens: Set[TokenType]) -> None:
        """Synchronize parser after error by finding next sync token."""
        while not self.at_end() and not self.match_any(sync_tokens):
            self.advance()
    
    # === Error Recovery ===
    
    def with_error_recovery(self, sync_tokens: Set[TokenType]):
        """Context manager for error recovery."""
        old_recovery = self.context.in_error_recovery
        old_sync = self.context.error_sync_tokens
        
        self.context.in_error_recovery = True
        self.context.error_sync_tokens = sync_tokens
        
        try:
            yield
        finally:
            self.context.in_error_recovery = old_recovery
            self.context.error_sync_tokens = old_sync
    
    def panic_mode_recovery(self, sync_tokens: Set[TokenType]) -> None:
        """Recover using panic mode - skip tokens until sync point.
        
        Args:
            sync_tokens: Set of tokens to synchronize on
        """
        self.context.in_error_recovery = True
        
        while not self.at_end() and not self.match_any(sync_tokens):
            self.advance()
        
        self.context.in_error_recovery = False
    
    def parse_statement_with_recovery(self):
        """Parse statement with automatic recovery.
        
        Returns:
            Parsed statement or None if recovery was needed
        """
        try:
            # This would be implemented by subclasses that have statement parsing
            # For now, this is a placeholder showing the pattern
            return self._parse_statement_impl()
        except ParseError as e:
            # Check if we have an error collector (multi-error mode)
            if hasattr(self, 'error_collector') and self.error_collector:
                self.error_collector.add_error(e)
                
                # Import here to avoid circular imports
                from .support.error_collector import RecoveryPoints
                recovery_points = RecoveryPoints()
                
                self.panic_mode_recovery(recovery_points.STATEMENT_START)
                return None  # Skip this statement
            else:
                raise  # Normal error propagation
    
    def _parse_statement_impl(self):
        """Implementation placeholder for statement parsing."""
        # This would be implemented by subclasses
        raise NotImplementedError("Subclasses should implement statement parsing")
    
    # === Token Type Conversion ===
    
    def _error(self, message: str, token: Optional[Token] = None) -> ParseError:
        """Create a ParseError with context."""
        if token is None:
            token = self.peek()
        error_context = ErrorContext(
            token=token,
            message=message,
            position=token.position
        )
        return ParseError(error_context)
    
    def _token_type_to_string(self, token_type: TokenType) -> str:
        """Convert token type to human-readable string."""
        # Token type to display string mapping
        TOKEN_DISPLAY_NAMES = {
            TokenType.LBRACE: "'{'",
            TokenType.RBRACE: "'}'",
            TokenType.LPAREN: "'('",
            TokenType.RPAREN: "')'",
            TokenType.SEMICOLON: "';'",
            TokenType.PIPE: "'|'",
            TokenType.AMPERSAND: "'&'",
            TokenType.AND_AND: "'&&'",
            TokenType.OR_OR: "'||'",
            TokenType.DOUBLE_LBRACKET: "'[['",
            TokenType.DOUBLE_RBRACKET: "']]'",
            TokenType.DOUBLE_LPAREN: "'(('", 
            TokenType.EOF: "end of input",
            TokenType.NEWLINE: "newline",
            TokenType.WORD: "word",
            TokenType.STRING: "string",
            TokenType.VARIABLE: "variable",
            TokenType.IF: "'if'",
            TokenType.THEN: "'then'",
            TokenType.ELSE: "'else'",
            TokenType.ELIF: "'elif'",
            TokenType.FI: "'fi'",
            TokenType.WHILE: "'while'",
            TokenType.UNTIL: "'until'",
            TokenType.DO: "'do'",
            TokenType.DONE: "'done'",
            TokenType.FOR: "'for'",
            TokenType.IN: "'in'",
            TokenType.CASE: "'case'",
            TokenType.ESAC: "'esac'",
            TokenType.FUNCTION: "'function'",
            TokenType.SELECT: "'select'",
            TokenType.BREAK: "'break'",
            TokenType.CONTINUE: "'continue'",
            TokenType.RETURN: "'return'",
            TokenType.REDIRECT_IN: "'<'",
            TokenType.REDIRECT_OUT: "'>'",
            TokenType.REDIRECT_APPEND: "'>>'",
            TokenType.REDIRECT_ERR: "'2>'",
            TokenType.REDIRECT_ERR_APPEND: "'2>>'",
            TokenType.HEREDOC: "'<<'",
            TokenType.HEREDOC_STRIP: "'<<-'",
            TokenType.HERE_STRING: "'<<<'",
            TokenType.COMMAND_SUB: "command substitution",
            TokenType.ARITH_EXPANSION: "arithmetic expansion",
        }
        
        return TOKEN_DISPLAY_NAMES.get(token_type, token_type.name.lower().replace('_', ' '))
    
    def _enhance_error_context(self, error_context: ErrorContext, expected_token_type: TokenType) -> None:
        """Enhance error context with smart suggestions."""
        from ..errors import ErrorSuggester, ParserErrorCatalog
        
        # Add context tokens
        self._add_token_context(error_context)
        
        # Try to find a matching error template
        template = self._find_error_template(expected_token_type, error_context.token)
        if template:
            error_context.set_error_template(template)
        
        # Add typo suggestions
        typo_suggestion = ErrorSuggester.suggest_for_typo(
            self._token_type_to_string(expected_token_type),
            error_context.token.value or ""
        )
        if typo_suggestion:
            error_context.add_suggestion(typo_suggestion)
        
        # Add context-based suggestions
        context_suggestion = self._get_contextual_suggestion(expected_token_type, error_context.token)
        if context_suggestion:
            error_context.add_suggestion(context_suggestion)
    
    def _add_contextual_suggestions(self, error_context: ErrorContext, 
                                  expected_token_type: TokenType, 
                                  recovery_hint: Optional[str]) -> None:
        """Add contextual suggestions to error context."""
        if recovery_hint:
            error_context.add_suggestion(recovery_hint)
        
        # Add suggestions based on surrounding tokens
        preceding_tokens = self._get_preceding_tokens(3)
        from ..errors import ErrorSuggester
        
        suggestion = ErrorSuggester.suggest_for_context(
            error_context.token,
            preceding_tokens
        )
        if suggestion:
            error_context.add_suggestion(suggestion)
    
    def _add_token_context(self, error_context: ErrorContext) -> None:
        """Add surrounding tokens for context."""
        # Get 3 tokens before and after current position
        context_tokens = []
        
        # Preceding tokens
        for i in range(max(0, self.current - 3), self.current):
            if i < len(self.tokens):
                context_tokens.append(self.tokens[i].value or str(self.tokens[i].type))
        
        # Following tokens
        for i in range(self.current + 1, min(len(self.tokens), self.current + 4)):
            context_tokens.append(self.tokens[i].value or str(self.tokens[i].type))
        
        error_context.add_context_tokens(context_tokens)
    
    def _find_error_template(self, expected_token_type: TokenType, actual_token: Token):
        """Find appropriate error template for the situation."""
        from ..errors import ParserErrorCatalog
        
        # Map token types to error templates
        token_error_map = {
            TokenType.THEN: ParserErrorCatalog.MISSING_SEMICOLON_BEFORE_THEN,
            TokenType.DO: self._get_do_error_template(),
            TokenType.FI: ParserErrorCatalog.UNCLOSED_IF_STATEMENT,
            TokenType.DONE: self._get_done_error_template(),
            TokenType.ESAC: ParserErrorCatalog.UNCLOSED_CASE_STATEMENT,
            TokenType.RBRACE: ParserErrorCatalog.UNCLOSED_FUNCTION_BODY,
        }
        
        return token_error_map.get(expected_token_type)
    
    def _get_do_error_template(self):
        """Get appropriate 'do' error template based on context."""
        from ..errors import ParserErrorCatalog
        
        # Look for preceding for/while to determine context
        preceding_tokens = self._get_preceding_tokens(5)
        for token in reversed(preceding_tokens):
            if token.type == TokenType.FOR:
                return ParserErrorCatalog.MISSING_DO_AFTER_FOR
            elif token.type == TokenType.WHILE or token.type == TokenType.UNTIL:
                return ParserErrorCatalog.MISSING_DO_AFTER_WHILE
        
        # Default to generic missing do
        return ParserErrorCatalog.MISSING_DO_AFTER_FOR
    
    def _get_done_error_template(self):
        """Get appropriate 'done' error template based on context."""
        from ..errors import ParserErrorCatalog
        
        # Look for preceding for/while to determine context
        preceding_tokens = self._get_preceding_tokens(10)
        for token in reversed(preceding_tokens):
            if token.type == TokenType.FOR:
                return ParserErrorCatalog.UNCLOSED_FOR_LOOP
            elif token.type == TokenType.WHILE or token.type == TokenType.UNTIL:
                return ParserErrorCatalog.UNCLOSED_WHILE_LOOP
        
        return ParserErrorCatalog.UNCLOSED_FOR_LOOP
    
    def _get_contextual_suggestion(self, expected_token_type: TokenType, actual_token: Token) -> Optional[str]:
        """Get contextual suggestion based on parser state."""
        # Check if we're in specific parsing contexts
        if expected_token_type == TokenType.THEN:
            return "Add ';' after the condition and before 'then'"
        elif expected_token_type == TokenType.DO:
            return "Add ';' after the loop header and before 'do'"
        elif expected_token_type == TokenType.SEMICOLON:
            return "Add ';' to separate commands"
        elif expected_token_type == TokenType.RPAREN:
            return "Add ')' to close the parentheses"
        elif expected_token_type == TokenType.RBRACE:
            return "Add '}' to close the brace group"
        
        return None
    
    def _get_preceding_tokens(self, count: int) -> List[Token]:
        """Get the preceding tokens for context analysis."""
        start = max(0, self.current - count)
        return self.tokens[start:self.current]
