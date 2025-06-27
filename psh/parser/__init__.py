"""
Parser package for PSH shell.

This package provides a modular parser implementation with clear separation of concerns.
The parser is responsible for converting tokens into an Abstract Syntax Tree (AST).
"""

from .main import Parser
from .helpers import ParseError, TokenGroups
from .base import BaseParser

# Public API
__all__ = ['parse', 'parse_with_heredocs', 'Parser', 'ParseError', 'TokenGroups', 'BaseParser']


def parse(tokens):
    """Parse tokens into AST."""
    return Parser(tokens).parse()


def parse_with_heredocs(tokens, heredoc_map):
    """Parse tokens with heredoc content."""
    from .utils import parse_with_heredocs as utils_parse_with_heredocs
    return utils_parse_with_heredocs(tokens, heredoc_map)