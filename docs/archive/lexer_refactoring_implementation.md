# Lexer Refactoring Implementation Guide

This document provides a comprehensive implementation guide for refactoring the PSH lexer based on the initial plan in `LEXER_REFACTORING_PLAN.md` and analysis of the current `state_machine_lexer.py`.

## Overview

The current lexer implementation is already well-structured with a state machine approach. This guide focuses on incremental improvements while maintaining backward compatibility, with enhanced attention to error recovery, performance, security, and integration testing.

## 1. Enhanced Position Tracking - **High Priority**

The plan correctly identifies the need for line/column tracking. Currently, the lexer only tracks absolute position.

### Implementation

```python
@dataclass
class Position:
    offset: int  # Absolute position in input
    line: int    # 1-based line number
    column: int  # 1-based column number
    
class StateMachineLexer:
    def __init__(self, input_string: str):
        # ... existing code ...
        self.line = 1
        self.column = 1
        self.line_starts = [0]  # Track start position of each line
        
    def advance(self, count: int = 1) -> None:
        """Move position forward, updating line/column."""
        for _ in range(count):
            if self.position < len(self.input):
                if self.input[self.position] == '\n':
                    self.line += 1
                    self.column = 1
                    self.line_starts.append(self.position + 1)
                else:
                    self.column += 1
                self.position += 1
                
    def get_current_position(self) -> Position:
        """Get current position as a Position object."""
        return Position(self.position, self.line, self.column)
```

## 2. Modularize Context-Specific Helpers - **Already Partially Done**

The current implementation already has some helper methods, but they could be better organized.

### Current Good Practices
- `_read_word_parts()` and `_read_quoted_parts()` are well-structured
- `parse_variable_or_expansion()` handles variable parsing

### Recommended Improvements

Extract more focused helpers:

```python
def _consume_single_quote(self) -> Tuple[str, bool]:
    """
    Consume content until closing single quote.
    Returns: (content, was_closed)
    """
    content = ""
    while self.current_char() and self.current_char() != "'":
        content += self.current_char()
        self.advance()
    
    was_closed = False
    if self.current_char() == "'":
        self.advance()
        was_closed = True
        
    return content, was_closed

def _consume_double_quote(self) -> Tuple[List[TokenPart], bool]:
    """
    Consume content until closing double quote, handling expansions.
    Returns: (parts, was_closed)
    """
    parts = self._read_quoted_parts('"')
    was_closed = False
    
    if self.current_char() == '"':
        self.advance()
        was_closed = True
        
    return parts, was_closed

def _consume_word(self) -> List[TokenPart]:
    """Consolidate word parsing logic."""
    return self._read_word_parts(quote_context=None)
```

## 3. Refactor Variable and Expansion Parsing - **Critical**

The current implementation has variable parsing spread across multiple methods.

### Improved Structure

```python
def _parse_variable_reference(self, quote_context: Optional[str] = None) -> TokenPart:
    """Unified variable parsing after $ is encountered."""
    start_pos = self.get_current_position()
    
    if self.current_char() == '{':
        return self._parse_braced_variable(quote_context, start_pos)
    elif self.current_char() == '(':
        if self.peek_char() == '(':
            return self._parse_arithmetic_expansion(quote_context, start_pos)
        else:
            return self._parse_command_substitution(quote_context, start_pos)
    else:
        return self._parse_simple_variable(quote_context, start_pos)

def _parse_simple_variable(self, quote_context: Optional[str], start_pos: Position) -> TokenPart:
    """Parse simple variable like $VAR or $1."""
    var_name = self.read_variable_name()
    return TokenPart(
        value=var_name,
        quote_type=quote_context,
        is_variable=True,
        start_pos=start_pos.offset,
        end_pos=self.position
    )

def _parse_braced_variable(self, quote_context: Optional[str], start_pos: Position) -> TokenPart:
    """Parse braced variable like ${VAR}."""
    self.advance()  # Skip {
    var_content = self.read_until_char('}')
    
    if self.current_char() == '}':
        self.advance()
        return TokenPart(
            value='{' + var_content + '}',
            quote_type=quote_context,
            is_variable=True,
            start_pos=start_pos.offset,
            end_pos=self.position
        )
    else:
        raise LexerError("Unclosed variable expansion", self.get_current_position(), self.input)

def _parse_command_substitution(self, quote_context: Optional[str], start_pos: Position) -> TokenPart:
    """Parse command substitution $(...)."""
    self.advance()  # Skip (
    content = self.read_balanced_parens()
    return TokenPart(
        value='$(' + content + ')',
        quote_type=quote_context,
        is_expansion=True,
        start_pos=start_pos.offset,
        end_pos=self.position
    )

def _parse_arithmetic_expansion(self, quote_context: Optional[str], start_pos: Position) -> TokenPart:
    """Parse arithmetic expansion $((...)."""
    self.advance(2)  # Skip ((
    content = self.read_balanced_double_parens()
    return TokenPart(
        value='$((' + content + '))',
        quote_type=quote_context,
        is_expansion=True,
        start_pos=start_pos.offset,
        end_pos=self.position
    )
```

## 4. Enhanced Configuration System - **Important for Flexibility**

Create a comprehensive configuration system to support various modes and features.

### Implementation

```python
@dataclass
class LexerConfig:
    # Character handling
    posix_mode: bool = False  # When True, restrict to POSIX character sets
    unicode_identifiers: bool = True  # When True, allow Unicode in identifiers
    
    # Performance
    enable_object_pooling: bool = True
    buffer_size: int = 8192
    
    # Features
    enable_brace_expansion: bool = True
    enable_history_expansion: bool = True
    enable_process_substitution: bool = True
    
    # Debugging
    debug_mode: bool = False
    debug_states: Set[LexerState] = field(default_factory=set)
    
    # Error handling
    strict_mode: bool = False  # If True, fail on first error
    recovery_mode: bool = True  # Attempt error recovery
    
    # Memory management
    streaming_mode: bool = False  # For large files
    max_token_cache: int = 1000

# Character validation functions
def is_valid_identifier_start(char: str, config: LexerConfig) -> bool:
    """Check if character can start an identifier."""
    if config.posix_mode:
        return char in string.ascii_letters or char == '_'
    return char.isalpha() or char == '_'
    
def is_valid_identifier_char(char: str, config: LexerConfig) -> bool:
    """Check if character can be part of an identifier."""
    if config.posix_mode:
        return char in string.ascii_letters + string.digits or char == '_'
    return char.isalnum() or char == '_'
    
def is_posix_identifier(name: str) -> bool:
    """Check if name is a valid POSIX identifier."""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))

# Update lexer to use config
class StateMachineLexer:
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        self.config = config or LexerConfig()
        # ... rest of initialization ...
```

## 5. Enhanced Error Handling and Recovery - **Essential**

Create a unified error reporting system with recovery capabilities for interactive use.

### Implementation

```python
class LexerError(SyntaxError):
    """Enhanced error with position and context information."""
    
    def __init__(self, message: str, position: Position, input_text: str, severity: str = "error"):
        self.position = position
        self.input_text = input_text
        self.severity = severity
        super().__init__(self._format_error(message))
        
    def _format_error(self, message: str) -> str:
        lines = self.input_text.splitlines()
        error_line = lines[self.position.line - 1] if self.position.line <= len(lines) else ""
        
        # Show context around error
        context_lines = []
        start_line = max(1, self.position.line - 2)
        end_line = min(len(lines), self.position.line + 2)
        
        for line_num in range(start_line, end_line + 1):
            if line_num <= len(lines):
                prefix = "  " if line_num != self.position.line else "> "
                context_lines.append(f"{prefix}{line_num:4d} | {lines[line_num - 1]}")
                
                if line_num == self.position.line:
                    # Add error pointer
                    context_lines.append(f"       | {' ' * (self.position.column - 1)}^")
        
        return f"""
Lexer {self.severity.title()}: {message}
  at line {self.position.line}, column {self.position.column}

{chr(10).join(context_lines)}
"""

class RecoverableLexerError(LexerError):
    """Error that allows continued parsing for interactive shells."""
    
    def __init__(self, message: str, position: Position, input_text: str, 
                 recovery_position: int, recovery_state: LexerState = LexerState.NORMAL):
        super().__init__(message, position, input_text, "warning")
        self.recovery_position = recovery_position
        self.recovery_state = recovery_state

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

# Update lexer to use error handler
def _error(self, message: str) -> bool:
    """Handle error with current position."""
    return self.error_handler.handle_error(self, message)
```

## 6. Revised Implementation Strategy

Implementation phases reordered for better risk management and incremental value delivery.

### Phase 1: Foundation and Error Handling (Low Risk, High Value)
1. Add `Position` class and update all position tracking
2. Implement enhanced error handling with recovery
3. Update `TokenPart` and `Token` to use `Position` objects
4. Ensure all error messages include line/column info
5. Update existing tests to verify position accuracy
6. **Success Criteria**: All existing tests pass, better error messages

### Phase 2: Helper Method Extraction (Medium Risk, Immediate Benefit)
1. Create focused helper methods for each quote type
2. Consolidate variable parsing into dedicated methods
3. Ensure each helper has clear input/output contracts
4. Add unit tests for each helper method
5. **Success Criteria**: Code is more modular, same functionality, 100% test coverage

### Phase 3: Configuration System (Low Risk, Enables Features)
1. Implement comprehensive `LexerConfig` class
2. Add feature flags for all major functionality
3. Update lexer initialization to use configuration
4. Add configuration validation and defaults
5. **Success Criteria**: All features can be enabled/disabled, backward compatibility maintained

### Phase 4: Unicode Support (High Risk, Well-Isolated)
1. Replace character sets with Unicode-aware functions
2. Add configuration option for POSIX-only mode
3. Update identifier validation logic
4. Add tests for Unicode identifiers and edge cases
5. **Success Criteria**: Unicode identifiers work when enabled, POSIX mode remains compatible

### Phase 5: Performance Optimizations (Medium Risk, Measurable)
1. Implement object pooling for TokenPart objects
2. Add streaming lexer for large files
3. Optimize string operations and memory usage
4. Add performance benchmarks and monitoring
5. **Success Criteria**: Performance within 10% of baseline, memory usage improved

### Phase 6: Advanced Features (Optional, Low Priority)
1. Incremental parsing support
2. Source maps for IDE integration
3. Enhanced debugging capabilities
4. Security hardening
5. **Success Criteria**: Advanced features work without breaking core functionality

## 7. Advanced Features and Optimizations

### A. State Validation

Add state transition validation to catch bugs:

```python
VALID_STATE_TRANSITIONS = {
    LexerState.NORMAL: {
        LexerState.IN_WORD, 
        LexerState.IN_SINGLE_QUOTE,
        LexerState.IN_DOUBLE_QUOTE,
        LexerState.IN_VARIABLE,
        LexerState.IN_COMMAND_SUB,
        LexerState.IN_ARITHMETIC,
        LexerState.IN_COMMENT,
        LexerState.IN_BACKTICK,
        LexerState.IN_BRACE_VAR
    },
    LexerState.IN_WORD: {LexerState.NORMAL},
    LexerState.IN_SINGLE_QUOTE: {LexerState.NORMAL},
    LexerState.IN_DOUBLE_QUOTE: {LexerState.NORMAL},
    # ... etc
}

def transition_to(self, new_state: LexerState):
    """Safely transition to a new state with validation."""
    if new_state not in VALID_STATE_TRANSITIONS.get(self.state, set()):
        raise self._error(f"Invalid state transition: {self.state} -> {new_state}")
    self.state = new_state
```

### B. Memory Management and Performance

Address memory efficiency for large files and object allocation:

```python
class StreamingLexer:
    """Memory-efficient lexer for large files."""
    
    def __init__(self, input_stream: io.TextIOBase, buffer_size: int = 8192):
        self.stream = input_stream
        self.buffer = ""
        self.buffer_size = buffer_size
        self.buffer_offset = 0
        
    def _refill_buffer(self):
        """Read more data from stream if needed."""
        if self.position >= len(self.buffer) - 100:  # Keep some lookahead
            new_data = self.stream.read(self.buffer_size)
            self.buffer = self.buffer[self.position:] + new_data
            self.buffer_offset += self.position
            self.position = 0

class TokenPartPool:
    """Object pool for TokenPart instances."""
    
    def __init__(self, initial_size: int = 100):
        self._pool = []
        self._in_use = set()
        
    def acquire(self, **kwargs) -> TokenPart:
        if self._pool:
            part = self._pool.pop()
            # Reset and configure
            for key, value in kwargs.items():
                setattr(part, key, value)
        else:
            part = TokenPart(**kwargs)
        self._in_use.add(part)
        return part
        
    def release(self, part: TokenPart):
        if part in self._in_use:
            self._in_use.remove(part)
            self._pool.append(part)
```

### C. Source Maps for IDE Integration

Track token origins through transformations:

```python
@dataclass
class SourceMap:
    original_position: Position
    transformed_position: Position
    transformation: str  # "brace_expansion", "alias_expansion", etc.

@dataclass 
class Token:
    # ... existing fields ...
    source_map: Optional[SourceMap] = None
    
class SourceMapManager:
    """Manage source mappings through lexical transformations."""
    
    def __init__(self):
        self.mappings: List[SourceMap] = []
        
    def add_transformation(self, original_pos: Position, new_pos: Position, transform_type: str):
        """Record a transformation mapping."""
        self.mappings.append(SourceMap(original_pos, new_pos, transform_type))
        
    def get_original_position(self, transformed_pos: Position) -> Optional[Position]:
        """Get original position from transformed position."""
        for mapping in reversed(self.mappings):
            if mapping.transformed_position.offset <= transformed_pos.offset:
                return mapping.original_position
        return None
```

### D. Incremental Parsing Support

For editors and interactive shells:

```python
class IncrementalLexer(StateMachineLexer):
    """Lexer that supports incremental re-lexing for editors."""
    
    def __init__(self, input_string: str, previous_tokens: List[Token] = None):
        super().__init__(input_string)
        self.previous_tokens = previous_tokens or []
        self.change_ranges: List[Tuple[int, int]] = []
        
    def update_range(self, start_pos: int, end_pos: int, new_text: str) -> List[Token]:
        """Re-lex only the changed range, reusing unchanged tokens."""
        # Find tokens affected by change
        affected_start = self._find_token_at_position(start_pos)
        affected_end = self._find_token_at_position(end_pos)
        
        # Update input string
        self.input = (self.input[:start_pos] + 
                     new_text + 
                     self.input[end_pos:])
        
        # Re-lex affected range
        lexer = StateMachineLexer(self.input[affected_start:affected_end + len(new_text)])
        new_tokens = lexer.tokenize()
        
        # Merge with unchanged tokens
        result = (self.previous_tokens[:affected_start] + 
                 new_tokens + 
                 self.previous_tokens[affected_end:])
        
        self.previous_tokens = result
        return result
        
    def _find_token_at_position(self, pos: int) -> int:
        """Find token index at given position."""
        for i, token in enumerate(self.previous_tokens):
            if token.position <= pos <= token.end_position:
                return i
        return len(self.previous_tokens)
```

### E. Enhanced Debugging Support

Add comprehensive debug logging and introspection:

```python
import logging
from typing import Callable

class LexerDebugger:
    """Enhanced debugging support for lexer development."""
    
    def __init__(self, lexer: StateMachineLexer, config: LexerConfig):
        self.lexer = lexer
        self.config = config
        self.logger = logging.getLogger('psh.lexer')
        self.trace_states = config.debug_states or set()
        self.breakpoints: List[Callable[[StateMachineLexer], bool]] = []
        
    def add_breakpoint(self, condition: Callable[[StateMachineLexer], bool]):
        """Add a conditional breakpoint."""
        self.breakpoints.append(condition)
        
    def should_break(self) -> bool:
        """Check if any breakpoint conditions are met."""
        return any(bp(self.lexer) for bp in self.breakpoints)
        
    def log_state_transition(self, old_state: LexerState, new_state: LexerState):
        """Log state transitions with context."""
        if self.config.debug_mode and (not self.trace_states or new_state in self.trace_states):
            context = self.lexer.input[max(0, self.lexer.position-10):self.lexer.position+10]
            self.logger.debug(
                f"State: {old_state.name} -> {new_state.name} "
                f"@ {self.lexer.line}:{self.lexer.column} "
                f"Context: ...{context}..."
            )
            
    def dump_lexer_state(self) -> dict:
        """Dump current lexer state for inspection."""
        return {
            'position': self.lexer.position,
            'line': self.lexer.line,
            'column': self.lexer.column,
            'state': self.lexer.state.name,
            'current_char': self.lexer.current_char(),
            'next_10_chars': self.lexer.input[self.lexer.position:self.lexer.position+10],
            'token_count': len(self.lexer.tokens),
            'current_parts': len(self.lexer.current_parts)
        }

class StateMachineLexer:
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        # ... existing initialization ...
        if config and config.debug_mode:
            self.debugger = LexerDebugger(self, config)
        
    def transition_to(self, new_state: LexerState):
        """Transition with debug logging and breakpoint checking."""
        old_state = self.state
        
        if hasattr(self, 'debugger'):
            self.debugger.log_state_transition(old_state, new_state)
            if self.debugger.should_break():
                breakpoint()  # Python 3.7+ built-in debugger
                
        self.state = new_state
```

### F. Security Considerations

Address potential security issues in input handling:

```python
class LexerSecurityValidator:
    """Security validation for lexer input."""
    
    def __init__(self, config: LexerConfig):
        self.config = config
        self.max_input_size = 1024 * 1024  # 1MB default
        self.max_nesting_depth = 100
        self.max_tokens = 10000
        
    def validate_input(self, input_string: str) -> None:
        """Validate input for security concerns."""
        # Check input size
        if len(input_string) > self.max_input_size:
            raise LexerError("Input too large", Position(0, 1, 1), "")
            
        # Check for potential DoS patterns
        if input_string.count('$(') > 50:  # Arbitrary limit
            raise LexerError("Too many command substitutions", Position(0, 1, 1), "")
            
        # Validate Unicode normalization doesn't create security issues
        import unicodedata
        normalized = unicodedata.normalize('NFC', input_string)
        if normalized != input_string:
            # Log but don't fail - might be legitimate
            logging.warning("Input contained non-normalized Unicode")
            
    def check_resource_limits(self, lexer: StateMachineLexer) -> None:
        """Check resource usage during lexing."""
        if len(lexer.tokens) > self.max_tokens:
            raise LexerError("Too many tokens generated", lexer.get_current_position(), lexer.input)
```

## 8. Comprehensive Testing Strategy

### Test File Organization

Create focused test files with enhanced coverage:

```
tests/lexer/
├── test_lexer_position_tracking.py  # Line/column accuracy
├── test_lexer_unicode.py           # Unicode identifier support
├── test_lexer_errors.py            # Error message quality and recovery
├── test_lexer_states.py            # State transition correctness
├── test_lexer_complex_cases.py     # Real-world shell scripts
├── test_lexer_performance.py       # Performance benchmarks
├── test_lexer_compatibility.py     # Backward compatibility
├── test_lexer_security.py          # Security validation
├── test_lexer_memory.py            # Memory usage and streaming
├── test_lexer_incremental.py       # Incremental parsing
└── test_lexer_integration.py       # Integration with parser/expander
```

### Validation Strategies

#### Differential Testing
Compare outputs with existing lexer on large corpus:

```python
def test_lexer_compatibility():
    """Comprehensive compatibility testing against existing lexer."""
    test_files = glob.glob("tests/corpus/*.sh")
    for file_path in test_files:
        with open(file_path) as f:
            content = f.read()
        
        old_tokens = old_tokenize(content)
        new_tokens = new_tokenize(content)
        
        assert_tokens_equivalent(old_tokens, new_tokens)

def assert_tokens_equivalent(old_tokens: List[Token], new_tokens: List[Token]):
    """Compare token streams for semantic equivalence."""
    assert len(old_tokens) == len(new_tokens), "Token count mismatch"
    
    for old, new in zip(old_tokens, new_tokens):
        assert old.type == new.type, f"Token type mismatch: {old.type} vs {new.type}"
        assert old.value == new.value, f"Token value mismatch: {old.value} vs {new.value}"
        # Position comparison with tolerance for formatting differences
        assert abs(old.position - new.position.offset) <= 2, "Position mismatch"
```

#### Property-Based Testing
Use hypothesis for edge case discovery:

```python
from hypothesis import given, strategies as st

# Define strategies for shell script generation
shell_identifier = st.text(
    alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd']) | {'_'},
    min_size=1, max_size=20
).filter(lambda x: x[0].isalpha() or x[0] == '_')

shell_string = st.one_of(
    st.text(min_size=0, max_size=100),  # Unquoted
    st.text(min_size=0, max_size=100).map(lambda x: f'"{x}"'),  # Double quoted
    st.text(min_size=0, max_size=100).map(lambda x: f"'{x}'"),  # Single quoted
)

shell_command = st.builds(
    lambda cmd, args: f"{cmd} {' '.join(args)}",
    cmd=shell_identifier,
    args=st.lists(shell_string, min_size=0, max_size=5)
)

@given(shell_script=shell_command)
def test_lexer_properties(shell_script):
    """Test lexer properties hold for generated shell scripts."""
    try:
        tokens = tokenize(shell_script)
        
        # Property 1: Round-trip accuracy
        reconstructed = reconstruct_from_tokens(tokens)
        retokenized = tokenize(reconstructed)
        assert_tokens_equivalent(tokens, retokenized)
        
        # Property 2: Position correctness
        for token in tokens:
            if hasattr(token, 'position') and isinstance(token.position, Position):
                assert 0 <= token.position.offset <= len(shell_script)
                assert token.position.line >= 1
                assert token.position.column >= 1
                
        # Property 3: No token gaps or overlaps
        for i in range(len(tokens) - 1):
            assert tokens[i].end_position <= tokens[i+1].position.offset
            
    except LexerError:
        # Some generated scripts may be invalid - that's okay
        pass
```

### Example Test Cases

```python
# test_lexer_position_tracking.py
def test_position_tracking_multiline():
    input_text = "echo hello\necho 'world with spaces'\necho $var"
    lexer = StateMachineLexer(input_text)
    tokens = lexer.tokenize()
    
    # Verify specific positions
    assert tokens[0].position.line == 1 and tokens[0].position.column == 1  # 'echo'
    assert tokens[1].position.line == 1 and tokens[1].position.column == 6  # 'hello'
    assert tokens[3].position.line == 2 and tokens[3].position.column == 1  # 'echo'
    assert tokens[4].position.line == 2 and tokens[4].position.column == 6  # quoted string
    assert tokens[6].position.line == 3 and tokens[6].position.column == 6  # '$var'

def test_position_tracking_with_tabs():
    input_text = "echo\thello\n\techo world"  # Mix of spaces and tabs
    lexer = StateMachineLexer(input_text)
    tokens = lexer.tokenize()
    
    # Tabs should count as single characters for column counting
    assert tokens[1].position.column == 6  # 'hello' after tab
    assert tokens[3].position.column == 2  # 'echo' after leading tab

# test_lexer_unicode.py  
def test_unicode_identifiers_comprehensive():
    config = LexerConfig(unicode_identifiers=True, posix_mode=False)
    test_cases = [
        ("λ=42", ["λ=42"]),  # Greek lambda
        ("café=shop", ["café=shop"]),  # Accented characters
        ("变量=value", ["变量=value"]),  # Chinese characters
        ("مرحبا=hello", ["مرحبا=hello"]),  # Arabic characters
    ]
    
    for input_text, expected_values in test_cases:
        lexer = StateMachineLexer(input_text, config)
        tokens = lexer.tokenize()
        actual_values = [t.value for t in tokens if t.type == TokenType.WORD]
        assert actual_values == expected_values

def test_posix_mode_restrictions():
    config = LexerConfig(unicode_identifiers=False, posix_mode=True)
    
    # Should work: POSIX identifiers
    lexer = StateMachineLexer("valid_var=42", config)
    tokens = lexer.tokenize()
    assert len(tokens) >= 1
    
    # Should fail or treat as separate tokens: Unicode identifiers
    lexer = StateMachineLexer("λ=42", config)
    tokens = lexer.tokenize()
    # In POSIX mode, λ should not be treated as a valid identifier start
    assert tokens[0].value != "λ=42"

# test_lexer_errors.py
def test_error_recovery():
    config = LexerConfig(recovery_mode=True, strict_mode=False)
    input_text = 'echo "unclosed string\necho "another command"'
    
    lexer = StateMachineLexer(input_text, config)
    tokens = lexer.tokenize()
    
    # Should have recovered and parsed the second command
    assert any(t.value == "another command" for t in tokens)
    assert len(lexer.error_handler.errors) > 0
    assert isinstance(lexer.error_handler.errors[0], RecoverableLexerError)

def test_error_formatting_context():
    input_text = "line1\nline2\necho 'unclosed\nline4\nline5"
    
    with pytest.raises(LexerError) as exc_info:
        lexer = StateMachineLexer(input_text)
        lexer.tokenize()
    
    error_str = str(exc_info.value)
    assert "line 3" in error_str  # Error is on line 3
    assert "line2" in error_str   # Context shows line 2
    assert "line4" in error_str   # Context shows line 4
    assert "^" in error_str       # Error pointer present

# test_lexer_performance.py
def test_performance_benchmarks():
    """Performance regression tests."""
    import time
    
    # Large script for performance testing
    large_script = "\n".join([
        f"echo 'command {i}' | grep pattern{i % 10} > /tmp/output{i}"
        for i in range(1000)
    ])
    
    start_time = time.time()
    lexer = StateMachineLexer(large_script)
    tokens = lexer.tokenize()
    end_time = time.time()
    
    # Should process at least 1MB/s (adjust based on actual performance)
    processing_time = end_time - start_time
    throughput = len(large_script) / processing_time
    assert throughput > 1024 * 1024, f"Throughput too low: {throughput} bytes/sec"
    
    # Memory usage should be reasonable
    import sys
    memory_per_token = sys.getsizeof(tokens) / len(tokens)
    assert memory_per_token < 1000, f"Memory per token too high: {memory_per_token} bytes"

# test_lexer_security.py  
def test_security_input_validation():
    config = LexerConfig()
    validator = LexerSecurityValidator(config)
    
    # Test input size limits
    large_input = "echo " + "a" * (1024 * 1024 + 1)  # Exceed 1MB limit
    with pytest.raises(LexerError, match="Input too large"):
        validator.validate_input(large_input)
    
    # Test DoS pattern detection
    malicious_input = "$($($($($(echo hello)))))"  # Deeply nested
    with pytest.raises(LexerError, match="Too many command substitutions"):
        validator.validate_input(malicious_input)

# test_lexer_integration.py
def test_parser_integration():
    """Test that lexer changes don't break parser."""
    from psh.parser import Parser
    
    test_scripts = [
        "if [ -f file ]; then echo found; fi",
        "for x in a b c; do echo $x; done", 
        "function test() { local var=value; echo $var; }",
        "echo $(echo nested | grep pattern)"
    ]
    
    for script in test_scripts:
        lexer = StateMachineLexer(script)
        tokens = lexer.tokenize()
        
        # Should parse without errors
        parser = Parser(tokens)
        ast = parser.parse()
        assert ast is not None

def test_expansion_integration():
    """Test that TokenPart metadata works with expansion."""
    from psh.expansion_manager import ExpansionManager
    
    script = 'echo "Hello $name"'
    lexer = StateMachineLexer(script)
    tokens = lexer.tokenize()
    
    # Find the string token
    string_token = next(t for t in tokens if t.type == TokenType.STRING)
    assert hasattr(string_token, 'parts')
    assert len(string_token.parts) >= 2  # "Hello " and variable part
    
    # Expansion should work with parts
    expander = ExpansionManager({'name': 'World'})
    expanded = expander.expand_token(string_token)
    assert expanded == "Hello World"
```

## 9. Migration Path

### Backward Compatibility

Ensure the refactored lexer maintains compatibility:

1. Keep existing public API unchanged
2. Make new features opt-in via configuration
3. Preserve token output format
4. Add compatibility tests

### Gradual Rollout

1. **Phase 1**: Implement position tracking internally without changing Token interface
2. **Phase 2**: Add optional RichToken with position info
3. **Phase 3**: Migrate parser to use position info for better errors
4. **Phase 4**: Enable Unicode support with feature flag

## Summary

The refactoring plan is solid but should be implemented incrementally. The current implementation already has good structure, so focus on:

1. **Immediate wins**: Add line/column tracking and improve error messages
2. **Code organization**: Extract cleaner helper methods
3. **Modernization**: Add Unicode support with POSIX compatibility mode
4. **Robustness**: Add state validation and comprehensive tests

The key is to maintain backward compatibility while improving the internals. Each phase should be testable independently, allowing for gradual migration without breaking existing functionality.

### Performance Benchmarks

Create standardized benchmarks with specific targets:

```python
class LexerBenchmarkSuite:
    """Comprehensive performance benchmarking for lexer."""
    
    def __init__(self):
        self.test_files = {
            'small': self._generate_small_script(),      # ~1KB
            'medium': self._generate_medium_script(),    # ~100KB  
            'large': self._generate_large_script(),      # ~1MB
            'configure': self._load_configure_script(),  # Real autotools script
            'kernel': self._load_kernel_script(),        # Linux kernel build script
        }
        
    def benchmark_throughput(self):
        """Measure lexing throughput for different file sizes."""
        results = {}
        for name, content in self.test_files.items():
            start_time = time.perf_counter()
            lexer = StateMachineLexer(content)
            tokens = lexer.tokenize()
            end_time = time.perf_counter()
            
            throughput = len(content) / (end_time - start_time)
            results[name] = {
                'size': len(content),
                'tokens': len(tokens),
                'time': end_time - start_time,
                'throughput': throughput,
                'tokens_per_sec': len(tokens) / (end_time - start_time)
            }
        return results
        
    def benchmark_memory(self):
        """Measure memory usage during lexing."""
        import tracemalloc
        results = {}
        
        for name, content in self.test_files.items():
            tracemalloc.start()
            lexer = StateMachineLexer(content)
            tokens = lexer.tokenize()
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            results[name] = {
                'peak_memory': peak,
                'current_memory': current,
                'memory_per_byte': peak / len(content),
                'memory_per_token': peak / len(tokens)
            }
        return results

# Target performance metrics
PERFORMANCE_TARGETS = {
    'throughput': {
        'small': 10 * 1024 * 1024,   # 10 MB/s for small files
        'medium': 5 * 1024 * 1024,   # 5 MB/s for medium files  
        'large': 1 * 1024 * 1024,    # 1 MB/s for large files
    },
    'memory_efficiency': {
        'memory_per_byte': 10,       # Max 10 bytes overhead per input byte
        'memory_per_token': 500,     # Max 500 bytes per token
    },
    'startup_time': 0.010,           # Max 10ms cold start
}
```

## 9. Migration Path and Rollback Strategy

### Backward Compatibility

Ensure the refactored lexer maintains compatibility:

1. **API Compatibility**: Keep existing public API unchanged
2. **Feature Flags**: Make new features opt-in via configuration
3. **Token Format**: Preserve token output format for existing consumers
4. **Behavioral Compatibility**: Maintain existing tokenization behavior by default

### Gradual Rollout Strategy

```python
# Phase 1: Side-by-side deployment
class HybridLexer:
    """Allows gradual migration with fallback to old lexer."""
    
    def __init__(self, input_string: str, use_new_lexer: bool = False):
        self.input_string = input_string
        self.use_new_lexer = use_new_lexer
        
    def tokenize(self) -> List[Token]:
        if self.use_new_lexer:
            try:
                return StateMachineLexer(self.input_string).tokenize()
            except Exception as e:
                logging.warning(f"New lexer failed, falling back: {e}")
                return old_tokenize(self.input_string)
        else:
            return old_tokenize(self.input_string)

# Environment variable control
USE_NEW_LEXER = os.environ.get('PSH_USE_NEW_LEXER', 'false').lower() == 'true'
```

### Rollback Procedures

If a phase fails or introduces regressions:

1. **Immediate Rollback**: Revert to previous commit via git
2. **Feature Flags**: Disable problematic features via configuration  
3. **Hybrid Mode**: Fall back to old lexer for problematic inputs
4. **Gradual Rollback**: Disable new features incrementally

```python
# Emergency rollback configuration
EMERGENCY_ROLLBACK_CONFIG = LexerConfig(
    posix_mode=True,           # Use most conservative mode
    unicode_identifiers=False, # Disable new features
    recovery_mode=False,       # Disable error recovery
    enable_object_pooling=False, # Disable optimizations
    strict_mode=True,          # Fail fast on any issues
)
```

### Integration Testing Strategy

Test lexer changes don't break downstream components:

1. **Parser Integration**: Ensure token format compatibility
2. **Expansion Integration**: Verify TokenPart metadata correctness  
3. **Error Propagation**: Test error message flow through components
4. **Performance Impact**: Measure end-to-end shell execution time

## 10. Revised Timeline and Resource Allocation

### Updated Timeline

- **Phase 1** (Foundation): 2-3 weeks
  - Position tracking: 1 week
  - Error handling: 1-2 weeks  
  - **Deliverable**: Better error messages, all tests pass

- **Phase 2** (Refactoring): 1-2 weeks
  - Helper method extraction: 1 week
  - Code organization: 1 week
  - **Deliverable**: More maintainable code, 100% test coverage

- **Phase 3** (Configuration): 1 week
  - Configuration system: 1 week
  - **Deliverable**: Feature flags, backward compatibility

- **Phase 4** (Unicode): 2-3 weeks
  - Unicode support: 1-2 weeks
  - POSIX compatibility: 1 week
  - **Deliverable**: Unicode identifiers, POSIX mode

- **Phase 5** (Performance): 2-3 weeks
  - Object pooling: 1 week
  - Streaming lexer: 1-2 weeks
  - Benchmarking: 1 week
  - **Deliverable**: 10% performance improvement

- **Phase 6** (Advanced Features): 3-4 weeks (Optional)
  - Incremental parsing: 2 weeks
  - Source maps: 1 week
  - Security hardening: 1 week
  - **Deliverable**: Advanced IDE support

**Total**: 9-16 weeks for complete implementation (6-9 weeks for core features)

### Resource Requirements

- **Developer time**: 1 senior developer full-time
- **Testing infrastructure**: Expand test corpus, add performance monitoring
- **Documentation**: Update lexer documentation and migration guides
- **Code review**: Plan for thorough review of each phase

## 11. Success Metrics and Monitoring

### Quantitative Metrics

1. **Correctness**: All existing tests continue to pass (100%)
2. **Performance**: Lexing speed within 10% of baseline
3. **Memory**: Memory usage improved by 20% for large files
4. **Error Quality**: Error messages include accurate position info (100%)
5. **Coverage**: Code coverage >95% for lexer module
6. **Unicode**: Unicode identifiers work when enabled (100%)

### Qualitative Metrics

1. **Code Quality**: Reduced cyclomatic complexity, better modularity
2. **Maintainability**: Easier to add new features and fix bugs
3. **Developer Experience**: Better debugging tools and error messages
4. **User Experience**: More helpful error messages for shell users

### Monitoring and Alerts

```python
class LexerHealthMonitor:
    """Monitor lexer health in production."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        
    def record_tokenization(self, input_size: int, token_count: int, 
                          processing_time: float, error_count: int):
        """Record metrics for a tokenization operation."""
        self.metrics['throughput'].append(input_size / processing_time)
        self.metrics['tokens_per_second'].append(token_count / processing_time)
        self.metrics['error_rate'].append(error_count / max(1, token_count))
        
    def check_health(self) -> Dict[str, bool]:
        """Check if lexer performance is within acceptable bounds."""
        if not self.metrics['throughput']:
            return {'status': 'unknown'}
            
        recent_throughput = self.metrics['throughput'][-100:]
        recent_error_rate = self.metrics['error_rate'][-100:]
        
        return {
            'throughput_ok': sum(recent_throughput) / len(recent_throughput) > 1024*1024,
            'error_rate_ok': sum(recent_error_rate) / len(recent_error_rate) < 0.01,
            'status': 'healthy'
        }
```

This comprehensive plan now addresses all the major concerns and provides a robust foundation for implementing the lexer refactoring safely and effectively.