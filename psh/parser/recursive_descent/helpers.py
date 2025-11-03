"""Helper classes for the parser module."""

from typing import Set, Optional, List, Dict
from dataclasses import dataclass, field
from ...token_types import Token, TokenType


class TokenGroups:
    """Groups of related tokens for cleaner matching."""
    
    # Word-like tokens that can appear as command arguments
    WORD_LIKE: Set[TokenType] = frozenset({
        TokenType.WORD, TokenType.STRING, TokenType.VARIABLE,
        TokenType.COMMAND_SUB, TokenType.COMMAND_SUB_BACKTICK,
        TokenType.ARITH_EXPANSION, TokenType.PARAM_EXPANSION,
        TokenType.PROCESS_SUB_IN, TokenType.PROCESS_SUB_OUT,
        TokenType.LBRACKET, TokenType.RBRACKET,
        TokenType.LBRACE, TokenType.RBRACE, TokenType.COMPOSITE
    })
    
    # Redirect operators
    REDIRECTS: Set[TokenType] = frozenset({
        TokenType.REDIRECT_IN, TokenType.REDIRECT_OUT, 
        TokenType.REDIRECT_APPEND, TokenType.HEREDOC,
        TokenType.HEREDOC_STRIP, TokenType.HERE_STRING,
        TokenType.REDIRECT_ERR, TokenType.REDIRECT_ERR_APPEND, 
        TokenType.REDIRECT_DUP
    })
    
    # Control structure keywords
    CONTROL_KEYWORDS: Set[TokenType] = frozenset({
        TokenType.IF, TokenType.WHILE, TokenType.UNTIL, TokenType.FOR, 
        TokenType.CASE, TokenType.SELECT, TokenType.BREAK, TokenType.CONTINUE,
        TokenType.DOUBLE_LBRACKET, TokenType.DOUBLE_LPAREN
    })
    
    # Statement separators
    STATEMENT_SEPARATORS: Set[TokenType] = frozenset({
        TokenType.SEMICOLON, TokenType.NEWLINE
    })
    
    # Case statement terminators
    CASE_TERMINATORS: Set[TokenType] = frozenset({
        TokenType.DOUBLE_SEMICOLON, TokenType.SEMICOLON_AMP, 
        TokenType.AMP_SEMICOLON
    })
    
    # Command list end tokens
    COMMAND_LIST_END: Set[TokenType] = frozenset({
        TokenType.EOF, TokenType.FI, TokenType.DONE, 
        TokenType.ELSE, TokenType.ELIF, TokenType.ESAC, 
        TokenType.RBRACE
    })
    
    # Keywords that can be valid case patterns
    CASE_PATTERN_KEYWORDS: Set[TokenType] = frozenset({
        TokenType.IF, TokenType.THEN, TokenType.ELSE, TokenType.FI, TokenType.ELIF,
        TokenType.WHILE, TokenType.UNTIL, TokenType.DO, TokenType.DONE, TokenType.FOR, TokenType.IN,
        TokenType.BREAK, TokenType.CONTINUE, TokenType.CASE, TokenType.ESAC,
        TokenType.SELECT, TokenType.FUNCTION
    })


@dataclass
class ParseContext:
    """Context for parsing state management."""
    
    # Stack of parsing contexts (e.g., "in_regex_rhs", "in_arithmetic")
    context_stack: List[str] = field(default_factory=list)
    
    # Current position in token stream
    current_position: int = 0
    
    # Error recovery state
    in_error_recovery: bool = False
    error_sync_tokens: Set[TokenType] = field(default_factory=set)
    
    # Parser state flags
    in_test_expr: bool = False
    in_arithmetic: bool = False
    in_case_pattern: bool = False
    in_function_body: bool = False
    in_here_document: bool = False
    in_command_substitution: bool = False
    allow_keywords: bool = True
    allow_empty_commands: bool = False
    
    # Stack of saved states for nested context managers
    _saved_states: List[dict] = field(default_factory=list, init=False, repr=False)
    
    def push_context(self, context: str) -> None:
        """Push a new context onto the stack."""
        self.context_stack.append(context)
    
    def pop_context(self) -> Optional[str]:
        """Pop context from the stack."""
        return self.context_stack.pop() if self.context_stack else None
    
    def in_context(self, context: str) -> bool:
        """Check if we're in a specific context."""
        return context in self.context_stack
    
    @property
    def current_context(self) -> Optional[str]:
        """Get the current (top) context."""
        return self.context_stack[-1] if self.context_stack else None
    
    def __enter__(self):
        """Support context manager for state changes."""
        # Save current state
        saved_state = {
            'in_test_expr': self.in_test_expr,
            'in_arithmetic': self.in_arithmetic,
            'in_case_pattern': self.in_case_pattern,
            'in_function_body': self.in_function_body,
            'in_here_document': self.in_here_document,
            'in_command_substitution': self.in_command_substitution,
            'allow_keywords': self.allow_keywords,
            'allow_empty_commands': self.allow_empty_commands,
            'context_stack': self.context_stack.copy(),
            'in_error_recovery': self.in_error_recovery,
            'error_sync_tokens': self.error_sync_tokens.copy() if self.error_sync_tokens else set()
        }
        self._saved_states.append(saved_state)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous state."""
        if self._saved_states:
            saved_state = self._saved_states.pop()
            for key, value in saved_state.items():
                setattr(self, key, value)
        return False  # Don't suppress exceptions


@dataclass 
class ErrorContext:
    """Enhanced error context for better error messages."""
    
    token: Token
    expected: List[str] = field(default_factory=list)
    message: str = ""
    position: int = 0
    line: Optional[int] = None
    column: Optional[int] = None
    source_line: Optional[str] = None
    
    # Enhanced error information
    suggestions: List[str] = field(default_factory=list)
    error_code: str = ""
    severity: str = "error"  # "info", "warning", "error", "fatal"
    related_errors: List['ErrorContext'] = field(default_factory=list)
    context_tokens: List[str] = field(default_factory=list)  # Surrounding tokens for context
    
    def format_error(self) -> str:
        """Format a detailed error message."""
        # Main error message
        parts = []
        
        # Add error code if available
        if self.error_code:
            parts.append(f"[{self.error_code}] ")
        
        parts.append(f"Parse error at position {self.position}")
        
        if self.line is not None and self.column is not None:
            parts.append(f" (line {self.line}, column {self.column})")
        
        parts.append(": ")
        
        # Error description
        if self.expected:
            if len(self.expected) == 1:
                parts.append(f"Expected {self.expected[0]}")
            else:
                expected_str = ", ".join(self.expected[:-1]) + f" or {self.expected[-1]}"
                parts.append(f"Expected {expected_str}")
            parts.append(f", got {self._token_description(self.token)}")
        elif self.message:
            parts.append(self.message)
        else:
            parts.append(f"Unexpected {self._token_description(self.token)}")
        
        error_msg = "".join(parts)
        
        # Add source line context if available
        if self.source_line and self.column is not None:
            error_msg += f"\n\n{self.source_line}\n{' ' * (self.column - 1)}^"
        
        # Add suggestions if available
        if self.suggestions:
            error_msg += "\n\nSuggestions:"
            for suggestion in self.suggestions:
                error_msg += f"\n  • {suggestion}"
        
        # Add context tokens if available
        if self.context_tokens:
            error_msg += f"\n\nContext: {' '.join(self.context_tokens[-3:])} -> HERE <- {' '.join(self.context_tokens[:3])}"
        
        return error_msg
    
    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the error context."""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def add_context_tokens(self, tokens: List[str]) -> None:
        """Add context tokens around the error position."""
        self.context_tokens = tokens
    
    def set_error_template(self, template) -> None:
        """Set error information from an ErrorTemplate."""
        # Import here to avoid circular imports
        from ..errors import ErrorTemplate
        if isinstance(template, ErrorTemplate):
            self.error_code = template.code
            if not self.message:
                self.message = template.message
            self.severity = template.severity.value
            if template.suggestion:
                self.add_suggestion(template.suggestion)
    
    def _token_description(self, token: Token) -> str:
        """Get human-readable token description."""
        if token.type == TokenType.EOF:
            return "end of input"
        elif token.type == TokenType.NEWLINE:
            return "newline"
        elif token.value:
            return f"'{token.value}'"
        else:
            return token.type.name.lower()


class ParseError(Exception):
    """Enhanced parse error with context."""
    
    def __init__(self, error_context: ErrorContext):
        self.error_context = error_context
        self.message = error_context.message or error_context.format_error()
        super().__init__(error_context.format_error())
