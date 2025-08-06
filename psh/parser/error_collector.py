"""Error collection for multi-error parsing."""

from typing import List, Optional, Set
from dataclasses import dataclass, field
try:
    from .recursive_descent.helpers import ParseError
except ImportError:
    from .recursive_descent.helpers import ParseError
from ..token_types import TokenType


@dataclass
class RecoveryPoints:
    """Define synchronization points for error recovery."""
    
    # Statement starting tokens
    STATEMENT_START: Set[TokenType] = field(default_factory=lambda: {
        TokenType.IF, TokenType.WHILE, TokenType.FOR,
        TokenType.CASE, TokenType.FUNCTION, TokenType.WORD,
        TokenType.LBRACE, TokenType.DOUBLE_LBRACKET
    })
    
    # Statement ending tokens
    STATEMENT_END: Set[TokenType] = field(default_factory=lambda: {
        TokenType.SEMICOLON, TokenType.NEWLINE, 
        TokenType.AMPERSAND, TokenType.PIPE,
        TokenType.AND_AND, TokenType.OR_OR
    })
    
    # Block ending tokens
    BLOCK_END: Set[TokenType] = field(default_factory=lambda: {
        TokenType.FI, TokenType.DONE, TokenType.ESAC,
        TokenType.RBRACE, TokenType.EOF, TokenType.RPAREN
    })
    
    # All synchronization tokens
    ALL_SYNC: Set[TokenType] = field(default_factory=lambda: set())
    
    def __post_init__(self):
        """Initialize ALL_SYNC with all recovery points."""
        self.ALL_SYNC = self.STATEMENT_START | self.STATEMENT_END | self.BLOCK_END


class ErrorCollector:
    """Collect multiple parse errors for batch reporting."""
    
    def __init__(self, max_errors: int = 10, stop_on_fatal: bool = True):
        """Initialize error collector.
        
        Args:
            max_errors: Maximum number of errors to collect
            stop_on_fatal: Whether to stop parsing on fatal errors
        """
        self.errors: List[ParseError] = []
        self.max_errors = max_errors
        self.stop_on_fatal = stop_on_fatal
        self.fatal_error: Optional[ParseError] = None
        self.recovery_points = RecoveryPoints()
    
    def add_error(self, error: ParseError) -> None:
        """Add error to collection.
        
        Args:
            error: ParseError to add to collection
        """
        if len(self.errors) < self.max_errors:
            self.errors.append(error)
        
        # Check if this is a fatal error
        if (hasattr(error.error_context, 'severity') and 
            error.error_context.severity == 'fatal'):
            self.fatal_error = error
    
    def should_continue(self) -> bool:
        """Check if parsing should continue.
        
        Returns:
            True if parsing should continue, False otherwise
        """
        # Stop if we hit max errors
        if len(self.errors) >= self.max_errors:
            return False
        
        # Stop if we have a fatal error and configured to stop
        if self.stop_on_fatal and self.fatal_error:
            return False
        
        return True
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected.
        
        Returns:
            True if errors have been collected
        """
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """Get number of collected errors.
        
        Returns:
            Number of errors collected
        """
        return len(self.errors)
    
    def get_errors_by_severity(self, severity: str) -> List[ParseError]:
        """Get errors filtered by severity.
        
        Args:
            severity: Severity level to filter by
            
        Returns:
            List of errors with matching severity
        """
        return [
            error for error in self.errors
            if (hasattr(error.error_context, 'severity') and
                error.error_context.severity == severity)
        ]
    
    def format_error_summary(self) -> str:
        """Format a summary of all collected errors.
        
        Returns:
            Formatted error summary string
        """
        if not self.errors:
            return "No errors collected."
        
        lines = []
        lines.append(f"Collected {len(self.errors)} parse error(s):")
        lines.append("")
        
        for i, error in enumerate(self.errors, 1):
            lines.append(f"{i}. {error.message}")
            
            # Add suggestions if available
            if (hasattr(error.error_context, 'suggestions') and 
                error.error_context.suggestions):
                for suggestion in error.error_context.suggestions[:2]:  # Limit to 2
                    lines.append(f"   Suggestion: {suggestion}")
            lines.append("")
        
        # Add fatal error info if present
        if self.fatal_error:
            lines.append("Fatal error encountered - parsing stopped.")
            lines.append("")
        
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors.clear()
        self.fatal_error = None


class ErrorRecoveryStrategy:
    """Strategies for recovering from parse errors."""
    
    @staticmethod
    def skip_to_sync_token(parser, sync_tokens: Set[TokenType]) -> bool:
        """Skip tokens until reaching a synchronization point.
        
        Args:
            parser: Parser instance
            sync_tokens: Set of tokens to synchronize on
            
        Returns:
            True if sync token found, False if EOF reached
        """
        while not parser.at_end() and not parser.match_any(sync_tokens):
            parser.advance()
        
        return not parser.at_end()
    
    @staticmethod
    def skip_to_statement_end(parser) -> bool:
        """Skip to the end of current statement.
        
        Args:
            parser: Parser instance
            
        Returns:
            True if statement end found, False if EOF reached
        """
        recovery_points = RecoveryPoints()
        return ErrorRecoveryStrategy.skip_to_sync_token(
            parser, recovery_points.STATEMENT_END
        )
    
    @staticmethod
    def skip_to_block_end(parser) -> bool:
        """Skip to the end of current block.
        
        Args:
            parser: Parser instance
            
        Returns:
            True if block end found, False if EOF reached
        """
        recovery_points = RecoveryPoints()
        return ErrorRecoveryStrategy.skip_to_sync_token(
            parser, recovery_points.BLOCK_END
        )
    
    @staticmethod
    def find_next_statement(parser) -> bool:
        """Find the start of the next statement.
        
        Args:
            parser: Parser instance
            
        Returns:
            True if next statement found, False if EOF reached
        """
        recovery_points = RecoveryPoints()
        return ErrorRecoveryStrategy.skip_to_sync_token(
            parser, recovery_points.STATEMENT_START
        )


class MultiErrorParseResult:
    """Result of parsing with error collection."""
    
    def __init__(self, ast=None, errors: List[ParseError] = None):
        """Initialize parse result.
        
        Args:
            ast: Parsed AST (may be partial)
            errors: List of parse errors encountered
        """
        self.ast = ast
        self.errors = errors or []
        self.success = ast is not None and len(self.errors) == 0
        self.partial_success = ast is not None and len(self.errors) > 0
    
    def has_errors(self) -> bool:
        """Check if parsing had errors."""
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """Get number of parse errors."""
        return len(self.errors)
    
    def format_errors(self) -> str:
        """Format all errors for display."""
        if not self.errors:
            return "No errors."
        
        lines = []
        for i, error in enumerate(self.errors, 1):
            lines.append(f"Error {i}: {error.message}")
        
        return "\n".join(lines)