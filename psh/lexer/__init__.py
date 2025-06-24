"""Advanced lexer package with Unicode support.

This package provides a state machine-based lexer for shell tokenization
with comprehensive Unicode support, configurable features, and enhanced
error handling.

The main entry point is the StateMachineLexer class and the tokenize() function
for drop-in compatibility with the original tokenizer.
"""

from typing import List
from ..token_types import Token

# Core lexer components
from .core import StateMachineLexer
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

__version__ = "0.58.0"


def tokenize(input_string: str) -> List[Token]:
    """
    Drop-in replacement for the existing tokenize function.
    
    This maintains the same interface but uses the state machine lexer
    for better tokenization with preserved context.
    
    Args:
        input_string: The shell command string to tokenize
        
    Returns:
        List of tokens representing the parsed command
    """
    from ..brace_expansion import BraceExpander, BraceExpansionError
    from ..token_transformer import TokenTransformer
    
    try:
        # Expand braces first (same as original)
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError:
        # If brace expansion fails, use original string
        lexer = StateMachineLexer(input_string)
        tokens = lexer.tokenize()
    else:
        # Run state machine lexer on expanded string
        lexer = StateMachineLexer(expanded_string)
        tokens = lexer.tokenize()
    
    # Apply token transformations (same as original)
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)
    
    return tokens


__all__ = [
    # Main lexer interface
    'StateMachineLexer', 'tokenize',
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
    'LexerHelpers', 'StateHandlers'
]