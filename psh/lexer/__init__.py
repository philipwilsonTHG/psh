"""Advanced lexer package for PSH shell tokenization.

This package provides a unified lexer for shell tokenization with comprehensive 
Unicode support, metadata tracking, and context-aware parsing. Enhanced 
functionality is now built into the standard Token class and ModularLexer.

The main entry point is the tokenize() function which uses the ModularLexer
as the single lexer implementation.
"""

from typing import List

from ..token_types import Token
from .constants import DOUBLE_QUOTE_ESCAPES, KEYWORDS, OPERATORS_BY_LENGTH, SPECIAL_VARIABLES, WORD_TERMINATORS
from .helpers import LexerHelpers
from .keyword_normalizer import KeywordNormalizer

# Core lexer components
from .modular_lexer import ModularLexer
from .position import (
    LexerConfig,
    LexerError,
    LexerErrorHandler,
    LexerState,
    Position,
    PositionTracker,
    RecoverableLexerError,
)
from .state_context import LexerContext
from .token_parts import RichToken, TokenPart
from .unicode_support import (
    is_identifier_char,
    is_identifier_start,
    is_whitespace,
    normalize_identifier,
    validate_identifier,
)

__version__ = "0.91.1"  # Phase 3 Day 2: Clean imports and dependencies

def tokenize(input_string: str, strict: bool = True, shell_options: dict = None) -> List[Token]:
    """
    Tokenize a shell command string using the unified lexer implementation.

    This function provides the main entry point for shell tokenization with
    comprehensive Unicode support, metadata tracking, context awareness, and
    enhanced error handling - all features built into the standard Token class.

    Args:
        input_string: The shell command string to tokenize
        strict: If True, use strict mode (batch); if False, use interactive mode
        shell_options: Optional shell options dict to configure extglob etc.

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

    # Apply shell options to lexer config
    if shell_options and shell_options.get('extglob', False):
        config.enable_extglob = True

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

    # Normalize keywords before running additional transformations
    normalizer = KeywordNormalizer()
    tokens = normalizer.normalize(tokens)

    # Apply token transformations
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)

    return tokens


def tokenize_with_heredocs(input_string: str, strict: bool = True, shell_options: dict = None):
    """
    Tokenize a shell command string with heredoc support.

    This function tokenizes shell commands that may contain heredocs,
    collecting the heredoc content for later processing.

    Args:
        input_string: The shell command string to tokenize
        strict: If True, use strict mode (batch); if False, use interactive mode
        shell_options: Optional shell options dict to configure extglob etc.

    Returns:
        Tuple of (tokens, heredoc_map) where heredoc_map contains collected heredoc content
    """
    from .heredoc_lexer import HeredocLexer

    # Create appropriate lexer config based on strict mode
    if strict:
        config = LexerConfig.create_batch_config()
    else:
        config = LexerConfig.create_interactive_config()

    # Apply shell options to lexer config
    if shell_options and shell_options.get('extglob', False):
        config.enable_extglob = True

    # Use heredoc lexer
    lexer = HeredocLexer(input_string, config=config)
    tokens, heredoc_map = lexer.tokenize_with_heredocs()

    # Normalize keywords before transformations
    normalizer = KeywordNormalizer()
    tokens = normalizer.normalize(tokens)

    # Apply token transformations
    from ..token_transformer import TokenTransformer
    transformer = TokenTransformer()
    tokens = transformer.transform(tokens)

    return tokens, heredoc_map


__all__ = [
    # Main lexer interface
    'ModularLexer', 'tokenize', 'tokenize_with_heredocs',
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
    'LexerHelpers',
    # Context classes
    'LexerContext',
]
