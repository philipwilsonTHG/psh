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


import os

# Configuration flag for choosing lexer implementation
# Phase C: ModularLexer is now the default, can be disabled with PSH_USE_LEGACY_LEXER=true
USE_LEGACY_LEXER = os.environ.get('PSH_USE_LEGACY_LEXER', 'false').lower() == 'true'

# For backward compatibility, still check PSH_USE_MODULAR_LEXER
USE_MODULAR_LEXER = os.environ.get('PSH_USE_MODULAR_LEXER', 'true').lower() == 'true'

# Phase B: Enable ModularLexer for interactive mode by default (kept for compatibility)
ENABLE_MODULAR_FOR_INTERACTIVE = os.environ.get('PSH_MODULAR_INTERACTIVE', 'true').lower() == 'true'

def tokenize(input_string: str, strict: bool = True) -> List[Token]:
    """
    Drop-in replacement for the existing tokenize function.
    
    This maintains the same interface but uses the state machine lexer
    for better tokenization with preserved context.
    
    Can be configured to use the new ModularLexer by setting the
    PSH_USE_MODULAR_LEXER environment variable to 'true'.
    
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
    
    # Determine which lexer to use
    # Phase C: ModularLexer is the default unless explicitly disabled
    if USE_LEGACY_LEXER:
        use_modular = False
    elif not USE_MODULAR_LEXER:
        # PSH_USE_MODULAR_LEXER=false explicitly disables it
        use_modular = False
    else:
        # Default is to use ModularLexer
        use_modular = True
    
    try:
        # Expand braces first (same as original)
        expander = BraceExpander()
        expanded_string = expander.expand_line(input_string)
    except BraceExpansionError:
        # If brace expansion fails, use original string
        if use_modular:
            from .modular_lexer import ModularLexer
            lexer = ModularLexer(input_string, config=config)
        else:
            lexer = StateMachineLexer(input_string, config=config)
        tokens = lexer.tokenize()
    else:
        # Run state machine lexer on expanded string
        if use_modular:
            from .modular_lexer import ModularLexer
            lexer = ModularLexer(expanded_string, config=config)
        else:
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