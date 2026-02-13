"""
Parser package for PSH shell.

This package provides a unified parser implementation with comprehensive features.
The parser converts tokens into an Abstract Syntax Tree (AST) with metadata support,
context-aware parsing, semantic analysis, and enhanced error recovery.
"""

from .config import ErrorHandlingMode, ParserConfig, ParsingMode
from .recursive_descent.context import ParserContext, ParserProfiler
from .recursive_descent.helpers import ErrorContext, ParseError

# Import from final locations
from .recursive_descent.parser import Parser
from .recursive_descent.support.context_factory import create_context
from .recursive_descent.support.utils import parse_with_heredocs as utils_parse_with_heredocs

# Public API
__all__ = [
    # Main parsing interface
    'parse', 'parse_with_heredocs', 'Parser',
    # Configuration
    'ParserConfig',
    # Errors
    'ParseError',
]


def parse(tokens, config=None):
    """Parse tokens into AST using the unified parser implementation.

    This function provides comprehensive parsing with metadata utilization,
    context-aware analysis, and enhanced error handling - all features built
    into the standard parser.

    Args:
        tokens: List of tokens to parse
        config: Optional ParserConfig for custom parsing behavior

    Returns:
        Parsed AST with full feature support
    """
    if config is None:
        config = ParserConfig()

    return Parser(tokens, config=config).parse()


def parse_with_heredocs(tokens, heredoc_map):
    """Parse tokens with heredoc content."""
    return utils_parse_with_heredocs(tokens, heredoc_map)
