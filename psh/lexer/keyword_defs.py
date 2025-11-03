"""Shared keyword definitions and helpers."""

from typing import Optional

from ..token_types import TokenType
from ..token_enhanced import SemanticType

# Mapping between keyword strings and their canonical token types
KEYWORD_TYPE_MAP = {
    'if': TokenType.IF,
    'then': TokenType.THEN,
    'else': TokenType.ELSE,
    'elif': TokenType.ELIF,
    'fi': TokenType.FI,
    'for': TokenType.FOR,
    'select': TokenType.SELECT,
    'while': TokenType.WHILE,
    'until': TokenType.UNTIL,
    'do': TokenType.DO,
    'in': TokenType.IN,
    'done': TokenType.DONE,
    'case': TokenType.CASE,
    'esac': TokenType.ESAC,
    'function': TokenType.FUNCTION,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'return': TokenType.RETURN,
}

# Reverse lookup for matching by TokenType
KEYWORD_BY_TYPE = {value: key for key, value in KEYWORD_TYPE_MAP.items()}


def keyword_from_type(token_type: TokenType) -> Optional[str]:
    """Return the canonical keyword string for a token type."""
    return KEYWORD_BY_TYPE.get(token_type)


def matches_keyword_type(token, expected_type: TokenType) -> bool:
    """Check whether the token represents the given keyword token type."""
    if token.type == expected_type:
        return True

    keyword = KEYWORD_BY_TYPE.get(expected_type)
    if keyword is None:
        return False
    if token.type != TokenType.WORD:
        return False

    token_value = (token.value or '').lower()
    if token.metadata is not None:
        if token.metadata.semantic_type == SemanticType.KEYWORD and token_value == keyword:
            return True
        if token.metadata.semantic_type is None and token_value == keyword:
            token.metadata.semantic_type = SemanticType.KEYWORD
            return True
    else:
        if token_value == keyword:
            return True

    return False


def matches_keyword(token, keyword: str) -> bool:
    """Check whether the token represents the given keyword string."""
    keyword = keyword.lower()
    expected_type = KEYWORD_TYPE_MAP.get(keyword)
    if expected_type is None:
        return False
    return matches_keyword_type(token, expected_type)
