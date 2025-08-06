"""
Parser package for PSH shell.

This package provides a unified parser implementation with comprehensive features.
The parser converts tokens into an Abstract Syntax Tree (AST) with metadata support,
context-aware parsing, semantic analysis, and enhanced error recovery.
"""

from typing import Optional

# Temporary compatibility layer during parser refactoring
try:
    # Try to import from new location
    from .recursive_descent.parser import Parser
    from .recursive_descent.helpers import ParseError, TokenGroups
    from .recursive_descent.base import BaseParser
    from .recursive_descent.context import ParserContext, ParserProfiler, HeredocInfo
    from .recursive_descent.support.context_factory import ParserContextFactory, ContextConfiguration
    from .recursive_descent.support.context_snapshots import ContextSnapshot, BacktrackingParser, SpeculativeParser
except ImportError:
    # Fall back to old locations if not yet moved
    from .main import Parser
    from .helpers import ParseError, TokenGroups
    from .base import BaseParser
    from .context import ParserContext, ParserProfiler, HeredocInfo
    from .context_factory import ParserContextFactory, ContextConfiguration
    from .context_snapshots import ContextSnapshot, BacktrackingParser, SpeculativeParser
from .config import ParserConfig, ParsingMode, ErrorHandlingMode
from .factory import ParserFactory, ConfigurationValidator

# Standard parser components (enhanced features built-in)
try:
    from .recursive_descent.base_context import ContextBaseParser
except ImportError:
    from .base_context import ContextBaseParser
from .integration_manager import create_fully_enhanced_parser as create_parser

# Public API
__all__ = [
    # Main API
    'parse', 'parse_with_heredocs', 'Parser', 'ParseError', 'TokenGroups', 'BaseParser',
    'ContextBaseParser', 'ParserContext', 'ParserContextFactory', 'ContextConfiguration',
    'ContextSnapshot', 'BacktrackingParser', 'SpeculativeParser', 'ParserProfiler', 'HeredocInfo',
    'ParserConfig', 'ParsingMode', 'ErrorHandlingMode', 'ParserFactory', 'ConfigurationValidator',
    # Standard parser components
    'create_parser',
    # Parsing modes
    'parse_strict_posix', 'parse_bash_compatible', 'parse_permissive'
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
    from .utils import parse_with_heredocs as utils_parse_with_heredocs
    return utils_parse_with_heredocs(tokens, heredoc_map)


def parse_strict_posix(tokens, source_text=None):
    """Parse tokens with strict POSIX compliance.
    
    Args:
        tokens: List of tokens to parse
        source_text: Optional source text for error reporting
        
    Returns:
        Parsed AST in strict POSIX mode
    """
    return ParserFactory.create_strict_posix_parser(tokens, source_text).parse()


def parse_bash_compatible(tokens, source_text=None):
    """Parse tokens with Bash compatibility.
    
    Args:
        tokens: List of tokens to parse
        source_text: Optional source text for error reporting
        
    Returns:
        Parsed AST in Bash-compatible mode
    """
    return ParserFactory.create_bash_compatible_parser(tokens, source_text).parse()


def parse_permissive(tokens, source_text=None):
    """Parse tokens in permissive mode with error collection.
    
    Args:
        tokens: List of tokens to parse
        source_text: Optional source text for error reporting
        
    Returns:
        Parsed AST (may be partial if errors occurred)
    """
    return ParserFactory.create_permissive_parser(tokens, source_text).parse()




"""Temporary compatibility layer during parser refactoring.

This module provides forwarding imports to maintain backward compatibility
while migrating the recursive descent parser to its own package.
"""

# Phase 2: Core forwarding imports
try:
    from .recursive_descent.parser import Parser
    from .recursive_descent.base import BaseParser
    from .recursive_descent.context import ParserContext
    from .recursive_descent.helpers import ParseError, ErrorContext, TokenGroups
except ImportError:
    # Fall back to original locations if not yet moved
    from .main import Parser
    from .base import BaseParser
    from .context import ParserContext
    from .helpers import ParseError, ErrorContext, TokenGroups

# Export for backward compatibility
__all__ = ['Parser', 'BaseParser', 'ParserContext', 'ParseError', 'ErrorContext', 'TokenGroups']
