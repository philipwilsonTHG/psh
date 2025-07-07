"""Token recognizer system for modular lexing."""

from .base import TokenRecognizer
from .operator import OperatorRecognizer
from .keyword import KeywordRecognizer
from .literal import LiteralRecognizer
from .whitespace import WhitespaceRecognizer
from .comment import CommentRecognizer
from .registry import RecognizerRegistry, setup_default_recognizers

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