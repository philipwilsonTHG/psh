"""Advanced lexer package for PSH shell tokenization.

This package provides a unified lexer for shell tokenization with comprehensive 
Unicode support, metadata tracking, and context-aware parsing. Enhanced 
functionality is now built into the standard Token class and ModularLexer.

The main entry point is the tokenize() function which uses the ModularLexer
as the single lexer implementation.
"""

from typing import List
from ..token_types import Token

# Core lexer components
from .modular_lexer import ModularLexer
from .position import (
    Position, LexerState, LexerConfig, LexerError, RecoverableLexerError,
    LexerErrorHandler, PositionTracker
)
from .constants import (
    KEYWORDS, OPERATORS_BY_LENGTH, SPECIAL_VARIABLES,
    DOUBLE_QUOTE_ESCAPES, WORD_TERMINATORS
)
from .unicode_support import (
    is_identifier_start, is_identifier_char, is_whitespace,
    normalize_identifier, validate_identifier
)
from .token_parts import TokenPart, RichToken
from .helpers import LexerHelpers
from .state_handlers import StateHandlers
from .state_context import LexerContext

__version__ = "0.91.1"  # Phase 3 Day 2: Clean imports and dependencies

def tokenize(input_string: str, strict: bool = True) -> List[Token]:
    """
    Tokenize a shell command string using the unified lexer implementation.
    
    This function provides the main entry point for shell tokenization with 
    comprehensive Unicode support, metadata tracking, context awareness, and 
    enhanced error handling - all features built into the standard Token class.
    
    Args:
        input_string: The shell command string to tokenize
        strict: If True, use strict mode (batch); if False, use interactive mode
        
    Returns:
        List of tokens representing the parsed command
    """
    from ..brace_expansion import BraceExpander, BraceExpansionError
    from ..token_transformer import TokenTransformer
    
    # Create appropriate lexer config based on strict mode
    if strict:
        config = LexerConfig.create_batch_config()
    else:
        config = LexerConfig.create_interactive_config()
    
    try:
        # Expand braces first
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError:
        # If brace expansion fails, use original string
        lexer = ModularLexer(input_string, config=config)
        tokens = lexer.tokenize()
    else:
        # Run modular lexer on expanded string
        lexer = ModularLexer(expanded_string, config=config)
        tokens = lexer.tokenize()
    
    # Apply token transformations
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)
    
    return tokens


__all__ = [
    # Main lexer interface
    'ModularLexer', 'tokenize',
    # Position and configuration
    'Position', 'LexerState', 'LexerConfig', 'LexerError', 'RecoverableLexerError',
    'LexerErrorHandler', 'PositionTracker',
    # Constants
    'KEYWORDS', 'OPERATORS_BY_LENGTH', 'SPECIAL_VARIABLES',
    'DOUBLE_QUOTE_ESCAPES', 'WORD_TERMINATORS',
    # Unicode support
    'is_identifier_start', 'is_identifier_char', 'is_whitespace',
    'normalize_identifier', 'validate_identifier',
    # Token classes
    'TokenPart', 'RichToken',
    # Mixin classes (for advanced usage)
    'LexerHelpers', 'StateHandlers',
    # Context classes
    'LexerContext',
]