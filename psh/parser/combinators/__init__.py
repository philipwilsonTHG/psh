"""Parser combinator module for PSH.

This module provides a modular, functional approach to parsing shell syntax
using parser combinators. The implementation is split across multiple files
for better organization and maintainability.
"""

from .core import (
    ParseResult,
    Parser,
    ForwardParser,
    # Basic combinators
    token,
    many,
    many1,
    optional,
    sequence,
    separated_by,
    # Enhanced combinators
    lazy,
    between,
    skip,
    fail_with,
    try_parse,
    keyword,
    literal,
    with_error_context,
)

from .tokens import (
    TokenParsers,
    create_token_parsers,
    # Convenience functions
    pipe_separator,
    semicolon_separator,
    newline_separator,
    statement_terminator,
    logical_and,
    logical_or,
    background_operator,
)

from .expansions import (
    ExpansionParsers,
    create_expansion_parsers,
    # Convenience functions
    parse_variable_expansion,
    parse_command_substitution,
    parse_arithmetic_expansion,
    parse_parameter_expansion,
    parse_process_substitution,
)

from .commands import (
    CommandParsers,
    create_command_parsers,
    # Convenience functions
    parse_simple_command,
    parse_pipeline,
    parse_and_or_list,
)

__all__ = [
    # Core classes
    'ParseResult',
    'Parser',
    'ForwardParser',
    # Basic combinators
    'token',
    'many',
    'many1',
    'optional',
    'sequence',
    'separated_by',
    # Enhanced combinators
    'lazy',
    'between',
    'skip',
    'fail_with',
    'try_parse',
    'keyword',
    'literal',
    'with_error_context',
    # Token parsers
    'TokenParsers',
    'create_token_parsers',
    'pipe_separator',
    'semicolon_separator',
    'newline_separator',
    'statement_terminator',
    'logical_and',
    'logical_or',
    'background_operator',
    # Expansion parsers
    'ExpansionParsers',
    'create_expansion_parsers',
    'parse_variable_expansion',
    'parse_command_substitution',
    'parse_arithmetic_expansion',
    'parse_parameter_expansion',
    'parse_process_substitution',
    # Command parsers
    'CommandParsers',
    'create_command_parsers',
    'parse_simple_command',
    'parse_pipeline',
    'parse_and_or_list',
]