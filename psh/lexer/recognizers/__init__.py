"""Token recognizer system for modular lexing."""

from .base import TokenRecognizer
from .comment import CommentRecognizer
from .keyword import KeywordRecognizer
from .literal import LiteralRecognizer
from .operator import OperatorRecognizer
from .registry import RecognizerRegistry, setup_default_recognizers
from .whitespace import WhitespaceRecognizer

__all__ = [
    'TokenRecognizer',
    'OperatorRecognizer',
    'KeywordRecognizer',
    'LiteralRecognizer',
    'WhitespaceRecognizer',
    'CommentRecognizer',
    'RecognizerRegistry',
    'setup_default_recognizers'
]
