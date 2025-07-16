"""Base parser class using centralized ParserContext."""

from typing import List, Optional, Set, Union
from ..token_types import Token, TokenType
from .context import ParserContext
from .helpers import ParseError, TokenGroups


class ContextBaseParser:
    """Base parser with ParserContext for centralized state management.
    
    This is the new base parser that uses ParserContext instead of managing
    state directly. It provides cleaner interfaces and better maintainability.
    """
    
    def __init__(self, ctx: ParserContext):
        self.ctx = ctx
    
    # === Token Operations (delegated to context) ===
    
    def peek(self, offset: int = 0) -> Token:
        """Look at current token + offset without consuming."""
        return self.ctx.peek(offset)
    
    def advance(self) -> Token:
        """Consume and return current token."""
        return self.ctx.advance()
    
    def at_end(self) -> bool:
        """Check if at end of tokens."""
        return self.ctx.at_end()
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        token = self.peek()
        
        # Compatibility fix for ModularLexer: handle keywords tokenized as WORD
        if token.type == TokenType.WORD:
            if (TokenType.IN in token_types and token.value == "in"):
                return True
            elif (TokenType.ESAC in token_types and token.value == "esac"):
                return True
        
        return self.ctx.match(*token_types)
    
    def expect(self, token_type: TokenType, message: Optional[str] = None) -> Token:
        """Consume token of expected type or raise error."""
        token = self.peek()
        
        # Compatibility fix for ModularLexer: handle keywords tokenized as WORD
        if token.type == TokenType.WORD:
            if (token_type == TokenType.IN and token.value == "in"):
                return self.advance()
            elif (token_type == TokenType.ESAC and token.value == "esac"):
                return self.advance()
        
        return self.ctx.consume(token_type, message)
    
    def consume_if(self, token_type: TokenType) -> Optional[Token]:
        """Consume token if it matches type, otherwise return None."""
        if self.match(token_type):
            return self.advance()
        return None
    
    # === Context State Management ===
    
    def enter_scope(self, scope: str):
        """Enter a parsing scope."""
        self.ctx.enter_scope(scope)
    
    def exit_scope(self) -> Optional[str]:
        """Exit current parsing scope."""
        return self.ctx.exit_scope()
    
    def enter_rule(self, rule_name: str):
        """Enter a parse rule (for debugging/profiling)."""
        self.ctx.enter_rule(rule_name)
    
    def exit_rule(self, rule_name: str):
        """Exit a parse rule (for debugging/profiling)."""
        self.ctx.exit_rule(rule_name)
    
    def in_scope(self, scope: str) -> bool:
        """Check if currently in a specific scope."""
        return self.ctx.in_scope(scope)
    
    def in_loop(self) -> bool:
        """Check if currently parsing inside a loop."""
        return self.ctx.in_loop()
    
    def in_function(self) -> bool:
        """Check if currently parsing inside a function."""
        return self.ctx.in_function()
    
    def in_conditional(self) -> bool:
        """Check if currently parsing inside a conditional."""
        return self.ctx.in_conditional()
    
    # === Error Handling ===
    
    def error(self, message: str, token: Optional[Token] = None) -> ParseError:
        """Create a ParseError with context."""
        if token is None:
            token = self.peek()
        
        error_context = self.ctx._create_error_context(message, token)
        return ParseError(error_context)
    
    def should_collect_errors(self) -> bool:
        """Check if errors should be collected rather than thrown."""
        return self.ctx.should_collect_errors()
    
    def should_attempt_recovery(self) -> bool:
        """Check if error recovery should be attempted."""
        return self.ctx.should_attempt_recovery()
    
    def add_error(self, error: ParseError) -> bool:
        """Add error to context and return whether parsing should continue."""
        if self.ctx.config.collect_errors:
            self.ctx.errors.append(error)
            return self.ctx.can_continue_parsing()
        else:
            raise error
    
    # === Configuration Queries ===
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a parsing feature is enabled."""
        return self.ctx.config.is_feature_enabled(feature)
    
    def should_allow(self, capability: str) -> bool:
        """Check if a parsing capability should be allowed."""
        return self.ctx.config.should_allow(capability)
    
    def require_feature(self, feature: str, error_message: str = None) -> None:
        """Require that a feature is enabled, otherwise raise an error."""
        if not self.is_feature_enabled(feature):
            message = error_message or f"{feature} is not enabled in current parsing mode"
            error = self.error(message)
            self.add_error(error)
    
    def check_posix_compliance(self, feature: str, alternative: str = None) -> None:
        """Check POSIX compliance for a feature."""
        from .config import ParsingMode
        if self.ctx.config.parsing_mode == ParsingMode.STRICT_POSIX:
            message = f"{feature} is not POSIX compliant"
            if alternative:
                message += f". Use {alternative} instead"
            error = self.error(message)
            self.add_error(error)
    
    # === Utility Methods ===
    
    def skip_newlines(self):
        """Skip over newline tokens."""
        while self.match(TokenType.NEWLINE):
            self.advance()
    
    def skip_separators(self):
        """Skip over statement separators (newlines, semicolons)."""
        while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
            self.advance()
    
    def match_any(self, token_types: Set[TokenType]) -> bool:
        """Check if current token matches any in the set."""
        return self.peek().type in token_types
    
    def previous(self) -> Token:
        """Get the previous token."""
        if self.ctx.current > 0:
            return self.ctx.tokens[self.ctx.current - 1]
        return self.ctx.tokens[0] if self.ctx.tokens else Token(TokenType.EOF, "", 0)
    
    def synchronize(self, sync_tokens: Set[TokenType]):
        """Synchronize to recovery points after error."""
        self.ctx.enter_error_recovery()
        
        while not self.at_end() and not self.match_any(sync_tokens):
            self.advance()
        
        self.ctx.exit_error_recovery()
    
    # === Token Group Utilities ===
    
    def match_statement_start(self) -> bool:
        """Check if current token can start a statement."""
        return self.match_any(TokenGroups.STATEMENT_START)
    
    def match_redirection_start(self) -> bool:
        """Check if current token can start a redirection."""
        return self.match_any(TokenGroups.REDIRECTION_OPERATORS)
    
    def match_control_structure(self) -> bool:
        """Check if current token starts a control structure."""
        return self.match_any(TokenGroups.CONTROL_STRUCTURE_KEYWORDS)
    
    # === Debugging Support ===
    
    def trace(self, message: str):
        """Emit trace message if tracing is enabled."""
        if self.ctx.trace_enabled:
            indent = "  " * self.ctx.rule_stack_depth()
            print(f"{indent}{message}")
    
    def get_position_info(self, token: Optional[Token] = None) -> str:
        """Get position information for debugging."""
        if token is None:
            token = self.peek()
        
        if self.ctx.source_text and token.line:
            return f"line {token.line}, column {token.column}"
        else:
            return f"position {token.position}"
    
    # === Rule Management with Context ===
    
    def parse_with_rule(self, rule_name: str, parse_func, *args, **kwargs):
        """Execute parsing function with rule tracking."""
        self.enter_rule(rule_name)
        try:
            return parse_func(*args, **kwargs)
        finally:
            self.exit_rule(rule_name)
    
    def parse_scoped(self, scope: str, parse_func, *args, **kwargs):
        """Execute parsing function with scope tracking."""
        self.enter_scope(scope)
        try:
            return parse_func(*args, **kwargs)
        finally:
            self.exit_scope()
    
    # === Compatibility Methods ===
    
    def _token_type_to_string(self, token_type: TokenType) -> str:
        """Convert token type to readable string."""
        return str(token_type).replace('TokenType.', '').lower()
    
    # === State Queries ===
    
    def get_state_summary(self) -> dict:
        """Get summary of current parser state."""
        return self.ctx.get_state_summary()
    
    def generate_profiling_report(self) -> str:
        """Generate profiling report if enabled."""
        return self.ctx.generate_profiling_report()


# Compatibility adapter for existing code
class BaseParser(ContextBaseParser):
    """Compatibility adapter for existing BaseParser users.
    
    This adapter allows existing code to work with the new context-based
    architecture while providing a migration path.
    """
    
    def __init__(self, tokens: List[Token]):
        # Create a default context for backward compatibility
        from .context_factory import ParserContextFactory
        ctx = ParserContextFactory.create(tokens)
        super().__init__(ctx)
        
        # Expose tokens and current for backward compatibility
        self.tokens = self.ctx.tokens
        
        # Import old ParseContext for compatibility
        from .helpers import ParseContext
        self.context = ParseContext()
    
    @property
    def current(self) -> int:
        """Backward compatibility property."""
        return self.ctx.current
    
    @current.setter
    def current(self, value: int):
        """Backward compatibility property setter."""
        self.ctx.current = value
    
    def peek_ahead(self, n: int = 1) -> Optional[Token]:
        """Backward compatibility method."""
        return self.peek(n) if not self.at_end() else None