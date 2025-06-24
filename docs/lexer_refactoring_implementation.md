# Lexer Refactoring Implementation Guide

This document provides a comprehensive implementation guide for refactoring the PSH lexer based on the initial plan in `LEXER_REFACTORING_PLAN.md` and analysis of the current `state_machine_lexer.py`.

## Overview

The current lexer implementation is already well-structured with a state machine approach. This guide focuses on incremental improvements while maintaining backward compatibility.

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

## 4. Unicode Support - **Important for Modern Shell**

Replace ASCII-only character sets with Unicode-aware validation.

### Implementation

```python
# Configuration option
class LexerConfig:
    posix_mode: bool = False  # When True, restrict to POSIX character sets
    unicode_identifiers: bool = True  # When True, allow Unicode in identifiers

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

## 5. Consistent Error Handling - **Essential**

Create a unified error reporting system.

### Implementation

```python
class LexerError(SyntaxError):
    """Enhanced error with position and context information."""
    
    def __init__(self, message: str, position: Position, input_text: str):
        self.position = position
        self.input_text = input_text
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
Lexer Error: {message}
  at line {self.position.line}, column {self.position.column}

{chr(10).join(context_lines)}
"""

# Update all error raises
def _error(self, message: str) -> LexerError:
    """Create error with current position."""
    return LexerError(message, self.get_current_position(), self.input)
```

## 6. Implementation Strategy

### Phase 1: Position Tracking (Foundation)
1. Add `Position` class and update all position tracking
2. Update `TokenPart` and `Token` to use `Position` objects
3. Ensure all error messages include line/column info
4. Update existing tests to verify position accuracy

### Phase 2: Helper Method Extraction
1. Create focused helper methods for each quote type
2. Consolidate variable parsing into dedicated methods
3. Ensure each helper has clear input/output contracts
4. Add unit tests for each helper method

### Phase 3: Unicode Support
1. Replace character sets with Unicode-aware functions
2. Add configuration option for POSIX-only mode
3. Update identifier validation logic
4. Add tests for Unicode identifiers and edge cases

### Phase 4: Enhanced Testing
1. Create comprehensive test suite for each lexer state
2. Add tests for Unicode identifiers
3. Test error messages for clarity and accuracy
4. Add performance benchmarks

## 7. Additional Recommendations Beyond the Plan

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

### B. Performance Optimization

The current implementation creates many `TokenPart` objects. Consider:

1. **Object Pooling**: Reuse `TokenPart` objects for common cases
2. **Lazy Evaluation**: Only create token parts when needed
3. **String Builder**: Use efficient string accumulation

```python
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

### C. Debugging Support

Add optional debug logging:

```python
import logging

class StateMachineLexer:
    def __init__(self, input_string: str, debug: bool = False):
        self.debug = debug
        if debug:
            self.logger = logging.getLogger('psh.lexer')
            self.logger.setLevel(logging.DEBUG)
        # ...
        
    def _debug_log(self, message: str):
        """Log debug message with current state and position."""
        if self.debug:
            self.logger.debug(
                f"[{self.state.name}@{self.line}:{self.column}] {message}"
            )
            
    def transition_to(self, new_state: LexerState):
        """Transition with debug logging."""
        self._debug_log(f"State transition: {self.state} -> {new_state}")
        self.state = new_state
```

### D. Heredoc Improvements

The current heredoc tracking is basic. Consider:

```python
@dataclass
class HeredocMarker:
    delimiter: str
    strip_tabs: bool  # For <<-
    position: Position
    
class StateMachineLexer:
    def __init__(self, input_string: str):
        # ...
        self.heredoc_markers: List[HeredocMarker] = []
        
    def handle_heredoc_operator(self, strip_tabs: bool):
        """Handle << or <<- operator."""
        # Read delimiter
        delimiter = self._read_heredoc_delimiter()
        marker = HeredocMarker(
            delimiter=delimiter,
            strip_tabs=strip_tabs,
            position=self.get_current_position()
        )
        self.heredoc_markers.append(marker)
```

## 8. Testing Strategy

### Test File Organization

Create focused test files:

```
tests/lexer/
├── test_lexer_position_tracking.py  # Line/column accuracy
├── test_lexer_unicode.py           # Unicode identifier support
├── test_lexer_errors.py            # Error message quality
├── test_lexer_states.py            # State transition correctness
├── test_lexer_complex_cases.py     # Real-world shell scripts
├── test_lexer_performance.py       # Performance benchmarks
└── test_lexer_compatibility.py     # Backward compatibility
```

### Example Test Cases

```python
# test_lexer_position_tracking.py
def test_position_tracking_simple():
    lexer = StateMachineLexer("echo hello\necho world")
    tokens = lexer.tokenize()
    
    # First line tokens
    assert tokens[0].position.line == 1
    assert tokens[0].position.column == 1
    assert tokens[1].position.line == 1
    assert tokens[1].position.column == 6
    
    # Second line tokens
    assert tokens[3].position.line == 2
    assert tokens[3].position.column == 1

# test_lexer_unicode.py
def test_unicode_identifiers():
    lexer = StateMachineLexer("λ=42; echo $λ", LexerConfig(unicode_identifiers=True))
    tokens = lexer.tokenize()
    assert tokens[0].value == "λ=42"
    assert tokens[3].value == "λ"

# test_lexer_errors.py
def test_error_formatting():
    with pytest.raises(LexerError) as exc_info:
        lexer = StateMachineLexer('echo "unclosed string')
        lexer.tokenize()
    
    error = exc_info.value
    assert "line 1, column 23" in str(error)
    assert "unclosed string" in str(error).lower()
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

## Timeline Estimate

- **Phase 1** (Position Tracking): 1-2 weeks
- **Phase 2** (Helper Methods): 1 week
- **Phase 3** (Unicode Support): 1-2 weeks
- **Phase 4** (Testing): 1-2 weeks

Total: 4-7 weeks for complete implementation

## Success Metrics

1. All existing tests continue to pass
2. Error messages include accurate line/column information
3. Unicode identifiers work correctly when enabled
4. Performance remains within 10% of current implementation
5. Code coverage increases to >95% for lexer module