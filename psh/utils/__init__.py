"""
PSH Utils Package

Utility modules supporting shell infrastructure:
- signal_utils: Signal handling with self-pipe pattern and registry
- shell_formatter: Reconstruct shell syntax from AST nodes
- parser_factory: Configurable parser instantiation
- heredoc_detection: Distinguish heredocs from bit-shift operators
- ast_debug: AST visualization for debugging
- file_tests: File comparison utilities for test expressions
- token_formatter: Token list formatting for debug output
"""

from .ast_debug import print_ast_debug
from .file_tests import file_newer_than, file_older_than, files_same, to_int
from .heredoc_detection import contains_heredoc
from .parser_factory import create_parser
from .shell_formatter import ShellFormatter
from .signal_utils import SignalNotifier, get_signal_registry
from .token_formatter import TokenFormatter

__all__ = [
    'SignalNotifier',
    'get_signal_registry',
    'ShellFormatter',
    'create_parser',
    'contains_heredoc',
    'print_ast_debug',
    'TokenFormatter',
    'to_int',
    'file_newer_than',
    'file_older_than',
    'files_same',
]
