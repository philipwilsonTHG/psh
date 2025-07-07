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
from .enhanced_core import EnhancedStateMachineLexer
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

# New unified state management components
from .state_context import LexerContext
from .transitions import StateTransition, TransitionTable, StateManager

# Pure helper functions (Phase 2)
from . import pure_helpers
from .enhanced_helpers import EnhancedLexerHelpers

__version__ = "0.58.0"


def tokenize(input_string: str, strict: bool = True) -> List[Token]:
    """
    Drop-in replacement for the existing tokenize function.
    
    This maintains the same interface but uses the state machine lexer
    for better tokenization with preserved context.
    
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
        config = LexerConfig.create_batch_config()  # strict_mode=True
    else:
        config = LexerConfig.create_interactive_config()  # strict_mode=False
    
    try:
        # Expand braces first (same as original)
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError:
        # If brace expansion fails, use original string
        lexer = StateMachineLexer(input_string, config=config)
        tokens = lexer.tokenize()
    else:
        # Run state machine lexer on expanded string
        lexer = StateMachineLexer(expanded_string, config=config)
        tokens = lexer.tokenize()
    
    # Apply token transformations (same as original)
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)
    
    return tokens


__all__ = [
    # Main lexer interface
    'StateMachineLexer', 'EnhancedStateMachineLexer', 'tokenize',
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
    'LexerHelpers', 'StateHandlers', 'EnhancedLexerHelpers',
    # New state management components
    'LexerContext', 'StateTransition', 'TransitionTable', 'StateManager',
    # Pure helper functions
    'pure_helpers'
]