#!/usr/bin/env python3
"""
State machine-based lexer for PSH - drop-in replacement for tokenizer.py

This module provides backward compatibility by re-exporting the lexer
components from the new package structure.
"""

from typing import List
from .token_types import Token

# Import from the new lexer package
from .lexer import StateMachineLexer, tokenize

# Re-export for backward compatibility
__all__ = ['StateMachineLexer', 'tokenize']