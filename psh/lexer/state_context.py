"""Unified state representation for the lexer."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .position import LexerState


@dataclass
class LexerContext:
    """
    Unified state representation for the lexer.
    
    This replaces the fragmented state tracking that was previously
    scattered across multiple boolean flags and counters.
    """
    state: LexerState = LexerState.NORMAL
    bracket_depth: int = 0  # Replaces in_double_brackets
    paren_depth: int = 0
    command_position: bool = True
    after_regex_match: bool = False
    quote_stack: List[str] = field(default_factory=list)
    heredoc_delimiters: List[str] = field(default_factory=list)
    
    # Additional context for nested structures
    brace_depth: int = 0  # For ${...} tracking
    arithmetic_depth: int = 0  # For $((...)) tracking
    
    # Token building context
    token_start_offset: int = 0
    current_token_parts: List[Any] = field(default_factory=list)
    
    def copy(self) -> 'LexerContext':
        """Create a deep copy of the context."""
        return LexerContext(
            state=self.state,
            bracket_depth=self.bracket_depth,
            paren_depth=self.paren_depth,
            command_position=self.command_position,
            after_regex_match=self.after_regex_match,
            quote_stack=self.quote_stack.copy(),
            heredoc_delimiters=self.heredoc_delimiters.copy(),
            brace_depth=self.brace_depth,
            arithmetic_depth=self.arithmetic_depth,
            token_start_offset=self.token_start_offset,
            current_token_parts=self.current_token_parts.copy()
        )
    
    def in_double_brackets(self) -> bool:
        """Check if we're inside [[ ]] construct."""
        return self.bracket_depth > 0
    
    def in_quotes(self) -> bool:
        """Check if we're inside any quote context."""
        return len(self.quote_stack) > 0
    
    def current_quote_type(self) -> Optional[str]:
        """Get the current quote type if in quotes."""
        return self.quote_stack[-1] if self.quote_stack else None
    
    def push_quote(self, quote_char: str) -> None:
        """Enter a quote context."""
        self.quote_stack.append(quote_char)
    
    def pop_quote(self) -> Optional[str]:
        """Exit quote context."""
        return self.quote_stack.pop() if self.quote_stack else None
    
    def enter_double_brackets(self) -> None:
        """Enter [[ ]] context."""
        self.bracket_depth += 1
    
    def exit_double_brackets(self) -> None:
        """Exit [[ ]] context."""
        if self.bracket_depth > 0:
            self.bracket_depth -= 1
    
    def enter_parentheses(self) -> None:
        """Enter parentheses context."""
        self.paren_depth += 1
    
    def exit_parentheses(self) -> None:
        """Exit parentheses context."""
        if self.paren_depth > 0:
            self.paren_depth -= 1
    
    def enter_brace_expansion(self) -> None:
        """Enter ${...} context."""
        self.brace_depth += 1
    
    def exit_brace_expansion(self) -> None:
        """Exit ${...} context."""
        if self.brace_depth > 0:
            self.brace_depth -= 1
    
    def enter_arithmetic(self) -> None:
        """Enter $((...)) context."""
        self.arithmetic_depth += 1
    
    def exit_arithmetic(self) -> None:
        """Exit $((...)) context."""
        if self.arithmetic_depth > 0:
            self.arithmetic_depth -= 1
    
    def reset_command_position(self) -> None:
        """Reset to non-command position."""
        self.command_position = False
    
    def set_command_position(self) -> None:
        """Set to command position."""
        self.command_position = True
    
    def clear_regex_match_flag(self) -> None:
        """Clear the after regex match flag."""
        self.after_regex_match = False
    
    def set_regex_match_flag(self) -> None:
        """Set the after regex match flag."""
        self.after_regex_match = True
    
    def is_in_nested_structure(self) -> bool:
        """Check if we're inside any nested structure."""
        return (self.bracket_depth > 0 or 
                self.paren_depth > 0 or 
                self.brace_depth > 0 or 
                self.arithmetic_depth > 0 or
                len(self.quote_stack) > 0)
    
    def get_nesting_summary(self) -> Dict[str, int]:
        """Get a summary of current nesting levels."""
        return {
            'brackets': self.bracket_depth,
            'parentheses': self.paren_depth,
            'braces': self.brace_depth,
            'arithmetic': self.arithmetic_depth,
            'quotes': len(self.quote_stack)
        }
    
    def __str__(self) -> str:
        """Human-readable representation of the context."""
        parts = [f"state={self.state.name}"]
        
        if self.bracket_depth > 0:
            parts.append(f"brackets={self.bracket_depth}")
        if self.paren_depth > 0:
            parts.append(f"parens={self.paren_depth}")
        if self.brace_depth > 0:
            parts.append(f"braces={self.brace_depth}")
        if self.arithmetic_depth > 0:
            parts.append(f"arithmetic={self.arithmetic_depth}")
        if self.quote_stack:
            parts.append(f"quotes={self.quote_stack}")
        if self.command_position:
            parts.append("cmd_pos")
        if self.after_regex_match:
            parts.append("after_regex")
        
        return f"LexerContext({', '.join(parts)})"