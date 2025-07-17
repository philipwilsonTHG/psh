"""Enhanced token classes with rich metadata and context tracking."""

from dataclasses import dataclass, field
from typing import Set, Optional, List
from enum import Enum

from .token_types import Token, TokenType
from .lexer.token_parts import TokenPart


class TokenContext(Enum):
    """Context in which a token appears."""
    COMMAND_POSITION = "command_position"
    ARGUMENT_POSITION = "argument_position"
    TEST_EXPRESSION = "test_expression"
    ARITHMETIC_EXPRESSION = "arithmetic_expression"
    CASE_PATTERN = "case_pattern"
    REDIRECT_TARGET = "redirect_target"
    ASSIGNMENT_RHS = "assignment_rhs"
    FUNCTION_BODY = "function_body"
    CONDITIONAL_EXPRESSION = "conditional_expression"


class SemanticType(Enum):
    """Semantic classification of tokens."""
    KEYWORD = "keyword"
    BUILTIN = "builtin"
    ASSIGNMENT = "assignment"
    OPERATOR = "operator"
    LITERAL = "literal"
    EXPANSION = "expansion"
    PATTERN = "pattern"
    REDIRECT = "redirect"
    DELIMITER = "delimiter"
    IDENTIFIER = "identifier"


@dataclass
class LexerError:
    """Information about lexer-detected errors."""
    error_type: str
    message: str
    expected: Optional[str] = None
    suggestion: Optional[str] = None
    severity: str = "error"  # error, warning, info


@dataclass
class TokenMetadata:
    """Additional metadata for tokens."""
    contexts: Set[TokenContext] = field(default_factory=set)
    semantic_type: Optional[SemanticType] = None
    paired_with: Optional[int] = None  # Index of paired token
    expansion_depth: int = 0
    quote_depth: int = 0
    error_info: Optional[LexerError] = None
    
    def add_context(self, context: TokenContext):
        """Add a context to this token."""
        self.contexts.add(context)
    
    def has_context(self, context: TokenContext) -> bool:
        """Check if token has a specific context."""
        return context in self.contexts
    
    def is_in_test_context(self) -> bool:
        """Check if token is in test expression context."""
        return self.has_context(TokenContext.TEST_EXPRESSION)
    
    def is_command_position(self) -> bool:
        """Check if token is in command position."""
        return self.has_context(TokenContext.COMMAND_POSITION)


# DEPRECATED: EnhancedToken functionality has been merged into Token class
# This alias is provided for backward compatibility only
import warnings

@dataclass 
class EnhancedToken(Token):
    """DEPRECATED: Use Token class instead. Enhanced functionality is now built into Token."""
    
    def __post_init__(self):
        """Initialize with deprecation warning."""
        warnings.warn(
            "EnhancedToken is deprecated. Use Token class instead - enhanced functionality is now built-in.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__post_init__()
    
    @classmethod
    def from_token(
        cls, 
        token: Token, 
        metadata: Optional[TokenMetadata] = None,
        parts: Optional[List[TokenPart]] = None
    ) -> 'EnhancedToken':
        """DEPRECATED: Create EnhancedToken from regular Token. Use Token class directly."""
        warnings.warn(
            "EnhancedToken.from_token() is deprecated. Use Token class directly.",
            DeprecationWarning,
            stacklevel=2
        )
        return cls(
            type=token.type,
            value=token.value,
            position=token.position,
            end_position=token.end_position,
            quote_type=token.quote_type,
            line=token.line,
            column=token.column,
            metadata=metadata or TokenMetadata(),
            parts=parts or []
        )
    
    @property
    def is_error(self) -> bool:
        """Check if this token represents an error."""
        return self.metadata.error_info is not None
    
    @property
    def is_assignment(self) -> bool:
        """Check if this token is an assignment."""
        return (self.metadata.semantic_type == SemanticType.ASSIGNMENT or
                self.type in {TokenType.ASSIGNMENT_WORD, TokenType.ARRAY_ASSIGNMENT_WORD})
    
    @property
    def is_keyword(self) -> bool:
        """Check if this token is a keyword."""
        return (self.metadata.semantic_type == SemanticType.KEYWORD or
                self.type in {TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI,
                             TokenType.WHILE, TokenType.DO, TokenType.DONE, TokenType.FOR,
                             TokenType.IN, TokenType.CASE, TokenType.ESAC, TokenType.SELECT,
                             TokenType.FUNCTION, TokenType.BREAK, TokenType.CONTINUE})
    
    @property
    def is_operator(self) -> bool:
        """Check if this token is an operator."""
        return (self.metadata.semantic_type == SemanticType.OPERATOR or
                self.type in {TokenType.PIPE, TokenType.AND_AND, TokenType.OR_OR,
                             TokenType.SEMICOLON, TokenType.AMPERSAND, TokenType.EQUAL,
                             TokenType.NOT_EQUAL, TokenType.REGEX_MATCH})
    
    @property
    def is_redirect(self) -> bool:
        """Check if this token is a redirection."""
        return (self.metadata.semantic_type == SemanticType.REDIRECT or
                self.type in {TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT,
                             TokenType.REDIRECT_APPEND, TokenType.REDIRECT_ERR,
                             TokenType.REDIRECT_ERR_APPEND, TokenType.REDIRECT_DUP,
                             TokenType.HEREDOC, TokenType.HEREDOC_STRIP, TokenType.HERE_STRING})
    
    def add_context(self, context: TokenContext):
        """Add a context to this token."""
        self.metadata.add_context(context)
    
    def has_context(self, context: TokenContext) -> bool:
        """Check if token has a specific context."""
        return self.metadata.has_context(context)
    
    def set_semantic_type(self, semantic_type: SemanticType):
        """Set the semantic type of this token."""
        self.metadata.semantic_type = semantic_type
    
    def set_error(self, error_info: LexerError):
        """Mark this token as containing an error."""
        self.metadata.error_info = error_info
    
    def set_paired_with(self, token_index: int):
        """Mark this token as paired with another token."""
        self.metadata.paired_with = token_index


class LexerErrorType:
    """Standard lexer error types."""
    UNCLOSED_QUOTE = "unclosed_quote"
    UNCLOSED_EXPANSION = "unclosed_expansion"
    INVALID_ASSIGNMENT = "invalid_assignment"
    UNMATCHED_BRACKET = "unmatched_bracket"
    INVALID_REDIRECT = "invalid_redirect"
    MALFORMED_PATTERN = "malformed_pattern"
    UNRECOGNIZED_CHARACTER = "unrecognized_character"
    TOO_MANY_ERRORS = "too_many_errors"
    SUSPICIOUS_REDIRECT = "suspicious_redirect"


def create_error_token(
    position: int,
    value: str,
    error_type: str,
    message: str,
    end_position: Optional[int] = None,
    **kwargs
) -> Token:
    """Create a token representing a lexer error."""
    error_info = LexerError(
        error_type=error_type,
        message=message,
        **kwargs
    )
    
    token = Token(
        type=TokenType.WORD,  # Fallback type
        value=value,
        position=position,
        end_position=end_position or (position + len(value))
    )
    token.set_error(error_info)
    
    return token


def create_assignment_token(
    position: int,
    value: str,
    assignment_type: TokenType,
    end_position: Optional[int] = None
) -> Token:
    """Create a token representing an assignment."""
    token = Token(
        type=assignment_type,
        value=value,
        position=position,
        end_position=end_position or (position + len(value))
    )
    token.set_semantic_type(SemanticType.ASSIGNMENT)
    token.add_context(TokenContext.COMMAND_POSITION)
    
    return token