"""Centralized parser context for PSH.

This module provides the ParserContext class that consolidates all parser state
into a single, manageable object, improving maintainability and performance tracking.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...token_types import Token, TokenType
from ..config import ParserConfig
from .helpers import ParseError

logger = logging.getLogger(__name__)


@dataclass
class HeredocInfo:
    """Information about a heredoc being processed."""
    delimiter: str
    strip_tabs: bool = False
    quoted: bool = False
    start_line: int = 0
    content_lines: List[str] = field(default_factory=list)
    closed: bool = False


class ParserProfiler:
    """Performance profiler for parser operations."""

    def __init__(self, config: ParserConfig):
        self.config = config
        self.rule_times: Dict[str, float] = {}
        self.rule_counts: Dict[str, int] = {}
        self.rule_stack: List[tuple] = []  # (rule_name, start_time)
        self.enabled = config.profile_parsing

        # Additional performance metrics
        self.token_consumption_count = 0
        self.backtrack_count = 0
        self.error_recovery_count = 0
        self.max_recursion_depth = 0
        self.parse_start_time = None
        self.parse_end_time = None

    def enter_rule(self, rule_name: str):
        """Enter a parse rule."""
        if self.enabled:
            import time
            self.rule_stack.append((rule_name, time.perf_counter()))
            self.rule_counts[rule_name] = self.rule_counts.get(rule_name, 0) + 1

            # Track recursion depth
            current_depth = len(self.rule_stack)
            self.max_recursion_depth = max(self.max_recursion_depth, current_depth)

    def exit_rule(self, rule_name: str):
        """Exit a parse rule."""
        if self.enabled and self.rule_stack:
            import time
            stack_rule, start_time = self.rule_stack.pop()
            if stack_rule == rule_name:
                duration = time.perf_counter() - start_time
                self.rule_times[rule_name] = self.rule_times.get(rule_name, 0.0) + duration

    def start_parsing(self):
        """Mark the start of parsing."""
        if self.enabled:
            import time
            self.parse_start_time = time.perf_counter()

    def end_parsing(self):
        """Mark the end of parsing."""
        if self.enabled:
            import time
            self.parse_end_time = time.perf_counter()

    def record_token_consumption(self):
        """Record that a token was consumed."""
        if self.enabled:
            self.token_consumption_count += 1

    def record_backtrack(self):
        """Record that backtracking occurred."""
        if self.enabled:
            self.backtrack_count += 1

    def record_error_recovery(self):
        """Record that error recovery was performed."""
        if self.enabled:
            self.error_recovery_count += 1

    def get_total_parse_time(self) -> float:
        """Get total parsing time in seconds."""
        if self.parse_start_time and self.parse_end_time:
            return self.parse_end_time - self.parse_start_time
        return 0.0

    def report(self) -> str:
        """Generate profiling report."""
        if not self.enabled:
            return "Profiling disabled"

        lines = ["Parser Performance Report:", "=" * 50]

        # Overall statistics
        total_time = self.get_total_parse_time()
        if total_time > 0:
            lines.extend([
                f"Total Parse Time: {total_time*1000:.2f}ms",
                f"Tokens Consumed: {self.token_consumption_count}",
                f"Max Recursion Depth: {self.max_recursion_depth}",
                f"Backtrack Operations: {self.backtrack_count}",
                f"Error Recoveries: {self.error_recovery_count}",
                ""
            ])

        # Rule performance breakdown
        if self.rule_times:
            lines.append("Rule Performance Breakdown:")
            lines.append("-" * 50)

            # Sort by total time
            sorted_rules = sorted(self.rule_times.items(), key=lambda x: x[1], reverse=True)

            lines.append(f"{'Rule':<30} {'Count':<8} {'Total(ms)':<10} {'Avg(ms)':<10}")
            lines.append("-" * 68)

            for rule_name, total_time in sorted_rules:
                count = self.rule_counts.get(rule_name, 0)
                avg_time = total_time / count if count > 0 else 0
                lines.append(f"{rule_name:<30} {count:<8} {total_time*1000:<10.2f} {avg_time*1000:<10.2f}")
        else:
            lines.append("No rule timing data collected")

        return "\n".join(lines)


@dataclass
class ParserContext:
    """Centralized parser state management.
    
    This class consolidates all parser state into a single object, providing
    cleaner interfaces for sub-parsers and better performance tracking.
    """

    # Core parsing state
    tokens: List[Token]
    current: int = 0
    config: ParserConfig = field(default_factory=ParserConfig)

    # Error handling
    errors: List[ParseError] = field(default_factory=list)
    error_recovery_mode: bool = False
    fatal_error: Optional[ParseError] = None

    # Parsing context
    nesting_depth: int = 0
    scope_stack: List[str] = field(default_factory=list)
    parse_stack: List[str] = field(default_factory=list)

    # Special parsing state
    heredoc_trackers: Dict[str, HeredocInfo] = field(default_factory=dict)
    in_case_pattern: bool = False
    in_arithmetic: bool = False
    in_test_expr: bool = False
    in_function_body: bool = False
    in_command_substitution: bool = False
    in_process_substitution: bool = False

    # Control flow state
    loop_depth: int = 0
    function_depth: int = 0
    conditional_depth: int = 0

    # Source context
    source_text: Optional[str] = None
    source_lines: Optional[List[str]] = None

    # Performance tracking
    trace_enabled: bool = False
    profiler: Optional[ParserProfiler] = None

    def __post_init__(self):
        """Initialize derived state."""
        if self.source_text and not self.source_lines:
            self.source_lines = self.source_text.splitlines()

        if self.config.trace_parsing:
            self.trace_enabled = True

        if self.config.profile_parsing:
            self.profiler = ParserProfiler(self.config)

    # === Token Access Methods ===

    def peek(self, offset: int = 0) -> Token:
        """Look at current token + offset without consuming."""
        pos = self.current + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1] if self.tokens else Token(TokenType.EOF, "", 0)

    def advance(self) -> Token:
        """Consume and return current token."""
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1

        # Record token consumption for profiling
        if self.profiler:
            self.profiler.record_token_consumption()

        return token

    def at_end(self) -> bool:
        """Check if at end of tokens."""
        return self.peek().type == TokenType.EOF

    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        return self.peek().type in token_types

    def consume(self, token_type: TokenType, error_message: str = None) -> Token:
        """Consume token of expected type or raise error."""
        if self.match(token_type):
            return self.advance()

        current = self.peek()
        message = error_message or f"Expected {token_type}, got {current.type}"

        # Create error with context
        error_context = self._create_error_context(message, current)
        error = ParseError(error_context)

        if self.config.collect_errors:
            self.add_error(error)
            return current  # Return current token to continue parsing
        else:
            raise error

    def _create_error_context(self, message: str, token: Token):
        """Create error context with source information."""
        from .helpers import ErrorContext

        source_line = None
        if self.source_lines and token.line and 0 < token.line <= len(self.source_lines):
            source_line = self.source_lines[token.line - 1]

        error_context = ErrorContext(
            token=token,
            message=message,
            position=token.position,
            line=token.line,
            column=token.column,
            source_line=source_line
        )

        # Enhance error context with suggestions and context tokens
        self._enhance_error_context(error_context, token)

        return error_context

    def _enhance_error_context(self, error_context, token):
        """Enhance error context with smart suggestions and context tokens."""
        try:
            # Add context tokens (3 before and after current position)
            context_tokens = []

            # Preceding tokens
            for i in range(max(0, self.current - 3), self.current):
                if i < len(self.tokens):
                    context_tokens.append(self.tokens[i].value or str(self.tokens[i].type))

            # Following tokens
            for i in range(self.current + 1, min(len(self.tokens), self.current + 4)):
                context_tokens.append(self.tokens[i].value or str(self.tokens[i].type))

            error_context.context_tokens = context_tokens

            # Add contextual suggestions based on message
            if "Expected TokenType.THEN" in error_context.message:
                error_context.suggestions.append("Add ';' before 'then' keyword")
            elif "Expected TokenType.DO" in error_context.message:
                error_context.suggestions.append("Add ';' before 'do' keyword")
            elif "Expected TokenType.RPAREN" in error_context.message:
                error_context.suggestions.append("Add ')' to close parentheses")
            elif "Expected TokenType.RBRACE" in error_context.message:
                error_context.suggestions.append("Add '}' to close brace group")
            elif "Expected TokenType.FI" in error_context.message:
                error_context.suggestions.append("Add 'fi' to close if statement")

        except ImportError:
            # If errors module is not available, just add basic context
            pass

    # === Context Management ===

    def enter_scope(self, scope: str):
        """Enter a new parsing scope."""
        self.scope_stack.append(scope)
        self.nesting_depth += 1

        if scope == "loop":
            self.loop_depth += 1
        elif scope == "function":
            self.function_depth += 1
        elif scope in ("if", "case", "conditional"):
            self.conditional_depth += 1

    def exit_scope(self) -> Optional[str]:
        """Exit current parsing scope."""
        if self.scope_stack:
            scope = self.scope_stack.pop()
            self.nesting_depth -= 1

            if scope == "loop":
                self.loop_depth = max(0, self.loop_depth - 1)
            elif scope == "function":
                self.function_depth = max(0, self.function_depth - 1)
            elif scope in ("if", "case", "conditional"):
                self.conditional_depth = max(0, self.conditional_depth - 1)

            return scope
        return None

    def current_scope(self) -> Optional[str]:
        """Get current parsing scope."""
        return self.scope_stack[-1] if self.scope_stack else None

    def in_scope(self, scope: str) -> bool:
        """Check if currently in a specific scope."""
        return scope in self.scope_stack

    # === Rule Tracking for Profiling/Debugging ===

    def enter_rule(self, rule_name: str):
        """Enter a parse rule."""
        self.parse_stack.append(rule_name)

        if self.trace_enabled:
            indent = "  " * len(self.parse_stack)
            logger.debug("%s→ %s @ %s", indent, rule_name, self.peek())

        if self.profiler:
            self.profiler.enter_rule(rule_name)

    def exit_rule(self, rule_name: str):
        """Exit a parse rule."""
        if self.parse_stack and self.parse_stack[-1] == rule_name:
            self.parse_stack.pop()

        if self.trace_enabled:
            indent = "  " * len(self.parse_stack)
            logger.debug("%s← %s", indent, rule_name)

        if self.profiler:
            self.profiler.exit_rule(rule_name)

    def current_rule(self) -> Optional[str]:
        """Get current parse rule."""
        return self.parse_stack[-1] if self.parse_stack else None

    def rule_stack_depth(self) -> int:
        """Get current parse rule stack depth."""
        return len(self.parse_stack)

    # === State Queries ===

    def in_loop(self) -> bool:
        """Check if currently parsing inside a loop."""
        return self.loop_depth > 0

    def in_function(self) -> bool:
        """Check if currently parsing inside a function."""
        return self.function_depth > 0

    def in_conditional(self) -> bool:
        """Check if currently parsing inside a conditional."""
        return self.conditional_depth > 0

    def should_collect_errors(self) -> bool:
        """Check if errors should be collected rather than thrown."""
        return self.config.collect_errors or bool(self.errors)

    def should_attempt_recovery(self) -> bool:
        """Check if error recovery should be attempted."""
        return self.config.enable_error_recovery and not self.error_recovery_mode

    def enter_error_recovery(self):
        """Enter error recovery mode."""
        self.error_recovery_mode = True
        if self.profiler:
            self.profiler.record_error_recovery()

    def exit_error_recovery(self):
        """Exit error recovery mode."""
        self.error_recovery_mode = False

    def add_error(self, error: ParseError) -> None:
        """Add error to the error list, checking for fatal errors."""
        if len(self.errors) < self.config.max_errors:
            self.errors.append(error)

        # Check if this is a fatal error
        if (hasattr(error.error_context, 'severity') and
            error.error_context.severity == 'fatal'):
            self.fatal_error = error

    def can_continue_parsing(self) -> bool:
        """Check if parsing can continue."""
        if self.at_end():
            return False

        if self.fatal_error:
            return False

        if self.config.collect_errors:
            return len(self.errors) < self.config.max_errors

        return True

    # === Heredoc Management ===

    def register_heredoc(self, delimiter: str, strip_tabs: bool = False,
                        quoted: bool = False) -> str:
        """Register a heredoc and return a unique key."""
        key = f"heredoc_{len(self.heredoc_trackers)}_{delimiter}"
        self.heredoc_trackers[key] = HeredocInfo(
            delimiter=delimiter,
            strip_tabs=strip_tabs,
            quoted=quoted,
            start_line=self.peek().line
        )
        return key

    def add_heredoc_line(self, key: str, line: str):
        """Add a line to a heredoc."""
        if key in self.heredoc_trackers:
            heredoc = self.heredoc_trackers[key]
            if heredoc.strip_tabs:
                line = line.lstrip('\t')
            heredoc.content_lines.append(line)

    def close_heredoc(self, key: str) -> Optional[str]:
        """Close a heredoc and return its content."""
        if key in self.heredoc_trackers:
            heredoc = self.heredoc_trackers[key]
            heredoc.closed = True
            content = '\n'.join(heredoc.content_lines)
            if heredoc.content_lines:  # Add final newline if there was content
                content += '\n'
            return content
        return None

    def get_open_heredocs(self) -> List[str]:
        """Get list of open heredoc keys."""
        return [key for key, info in self.heredoc_trackers.items() if not info.closed]

    # === Context Manager for State Preservation ===

    def __enter__(self):
        """Save current parsing state flags."""
        saved = {
            'in_test_expr': self.in_test_expr,
            'in_arithmetic': self.in_arithmetic,
            'in_case_pattern': self.in_case_pattern,
            'in_function_body': self.in_function_body,
            'in_command_substitution': self.in_command_substitution,
        }
        if not hasattr(self, '_saved_states'):
            self._saved_states = []
        self._saved_states.append(saved)
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Restore previously saved parsing state flags."""
        if hasattr(self, '_saved_states') and self._saved_states:
            saved = self._saved_states.pop()
            for key, value in saved.items():
                setattr(self, key, value)
        return False

    # === Debug and Reporting ===

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current parser state."""
        return {
            'position': self.current,
            'total_tokens': len(self.tokens),
            'current_token': str(self.peek()),
            'nesting_depth': self.nesting_depth,
            'scope_stack': self.scope_stack.copy(),
            'parse_stack': self.parse_stack.copy(),
            'loop_depth': self.loop_depth,
            'function_depth': self.function_depth,
            'conditional_depth': self.conditional_depth,
            'error_count': len(self.errors),
            'error_recovery_mode': self.error_recovery_mode,
            'special_state': {
                'in_case_pattern': self.in_case_pattern,
                'in_arithmetic': self.in_arithmetic,
                'in_test_expr': self.in_test_expr,
                'in_function_body': self.in_function_body,
                'in_command_substitution': self.in_command_substitution,
                'in_process_substitution': self.in_process_substitution,
            },
            'open_heredocs': len(self.get_open_heredocs())
        }

    def generate_profiling_report(self) -> str:
        """Generate profiling report if enabled."""
        if self.profiler:
            return self.profiler.report()
        return "Profiling not enabled"

    def reset_state(self):
        """Reset parser state for reuse."""
        self.current = 0
        self.errors.clear()
        self.error_recovery_mode = False
        self.fatal_error = None
        self.nesting_depth = 0
        self.scope_stack.clear()
        self.parse_stack.clear()
        self.heredoc_trackers.clear()
        self.in_case_pattern = False
        self.in_arithmetic = False
        self.in_test_expr = False
        self.in_function_body = False
        self.in_command_substitution = False
        self.in_process_substitution = False
        self.loop_depth = 0
        self.function_depth = 0
        self.conditional_depth = 0
