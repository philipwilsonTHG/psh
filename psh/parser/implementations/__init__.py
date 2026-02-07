"""Parser implementations for experimentation.

This package contains various parser implementations that conform to
the AbstractShellParser interface, allowing for educational comparison
of different parsing approaches.
"""

# Import the new modular parser combinator implementation
from ..combinators.parser import ParserCombinatorShellParser
from .recursive_descent_adapter import RecursiveDescentAdapter

__all__ = [
    'RecursiveDescentAdapter',
    'ParserCombinatorShellParser',
]
