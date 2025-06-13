#!/usr/bin/env python3
"""Token type definitions for PSH lexer and parser."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class TokenType(Enum):
    """All token types recognized by the shell lexer."""
    # Basic tokens
    WORD = auto()
    PIPE = auto()
    REDIRECT_IN = auto()
    REDIRECT_OUT = auto()
    REDIRECT_APPEND = auto()
    REDIRECT_ERR = auto()
    REDIRECT_ERR_APPEND = auto()
    REDIRECT_DUP = auto()
    HEREDOC = auto()
    HEREDOC_STRIP = auto()
    HERE_STRING = auto()
    SEMICOLON = auto()
    AMPERSAND = auto()
    AND_AND = auto()
    OR_OR = auto()
    NEWLINE = auto()
    EOF = auto()
    
    # Quoted strings and variables
    STRING = auto()
    VARIABLE = auto()
    
    # Expansions
    COMMAND_SUB = auto()
    COMMAND_SUB_BACKTICK = auto()
    ARITH_EXPANSION = auto()
    PROCESS_SUB_IN = auto()    # <(...)
    PROCESS_SUB_OUT = auto()   # >(...)
    
    # Grouping
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    DOUBLE_LPAREN = auto()  # ((
    
    # Keywords
    FUNCTION = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FI = auto()
    ELIF = auto()
    WHILE = auto()
    DO = auto()
    DONE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    CASE = auto()
    ESAC = auto()
    SELECT = auto()
    
    # Case terminators
    DOUBLE_SEMICOLON = auto()  # ;;
    SEMICOLON_AMP = auto()     # ;&
    AMP_SEMICOLON = auto()     # ;;&
    
    # Special operators
    EXCLAMATION = auto()       # !
    DOUBLE_LBRACKET = auto()   # [[
    DOUBLE_RBRACKET = auto()   # ]]
    REGEX_MATCH = auto()       # =~
    
    # Composite tokens
    COMPOSITE = auto()         # Merged adjacent tokens


@dataclass
class Token:
    """A lexical token with type, value, and position information."""
    type: TokenType
    value: str
    position: int
    end_position: int = 0  # Position after the last character of the token
    quote_type: Optional[str] = None  # Track the quote character used (' or " or None)