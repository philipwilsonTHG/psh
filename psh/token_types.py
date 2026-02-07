#!/usr/bin/env python3
"""Token type definitions for PSH lexer and parser."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .lexer.token_parts import TokenPart
    from .token_enhanced import TokenMetadata


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
    PARAM_EXPANSION = auto()       # ${var:-default} style expansions
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
    DOUBLE_RPAREN = auto()  # ))

    # Keywords
    FUNCTION = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    FI = auto()
    ELIF = auto()
    WHILE = auto()
    UNTIL = auto()
    DO = auto()
    DONE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    RETURN = auto()
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
    EQUAL = auto()             # ==
    NOT_EQUAL = auto()         # !=

    # Assignment operators
    ASSIGN = auto()            # =
    PLUS_ASSIGN = auto()       # +=
    MINUS_ASSIGN = auto()      # -=
    MULT_ASSIGN = auto()       # *=
    DIV_ASSIGN = auto()        # /=
    MOD_ASSIGN = auto()        # %=
    AND_ASSIGN = auto()        # &=
    OR_ASSIGN = auto()         # |=
    XOR_ASSIGN = auto()        # ^=
    LSHIFT_ASSIGN = auto()     # <<=
    RSHIFT_ASSIGN = auto()     # >>=

    # Pattern matching
    GLOB_STAR = auto()         # * in patterns
    GLOB_QUESTION = auto()     # ? in patterns
    GLOB_BRACKET = auto()      # [...] in patterns

    # Context-specific operators
    LESS_THAN_TEST = auto()    # < in test context
    GREATER_THAN_TEST = auto() # > in test context
    LESS_EQUAL_TEST = auto()   # <= in test context
    GREATER_EQUAL_TEST = auto() # >= in test context

    # Special constructs
    HERE_DELIMITER = auto()    # Heredoc delimiter
    ASSIGNMENT_WORD = auto()   # VAR=value pattern
    ARRAY_ASSIGNMENT_WORD = auto() # arr[index]=value pattern

    # Composite tokens
    COMPOSITE = auto()         # Merged adjacent tokens


@dataclass
class Token:
    """Unified token class with metadata and context information (formerly EnhancedToken)."""
    type: TokenType
    value: str
    position: int
    end_position: int = 0  # Position after the last character of the token
    quote_type: Optional[str] = None  # Track the quote character used (' or " or None)
    line: Optional[int] = None  # Line number (1-based)
    column: Optional[int] = None  # Column number (1-based)
    adjacent_to_previous: bool = False  # True if no whitespace between this and previous token
    metadata: Optional['TokenMetadata'] = field(default=None)  # Rich metadata (imported from token_enhanced)
    parts: Optional[List['TokenPart']] = field(default=None)  # Token parts (imported from lexer.token_parts)

    def __post_init__(self):
        """Initialize metadata and parts if not provided."""
        if self.metadata is None:
            # Import here to avoid circular imports
            from .token_enhanced import TokenMetadata
            self.metadata = TokenMetadata()
        if self.parts is None:
            self.parts = []

    @classmethod
    def from_basic_token(
        cls,
        type: TokenType,
        value: str,
        position: int,
        end_position: int = 0,
        quote_type: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        adjacent_to_previous: bool = False
    ) -> 'Token':
        """Create unified Token from basic token information."""
        return cls(
            type=type,
            value=value,
            position=position,
            end_position=end_position,
            quote_type=quote_type,
            adjacent_to_previous=adjacent_to_previous,
            line=line,
            column=column
        )

    @classmethod
    def from_token(
        cls,
        token: 'Token',
        metadata: Optional['TokenMetadata'] = None,
        parts: Optional[List['TokenPart']] = None
    ) -> 'Token':
        """Create Token from another Token (for compatibility)."""
        if isinstance(token, cls):
            return token  # Already a unified token

        # Create new token with metadata
        new_token = cls(
            type=token.type,
            value=token.value,
            position=token.position,
            end_position=token.end_position,
            quote_type=token.quote_type,
            adjacent_to_previous=getattr(token, 'adjacent_to_previous', False),
            line=token.line,
            column=token.column
        )

        if metadata:
            new_token.metadata = metadata
        if parts:
            new_token.parts = parts

        return new_token

    def add_context(self, context):
        """Add a context to this token's metadata."""
        if self.metadata:
            self.metadata.add_context(context)

    def has_context(self, context) -> bool:
        """Check if token has a specific context."""
        return self.metadata.has_context(context) if self.metadata else False

    def is_in_test_context(self) -> bool:
        """Check if token is in test expression context."""
        return self.metadata.is_in_test_context() if self.metadata else False

    def is_command_position(self) -> bool:
        """Check if token is in command position."""
        return self.metadata.is_command_position() if self.metadata else False

    @property
    def normalized_value(self) -> str:
        """Return a canonical representation suitable for comparisons."""
        value = self.value or ""

        # Prefer canonical keyword spelling when available
        try:
            from .lexer.keyword_defs import keyword_from_type  # Late import avoids cycles
        except ImportError:
            keyword_from_type = None  # type: ignore
        if keyword_from_type is not None:
            canonical = keyword_from_type(self.type)
            if canonical:
                return canonical

        # If metadata marked this as a keyword, normalize to lowercase
        if self.metadata is not None:
            try:
                from .token_enhanced import SemanticType  # Late import avoids cycles
            except ImportError:
                SemanticType = None  # type: ignore
            if SemanticType is not None and self.metadata.semantic_type == SemanticType.KEYWORD:
                return value.lower()

        return value
