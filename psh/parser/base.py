"""Base parser class with common functionality."""

from typing import List, Optional, Set, Tuple
from ..token_types import Token, TokenType
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
        
        # Compatibility fix for ModularLexer: handle keywords tokenized as WORD
        if token.type == TokenType.WORD:
            if (token_type == TokenType.IN and token.value == "in"):
                return self.advance()
            elif (token_type == TokenType.ESAC and token.value == "esac"):
                return self.advance()
        
        if token.type != token_type:
            expected = self._token_type_to_string(token_type)
            error_context = ErrorContext(
                token=token,
                expected=[expected],
                position=token.position,
                message=message
            )
            raise ParseError(error_context)
        return self.advance()
    
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
        
        # Compatibility fix for ModularLexer: handle keywords tokenized as WORD
        if token.type == TokenType.WORD:
            if (TokenType.IN in token_types and token.value == "in"):
                return True
            elif (TokenType.ESAC in token_types and token.value == "esac"):
                return True
            
        return token.type in token_types
    
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