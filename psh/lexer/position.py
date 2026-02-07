#!/usr/bin/env python3
"""
Position tracking and error handling for the PSH lexer.

This module provides enhanced position tracking with line/column information
and comprehensive error handling with recovery capabilities.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple


@dataclass
class Position:
    """Represents a position in the input text with line and column information."""
    offset: int  # Absolute position in input (0-based)
    line: int    # Line number (1-based)
    column: int  # Column number (1-based)

    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"

    def __repr__(self) -> str:
        return f"Position(offset={self.offset}, line={self.line}, column={self.column})"


class LexerState(Enum):
    """States for the lexer state machine."""
    NORMAL = auto()
    IN_WORD = auto()
    IN_SINGLE_QUOTE = auto()
    IN_DOUBLE_QUOTE = auto()
    IN_VARIABLE = auto()
    IN_COMMAND_SUB = auto()
    IN_ARITHMETIC = auto()
    IN_COMMENT = auto()
    IN_BACKTICK = auto()
    IN_BRACE_VAR = auto()  # Inside ${...}


class LexerError(SyntaxError):
    """Enhanced error with position and context information."""

    def __init__(self, message: str, position: Position, input_text: str, severity: str = "error"):
        self.position = position
        self.input_text = input_text
        self.severity = severity
        super().__init__(self._format_error(message))

    def _format_error(self, message: str) -> str:
        """Format error message with context and position information."""
        lines = self.input_text.splitlines()

        # Show context around error
        context_lines = []
        start_line = max(1, self.position.line - 2)
        end_line = min(len(lines), self.position.line + 2)

        for line_num in range(start_line, end_line + 1):
            if line_num <= len(lines):
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                prefix = "  " if line_num != self.position.line else "> "
                context_lines.append(f"{prefix}{line_num:4d} | {line_content}")

                if line_num == self.position.line:
                    # Add error pointer
                    pointer_pos = 7 + (self.position.column - 1)  # Account for line number prefix
                    context_lines.append(f"       | {' ' * (self.position.column - 1)}^")

        return f"""
Lexer {self.severity.title()}: {message}
  at {self.position}

{chr(10).join(context_lines)}
"""


class RecoverableLexerError(LexerError):
    """Error that allows continued parsing for interactive shells."""

    def __init__(self, message: str, position: Position, input_text: str,
                 recovery_position: int, recovery_state: LexerState = LexerState.NORMAL):
        super().__init__(message, position, input_text, "warning")
        self.recovery_position = recovery_position
        self.recovery_state = recovery_state


@dataclass
class LexerConfig:
    """
    Comprehensive configuration for lexer behavior and features.
    
    This class controls all major aspects of lexer operation including:
    - Feature enablement/disablement
    - Character handling modes  
    - Performance optimizations
    - Error handling behavior
    - Debugging capabilities
    """

    # === CORE FEATURES ===

    # Quote processing
    enable_double_quotes: bool = True      # Process "..." with expansions
    enable_single_quotes: bool = True      # Process '...' as literals
    enable_backtick_quotes: bool = True    # Process `...` command substitution

    # Variable and expansion features
    enable_variable_expansion: bool = True      # Process $VAR
    enable_brace_expansion: bool = True         # Process {a,b,c}
    enable_parameter_expansion: bool = True     # Process ${VAR:-default}
    enable_command_substitution: bool = True    # Process $(cmd)
    enable_arithmetic_expansion: bool = True    # Process $((expr))
    enable_process_substitution: bool = True    # Process <(cmd) and >(cmd)
    enable_history_expansion: bool = True       # Process !! and !n

    # Operator and syntax features
    enable_pipes: bool = True              # Process | operator
    enable_redirections: bool = True       # Process <, >, >>, etc.
    enable_background: bool = True         # Process & operator
    enable_logical_operators: bool = True  # Process && and ||
    enable_compound_commands: bool = True  # Process (( )) and [[ ]]
    enable_heredocs: bool = True          # Process << and <<-

    # Advanced syntax
    enable_tilde_expansion: bool = True    # Process ~user
    enable_glob_patterns: bool = True      # Process *, ?, [...]
    enable_regex_operators: bool = True    # Process =~ operator
    enable_extglob: bool = False          # Process ?()|*()|+()|@()|!() extended globs

    # === CHARACTER HANDLING ===

    posix_mode: bool = False              # When True, restrict to POSIX character sets
    unicode_identifiers: bool = True      # When True, allow Unicode in identifiers
    case_sensitive: bool = True           # Case sensitivity for identifiers
    normalize_whitespace: bool = False    # Normalize tabs to spaces

    # === ERROR HANDLING ===

    strict_mode: bool = True              # If True, fail on first error (batch mode)
    recovery_mode: bool = False           # Attempt error recovery (interactive mode)
    max_errors: int = 10                  # Maximum errors before giving up
    continue_on_errors: bool = False      # Continue parsing after recoverable errors

    # === PERFORMANCE ===

    enable_object_pooling: bool = True    # Pool TokenPart objects for reuse
    buffer_size: int = 8192              # Input buffer size for streaming
    streaming_mode: bool = False         # Enable for large files (>1MB)
    max_token_cache: int = 1000          # Maximum cached tokens
    enable_position_cache: bool = True   # Cache line/column calculations

    # === DEBUGGING ===

    debug_mode: bool = False             # Enable debug output
    debug_states: Optional[set] = None   # Set of LexerState values to trace
    debug_tokens: bool = False           # Log all token creation
    debug_errors: bool = False           # Log all error handling
    debug_performance: bool = False      # Log performance metrics
    trace_method_calls: bool = False     # Trace helper method calls

    # === COMPATIBILITY ===

    bash_compatibility: bool = True      # Enable bash-specific features
    sh_compatibility: bool = False       # Restrict to POSIX sh features
    zsh_compatibility: bool = False      # Enable zsh-specific features
    legacy_mode: bool = False           # Enable deprecated features

    # === MEMORY MANAGEMENT ===

    max_input_size: int = 10 * 1024 * 1024  # 10MB maximum input
    max_token_parts: int = 1000             # Maximum parts per token
    gc_threshold: int = 1000                # Tokens before garbage collection

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration values and fix inconsistencies."""
        # Validate buffer size
        if self.buffer_size < 1024:
            self.buffer_size = 1024
        elif self.buffer_size > 64 * 1024:
            self.buffer_size = 64 * 1024

        # Validate cache sizes
        if self.max_token_cache < 100:
            self.max_token_cache = 100
        if self.max_token_parts < 10:
            self.max_token_parts = 10

        # Validate error limits
        if self.max_errors < 1:
            self.max_errors = 1

        # Validate input size limits
        if self.max_input_size < 1024:
            self.max_input_size = 1024

        # Handle compatibility mode conflicts
        if self.sh_compatibility:
            # POSIX sh mode restricts features
            self.enable_brace_expansion = False
            self.enable_process_substitution = False
            self.posix_mode = True
            self.bash_compatibility = False
            self.zsh_compatibility = False

        if self.legacy_mode:
            # Legacy mode enables older behavior
            self.strict_mode = False
            self.recovery_mode = True

        # Debug state validation
        if self.debug_states is not None:
            # Ensure debug_states contains valid LexerState values
            valid_states = set(LexerState)
            self.debug_states = self.debug_states.intersection(valid_states)

    @classmethod
    def create_interactive_config(cls) -> 'LexerConfig':
        """Create configuration optimized for interactive shell use."""
        return cls(
            strict_mode=False,
            recovery_mode=True,
            continue_on_errors=True,
            max_errors=50,
            debug_mode=False,
            streaming_mode=False
        )

    @classmethod
    def create_batch_config(cls) -> 'LexerConfig':
        """Create configuration optimized for batch script processing."""
        return cls(
            strict_mode=True,
            recovery_mode=False,
            continue_on_errors=False,
            max_errors=1,
            debug_mode=False,
            streaming_mode=False
        )

    @classmethod
    def create_performance_config(cls) -> 'LexerConfig':
        """Create configuration optimized for performance."""
        return cls(
            enable_object_pooling=True,
            enable_position_cache=True,
            streaming_mode=True,
            buffer_size=32 * 1024,
            max_token_cache=5000,
            debug_mode=False,
            trace_method_calls=False
        )

    @classmethod
    def create_debug_config(cls) -> 'LexerConfig':
        """Create configuration for debugging and development."""
        return cls(
            debug_mode=True,
            debug_tokens=True,
            debug_errors=True,
            debug_performance=True,
            trace_method_calls=True,
            strict_mode=False,
            recovery_mode=True
        )

    @classmethod
    def create_posix_config(cls) -> 'LexerConfig':
        """Create POSIX-compliant configuration."""
        return cls(
            sh_compatibility=True,
            posix_mode=True,
            unicode_identifiers=False,
            enable_brace_expansion=False,
            enable_process_substitution=False,
            bash_compatibility=False,
            zsh_compatibility=False
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        result = {}
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            if isinstance(value, set) and value is not None:
                # Convert sets to lists for serialization
                result[field] = list(value)
            else:
                result[field] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'LexerConfig':
        """Create configuration from dictionary."""
        # Convert debug_states back to set if present
        if 'debug_states' in data and data['debug_states'] is not None:
            data['debug_states'] = set(data['debug_states'])
        return cls(**data)


class LexerErrorHandler:
    """Centralized error handling and recovery."""

    def __init__(self, config: LexerConfig):
        self.config = config
        self.errors: List[LexerError] = []

    def handle_error(self, lexer: 'StateMachineLexer', message: str) -> bool:
        """
        Handle a lexical error, potentially recovering.
        Returns True if recovery was successful, False otherwise.
        """
        position = lexer.get_current_position()

        if self.config.recovery_mode:
            recovery_pos, recovery_state = self._attempt_recovery(lexer, message)
            if recovery_pos is not None:
                error = RecoverableLexerError(
                    message, position, lexer.input, recovery_pos, recovery_state
                )
                self.errors.append(error)
                lexer.position = recovery_pos
                lexer.state = recovery_state
                return True

        # No recovery possible or not enabled
        error = LexerError(message, position, lexer.input)
        if self.config.strict_mode:
            raise error
        else:
            self.errors.append(error)
            return False

    def _attempt_recovery(self, lexer: 'StateMachineLexer', message: str) -> Tuple[Optional[int], LexerState]:
        """Attempt to find a recovery position after an error."""
        # Strategy 1: Skip to next whitespace or semicolon
        pos = lexer.position
        while pos < len(lexer.input) and lexer.input[pos] not in ' \t\n;':
            pos += 1

        if pos < len(lexer.input):
            return pos, LexerState.NORMAL

        return None, LexerState.NORMAL


class PositionTracker:
    """Tracks position in input text with line and column information."""

    def __init__(self, input_text: str):
        self.input_text = input_text
        self.position = 0
        self.line = 1
        self.column = 1
        self.line_starts = [0]  # Track start position of each line

    def advance(self, count: int = 1) -> None:
        """Move position forward, updating line/column."""
        for _ in range(count):
            if self.position < len(self.input_text):
                if self.input_text[self.position] == '\n':
                    self.line += 1
                    self.column = 1
                    self.line_starts.append(self.position + 1)
                else:
                    self.column += 1
                self.position += 1

    def get_current_position(self) -> Position:
        """Get current position as a Position object."""
        return Position(self.position, self.line, self.column)

    def get_position_at_offset(self, offset: int) -> Position:
        """Get position information for a specific offset."""
        if offset < 0 or offset > len(self.input_text):
            offset = max(0, min(offset, len(self.input_text)))

        # Find which line this offset is on
        line = 1
        for line_start in self.line_starts:
            if offset >= line_start:
                line = self.line_starts.index(line_start) + 1
            else:
                break

        # Calculate column within that line
        line_start = self.line_starts[line - 1]
        column = offset - line_start + 1

        return Position(offset, line, column)
