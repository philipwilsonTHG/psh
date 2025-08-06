"""Parser implementations for experimentation.

This package contains various parser implementations that conform to
the AbstractShellParser interface, allowing for educational comparison
of different parsing approaches.
"""

from .recursive_descent_adapter import RecursiveDescentAdapter

# Import the new modular parser combinator implementation
from ..combinators.parser import ParserCombinatorShellParser

__all__ = [
    'RecursiveDescentAdapter',
    'ParserCombinatorShellParser',
]