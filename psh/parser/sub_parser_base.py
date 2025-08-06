"""Base class for context-aware sub-parsers.

This module provides the SubParserBase class that allows sub-parsers
to work with the centralized ParserContext.
"""

from typing import TYPE_CHECKING
from .recursive_descent.context import ParserContext

if TYPE_CHECKING:
    from .recursive_descent.parser import Parser


class SubParserBase:
    """Base class for sub-parsers that use centralized context.
    
    This class provides access to the shared parser context while maintaining
    backward compatibility with the main parser reference.
    """
    
    def __init__(self, main_parser: 'Parser'):
        """Initialize with reference to main parser."""
        self.parser = main_parser
        self.ctx = main_parser.ctx
    
    # === Context Delegation Methods ===
    
    def peek(self, offset: int = 0):
        """Look at current token + offset without consuming."""
        return self.ctx.peek(offset)
    
    def advance(self):
        """Consume and return current token."""
        return self.ctx.advance()
    
    def at_end(self) -> bool:
        """Check if at end of tokens."""
        return self.ctx.at_end()
    
    def match(self, *token_types):
        """Check if current token matches any of the given types."""
        return self.ctx.match(*token_types)
    
    def consume(self, token_type, error_message: str = None):
        """Consume token of expected type or raise error."""
        return self.ctx.consume(token_type, error_message)
    
    def skip_newlines(self):
        """Skip over newline tokens."""
        while self.match('NEWLINE'):
            self.advance()
    
    def skip_separators(self):
        """Skip over statement separators."""
        from ..token_types import TokenType
        while self.match(TokenType.NEWLINE, TokenType.SEMICOLON):
            self.advance()
    
    # === Context State ===
    
    def enter_scope(self, scope: str):
        """Enter a parsing scope."""
        self.ctx.enter_scope(scope)
    
    def exit_scope(self):
        """Exit current parsing scope."""
        return self.ctx.exit_scope()
    
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
    
    def error(self, message: str, token=None):
        """Create a ParseError with context."""
        return self.ctx._create_error_context(message, token or self.peek())
    
    def should_collect_errors(self) -> bool:
        """Check if errors should be collected rather than thrown."""
        return self.ctx.should_collect_errors()
    
    def should_attempt_recovery(self) -> bool:
        """Check if error recovery should be attempted."""
        return self.ctx.should_attempt_recovery()
    
    # === Configuration Queries ===
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a parsing feature is enabled."""
        return self.ctx.config.is_feature_enabled(feature)
    
    def should_allow(self, capability: str) -> bool:
        """Check if a parsing capability should be allowed."""
        return self.ctx.config.should_allow(capability)
    
    def require_feature(self, feature: str, error_message: str = None):
        """Require that a feature is enabled, otherwise raise an error."""
        if not self.is_feature_enabled(feature):
            message = error_message or f"{feature} is not enabled in current parsing mode"
            error = self.error(message)
            if self.should_collect_errors():
                self.ctx.errors.append(error)
            else:
                raise error
    
    # === Rule Tracking ===
    
    def enter_rule(self, rule_name: str):
        """Enter a parse rule."""
        self.ctx.enter_rule(rule_name)
    
    def exit_rule(self, rule_name: str):
        """Exit a parse rule."""
        self.ctx.exit_rule(rule_name)
    
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
    
    # === Utility Methods ===
    
    def match_any(self, token_set):
        """Check if current token is in the given set."""
        return self.peek().type in token_set
    
    def consume_if_match(self, *token_types):
        """Consume and return token if it matches any of the given types."""
        if self.match(*token_types):
            return self.advance()
        return None
    
    def save_position(self) -> int:
        """Save current parser position."""
        return self.ctx.current
    
    def restore_position(self, position: int):
        """Restore parser to saved position."""
        self.ctx.current = position


class LegacySubParserAdapter:
    """Adapter to help existing sub-parsers transition to context-based parsing.
    
    This adapter provides the same interface as before but delegates to
    context-based methods where possible.
    """
    
    def __init__(self, main_parser: 'Parser'):
        self.parser = main_parser
        self.ctx = main_parser.ctx
    
    # === Legacy Method Delegation ===
    
    def peek(self):
        """Legacy method that maps to context."""
        return self.parser.peek()
    
    def advance(self):
        """Legacy method that maps to context."""
        return self.parser.advance()
    
    def at_end(self):
        """Legacy method that maps to context."""
        return self.parser.at_end()
    
    def match(self, *token_types):
        """Legacy method that maps to context."""
        return self.parser.match(*token_types)
    
    def expect(self, token_type, message=None):
        """Legacy method that maps to context."""
        return self.parser.expect(token_type, message)
    
    def match_any(self, token_set):
        """Legacy method that maps to context."""
        return self.parser.match_any(token_set)
    
    def skip_newlines(self):
        """Legacy method that maps to context."""
        return self.parser.skip_newlines()
    
    def skip_separators(self):
        """Legacy method that maps to context."""
        return self.parser.skip_separators()
    
    def save_position(self):
        """Legacy method that maps to context."""
        return self.parser.save_position()
    
    def restore_position(self, position):
        """Legacy method that maps to context."""
        return self.parser.restore_position(position)
    
    def _error(self, message, token=None):
        """Legacy method that maps to context."""
        return self.parser._error(message, token)
    
    # === Configuration Methods ===
    
    def is_feature_enabled(self, feature):
        """Legacy method that maps to context."""
        return self.parser.is_feature_enabled(feature)
    
    def should_allow(self, capability):
        """Legacy method that maps to context."""
        return self.parser.should_allow(capability)
    
    def require_feature(self, feature, error_message=None):
        """Legacy method that maps to context."""
        return self.parser.require_feature(feature, error_message)
    
    def check_posix_compliance(self, feature, alternative=None):
        """Legacy method that maps to context."""
        return self.parser.check_posix_compliance(feature, alternative)