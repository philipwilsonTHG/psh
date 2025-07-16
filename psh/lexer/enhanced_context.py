"""Enhanced lexer context with parser hints and context tracking."""

from dataclasses import dataclass, field
from typing import List, Tuple, Set
from enum import Enum

from .state_context import LexerContext
from .position import LexerState
from ..token_enhanced import TokenContext


@dataclass
class EnhancedLexerContext(LexerContext):
    """Lexer context with enhanced tracking for parser hints."""
    
    # Position tracking
    command_position: bool = True
    after_assignment: bool = False
    expect_pattern: bool = False
    in_assignment_rhs: bool = False
    
    # Nesting contexts
    test_expr_depth: int = 0
    arithmetic_depth: int = 0
    case_pattern_depth: int = 0
    function_depth: int = 0
    conditional_depth: int = 0
    
    # Pairing tracking
    bracket_stack: List[Tuple[str, int]] = field(default_factory=list)
    
    # Context history for debugging
    context_history: List[str] = field(default_factory=list)
    
    def enter_test_expression(self):
        """Enter test expression context ([[...]])."""
        self.test_expr_depth += 1
        self._log_context_change("enter_test_expression")
    
    def exit_test_expression(self):
        """Exit test expression context."""
        self.test_expr_depth = max(0, self.test_expr_depth - 1)
        self._log_context_change("exit_test_expression")
    
    def enter_arithmetic_expression(self):
        """Enter arithmetic expression context (((...)))."""
        self.arithmetic_depth += 1
        self._log_context_change("enter_arithmetic_expression")
    
    def exit_arithmetic_expression(self):
        """Exit arithmetic expression context."""
        self.arithmetic_depth = max(0, self.arithmetic_depth - 1)
        self._log_context_change("exit_arithmetic_expression")
    
    def enter_case_pattern(self):
        """Enter case pattern context."""
        self.case_pattern_depth += 1
        self.expect_pattern = True
        self._log_context_change("enter_case_pattern")
    
    def exit_case_pattern(self):
        """Exit case pattern context."""
        self.case_pattern_depth = max(0, self.case_pattern_depth - 1)
        self.expect_pattern = False
        self._log_context_change("exit_case_pattern")
    
    def enter_function_body(self):
        """Enter function body context."""
        self.function_depth += 1
        self._log_context_change("enter_function_body")
    
    def exit_function_body(self):
        """Exit function body context."""
        self.function_depth = max(0, self.function_depth - 1)
        self._log_context_change("exit_function_body")
    
    def enter_conditional(self):
        """Enter conditional context (if, while, etc.)."""
        self.conditional_depth += 1
        self._log_context_change("enter_conditional")
    
    def exit_conditional(self):
        """Exit conditional context."""
        self.conditional_depth = max(0, self.conditional_depth - 1)
        self._log_context_change("exit_conditional")
    
    def set_command_position(self, is_command: bool):
        """Set whether we're in command position."""
        if self.command_position != is_command:
            self.command_position = is_command
            self._log_context_change(f"command_position={is_command}")
    
    def set_assignment_context(self, in_assignment: bool, is_rhs: bool = False):
        """Set assignment context."""
        self.after_assignment = in_assignment
        self.in_assignment_rhs = is_rhs
        if in_assignment:
            self._log_context_change(f"assignment_context(rhs={is_rhs})")
    
    def push_bracket(self, bracket_type: str, position: int):
        """Push a bracket onto the stack."""
        self.bracket_stack.append((bracket_type, position))
        self._log_context_change(f"push_bracket({bracket_type})")
    
    def pop_bracket(self, expected_type: str) -> Tuple[str, int, bool]:
        """Pop a bracket from the stack. Returns (type, position, matched)."""
        if not self.bracket_stack:
            return (expected_type, -1, False)
        
        actual_type, position = self.bracket_stack.pop()
        matched = actual_type == expected_type
        self._log_context_change(f"pop_bracket({expected_type}, matched={matched})")
        
        return (actual_type, position, matched)
    
    def get_current_contexts(self) -> Set[TokenContext]:
        """Get current token contexts."""
        contexts = set()
        
        # Position contexts
        if self.command_position:
            contexts.add(TokenContext.COMMAND_POSITION)
        else:
            contexts.add(TokenContext.ARGUMENT_POSITION)
        
        # Assignment contexts
        if self.in_assignment_rhs:
            contexts.add(TokenContext.ASSIGNMENT_RHS)
        
        # Expression contexts
        if self.test_expr_depth > 0:
            contexts.add(TokenContext.TEST_EXPRESSION)
        
        if self.arithmetic_depth > 0:
            contexts.add(TokenContext.ARITHMETIC_EXPRESSION)
        
        if self.case_pattern_depth > 0:
            contexts.add(TokenContext.CASE_PATTERN)
        
        if self.function_depth > 0:
            contexts.add(TokenContext.FUNCTION_BODY)
        
        if self.conditional_depth > 0:
            contexts.add(TokenContext.CONDITIONAL_EXPRESSION)
        
        return contexts
    
    def is_in_expression_context(self) -> bool:
        """Check if currently in any expression context."""
        return (self.test_expr_depth > 0 or 
                self.arithmetic_depth > 0 or
                self.case_pattern_depth > 0)
    
    def get_nesting_depth(self) -> int:
        """Get total nesting depth."""
        return (self.test_expr_depth + 
                self.arithmetic_depth + 
                self.case_pattern_depth + 
                self.function_depth + 
                self.conditional_depth)
    
    def should_expect_assignment(self) -> bool:
        """Check if we should expect assignment patterns."""
        return (self.command_position and 
                not self.is_in_expression_context() and 
                not self.after_assignment)
    
    def should_expect_pattern(self) -> bool:
        """Check if we should expect glob patterns."""
        return (self.expect_pattern or 
                self.case_pattern_depth > 0 or
                (not self.command_position and not self.is_in_expression_context()))
    
    def get_context_summary(self) -> str:
        """Get a summary of current context for debugging."""
        parts = []
        
        if self.command_position:
            parts.append("cmd")
        else:
            parts.append("arg")
        
        if self.test_expr_depth > 0:
            parts.append(f"test({self.test_expr_depth})")
        
        if self.arithmetic_depth > 0:
            parts.append(f"arith({self.arithmetic_depth})")
        
        if self.case_pattern_depth > 0:
            parts.append(f"case({self.case_pattern_depth})")
        
        if self.function_depth > 0:
            parts.append(f"func({self.function_depth})")
        
        if self.conditional_depth > 0:
            parts.append(f"cond({self.conditional_depth})")
        
        if self.bracket_stack:
            bracket_types = [bt for bt, _ in self.bracket_stack]
            parts.append(f"brackets({','.join(bracket_types)})")
        
        if self.after_assignment:
            parts.append("post-assign")
        
        if self.in_assignment_rhs:
            parts.append("assign-rhs")
        
        if self.expect_pattern:
            parts.append("expect-pattern")
        
        return "[" + ",".join(parts) + "]"
    
    def _log_context_change(self, change: str):
        """Log a context change for debugging."""
        if len(self.context_history) > 100:  # Limit history size
            self.context_history = self.context_history[-50:]
        
        self.context_history.append(f"{change} -> {self.get_context_summary()}")
    
    def get_context_history(self) -> List[str]:
        """Get the context change history."""
        return self.context_history.copy()
    
    def reset_context(self):
        """Reset context to initial state."""
        self.command_position = True
        self.after_assignment = False
        self.expect_pattern = False
        self.in_assignment_rhs = False
        self.test_expr_depth = 0
        self.arithmetic_depth = 0
        self.case_pattern_depth = 0
        self.function_depth = 0
        self.conditional_depth = 0
        self.bracket_stack.clear()
        self.context_history.clear()
        self._log_context_change("reset")


class ContextHint(Enum):
    """Hints about what kind of token to expect next."""
    ASSIGNMENT = "assignment"
    PATTERN = "pattern"
    COMMAND = "command"
    ARGUMENT = "argument"
    OPERATOR = "operator"
    KEYWORD = "keyword"
    REDIRECT_TARGET = "redirect_target"
    EXPRESSION = "expression"


def get_context_hint(context: EnhancedLexerContext) -> ContextHint:
    """Get a hint about what kind of token to expect next."""
    # Assignment patterns in command position
    if context.should_expect_assignment():
        return ContextHint.ASSIGNMENT
    
    # Patterns in case statements or argument position
    if context.should_expect_pattern():
        return ContextHint.PATTERN
    
    # Commands in command position
    if context.command_position and not context.is_in_expression_context():
        return ContextHint.COMMAND
    
    # Expressions in test/arithmetic contexts
    if context.is_in_expression_context():
        return ContextHint.EXPRESSION
    
    # Default to argument
    return ContextHint.ARGUMENT