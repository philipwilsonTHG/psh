# Lexer Refactoring Plan for PSH

## Overview

This document provides a detailed plan for refactoring the PSH lexer subsystem. It combines the recommendations from REFACTORING_RECOMMENDATIONS.md with additional architectural improvements identified through code analysis.

## Current State Analysis

### Strengths
- Modular package structure (v0.58.0 refactoring)
- Mixin-based architecture separating concerns
- State machine design with O(1) dispatch table
- Rich token support with TokenPart for preserving context
- Comprehensive Unicode support

### Weaknesses
- Fragmented state representation (enum + multiple boolean flags)
- Large core class despite modularization (417 lines)
- Tightly coupled helper methods
- Character-by-character processing inefficiency
- Duplicate logic for quote handling
- Complex error recovery mixed with parsing logic

## Refactoring Goals

1. **Improve Maintainability**: Reduce coupling and clarify responsibilities
2. **Enhance Performance**: Move from O(n) character iteration to O(1) pattern matching
3. **Simplify State Management**: Unify state representation and make transitions explicit
4. **Better Error Recovery**: Centralize and make error recovery strategies pluggable
5. **Increase Testability**: Pure functions and clear interfaces

## Detailed Refactoring Plan

### Phase 1: State Management Unification (Priority: HIGH)

**Goal**: Consolidate fragmented state into a single, explicit state representation.

#### 1.1 Create Unified State Context

```python
# lexer/state_context.py
from dataclasses import dataclass, field
from typing import List, Optional
from .position import LexerState

@dataclass
class LexerContext:
    """Unified state representation for the lexer."""
    state: LexerState
    bracket_depth: int = 0  # Replaces in_double_brackets
    paren_depth: int = 0
    command_position: bool = True
    after_regex_match: bool = False
    quote_stack: List[str] = field(default_factory=list)
    heredoc_delimiters: List[str] = field(default_factory=list)
    
    def in_double_brackets(self) -> bool:
        """Check if we're inside [[ ]]."""
        return self.bracket_depth > 0
    
    def push_quote(self, quote_char: str) -> None:
        """Track nested quote contexts."""
        self.quote_stack.append(quote_char)
    
    def pop_quote(self) -> Optional[str]:
        """Exit quote context."""
        return self.quote_stack.pop() if self.quote_stack else None
```

#### 1.2 Explicit State Transitions

```python
# lexer/transitions.py
from typing import Callable, Dict, List
from .position import LexerState
from .state_context import LexerContext

class StateTransition:
    """Represents a state machine transition."""
    def __init__(
        self, 
        from_state: LexerState,
        condition: Callable[[LexerContext, str], bool],
        to_state: LexerState,
        action: Optional[Callable] = None
    ):
        self.from_state = from_state
        self.condition = condition
        self.to_state = to_state
        self.action = action

class TransitionTable:
    """Manages state transitions for the lexer."""
    def __init__(self):
        self.transitions: Dict[LexerState, List[StateTransition]] = {}
    
    def add_transition(self, transition: StateTransition) -> None:
        """Register a state transition."""
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        self.transitions[transition.from_state].append(transition)
    
    def get_next_state(
        self, 
        context: LexerContext, 
        current_char: str
    ) -> Optional[StateTransition]:
        """Find applicable transition for current state and input."""
        if context.state not in self.transitions:
            return None
        
        for transition in self.transitions[context.state]:
            if transition.condition(context, current_char):
                return transition
        return None
```

### Phase 2: Decouple Helper Methods (Priority: HIGH)

**Goal**: Transform helper methods into pure functions for better testability and reusability.

#### 2.1 Pure Function Helpers

```python
# lexer/pure_helpers.py
from typing import Tuple, Optional, Set

def read_until_char(
    input_text: str,
    start_pos: int,
    target: str,
    escape: bool = False,
    escape_chars: Set[str] = {'"', '\\', '`', '$'}
) -> Tuple[str, int]:
    """
    Read characters until target is found.
    
    Returns:
        Tuple of (content_read, new_position)
    """
    content = ""
    pos = start_pos
    
    while pos < len(input_text) and input_text[pos] != target:
        if escape and input_text[pos] == '\\' and pos + 1 < len(input_text):
            pos += 1  # Skip backslash
            if pos < len(input_text):
                content += input_text[pos]
                pos += 1
        else:
            content += input_text[pos]
            pos += 1
    
    return content, pos

def find_closing_delimiter(
    input_text: str,
    start_pos: int,
    open_delim: str,
    close_delim: str,
    track_quotes: bool = True
) -> Tuple[int, bool]:
    """
    Find matching closing delimiter, handling nesting.
    
    Returns:
        Tuple of (position_after_close, found_closing)
    """
    depth = 1
    pos = start_pos
    in_single_quote = False
    in_double_quote = False
    
    while pos < len(input_text) and depth > 0:
        char = input_text[pos]
        
        # Handle quotes if tracking
        if track_quotes:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == '\\' and pos + 1 < len(input_text):
                pos += 1  # Skip next character
        
        # Track delimiter depth when not in quotes
        if not (in_single_quote or in_double_quote):
            if input_text[pos:pos+len(open_delim)] == open_delim:
                depth += 1
                pos += len(open_delim) - 1
            elif input_text[pos:pos+len(close_delim)] == close_delim:
                depth -= 1
                if depth == 0:
                    return pos + len(close_delim), True
                pos += len(close_delim) - 1
        
        pos += 1
    
    return pos, False
```

#### 2.2 Refactor Existing Helpers

```python
# lexer/helpers.py - Updated
class LexerHelpers:
    """Mixin providing lexer helper methods using pure functions."""
    
    def read_until_char(self, target: str, escape: bool = False) -> str:
        """Read until target character (wrapper for pure function)."""
        from .pure_helpers import read_until_char
        content, new_pos = read_until_char(
            self.input, 
            self.position, 
            target, 
            escape
        )
        self.position = new_pos
        return content
```

### Phase 3: Simplify Quote and Expansion Handling (Priority: HIGH)

**Goal**: Unify quote parsing logic and create a dedicated expansion parser.

#### 3.1 Unified Quote Parser

```python
# lexer/quote_parser.py
from typing import List, Dict, Callable, Optional
from .token_parts import TokenPart
from .pure_helpers import read_until_char

class QuoteRules:
    """Defines parsing rules for different quote types."""
    def __init__(
        self,
        quote_char: str,
        allow_expansions: bool,
        escape_sequences: Dict[str, str],
        allows_newlines: bool = True
    ):
        self.quote_char = quote_char
        self.allow_expansions = allow_expansions
        self.escape_sequences = escape_sequences
        self.allows_newlines = allows_newlines

# Predefined quote rules
QUOTE_RULES = {
    '"': QuoteRules(
        quote_char='"',
        allow_expansions=True,
        escape_sequences={
            'n': '\n', 't': '\t', 'r': '\r', 'b': '\b',
            'f': '\f', 'v': '\v', '\\': '\\', '"': '"',
            '`': '`', '$': '\\$'  # Special handling for $
        },
        allows_newlines=True
    ),
    "'": QuoteRules(
        quote_char="'",
        allow_expansions=False,
        escape_sequences={},  # No escapes in single quotes
        allows_newlines=True
    )
}

class UnifiedQuoteParser:
    """Handles all quote parsing with unified logic."""
    
    def parse_quoted_string(
        self,
        input_text: str,
        start_pos: int,
        rules: QuoteRules,
        expansion_parser: Optional['ExpansionParser'] = None
    ) -> Tuple[List[TokenPart], int]:
        """
        Parse a quoted string according to the given rules.
        
        Returns:
            Tuple of (token_parts, position_after_closing_quote)
        """
        parts: List[TokenPart] = []
        pos = start_pos
        current_value = ""
        part_start = start_pos
        
        while pos < len(input_text):
            char = input_text[pos]
            
            # Check for closing quote
            if char == rules.quote_char:
                # Save final part
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=rules.quote_char,
                        is_variable=False,
                        start_pos=part_start,
                        end_pos=pos
                    ))
                return parts, pos + 1
            
            # Handle expansions if allowed
            if rules.allow_expansions and char == '$' and expansion_parser:
                # Save current part
                if current_value:
                    parts.append(TokenPart(
                        value=current_value,
                        quote_type=rules.quote_char,
                        is_variable=False,
                        start_pos=part_start,
                        end_pos=pos
                    ))
                    current_value = ""
                
                # Parse expansion
                expansion_part, new_pos = expansion_parser.parse_expansion(
                    input_text, pos, rules.quote_char
                )
                parts.append(expansion_part)
                pos = new_pos
                part_start = pos
                continue
            
            # Handle escape sequences
            if char == '\\' and pos + 1 < len(input_text):
                next_char = input_text[pos + 1]
                if next_char in rules.escape_sequences:
                    current_value += rules.escape_sequences[next_char]
                    pos += 2
                    continue
                elif rules.allow_expansions:
                    # In double quotes, backslash only escapes special chars
                    if next_char in {'"', '\\', '`', '$', '\n'}:
                        if next_char == '\n':
                            # Line continuation
                            pos += 2
                            continue
                        current_value += next_char
                        pos += 2
                        continue
                    else:
                        # Keep the backslash
                        current_value += '\\'
                        pos += 1
                        continue
            
            # Regular character
            current_value += char
            pos += 1
        
        # Unclosed quote - add what we have
        if current_value:
            parts.append(TokenPart(
                value=current_value,
                quote_type=rules.quote_char,
                is_variable=False,
                start_pos=part_start,
                end_pos=pos
            ))
        
        return parts, pos
```

#### 3.2 Dedicated Expansion Parser

```python
# lexer/expansion_parser.py
from typing import Tuple, Optional
from .token_parts import TokenPart
from .pure_helpers import find_closing_delimiter

class ExpansionParser:
    """Handles all forms of shell expansions."""
    
    def parse_expansion(
        self,
        input_text: str,
        start_pos: int,  # Points at $
        quote_context: Optional[str] = None
    ) -> Tuple[TokenPart, int]:
        """
        Parse any form of expansion starting with $.
        
        Returns:
            Tuple of (token_part, position_after_expansion)
        """
        if start_pos + 1 >= len(input_text):
            # Lone $ at end
            return self._create_literal_part('$', start_pos, start_pos + 1), start_pos + 1
        
        next_char = input_text[start_pos + 1]
        
        # Dispatch to specific parsers
        if next_char == '(':
            return self._parse_command_or_arithmetic(input_text, start_pos, quote_context)
        elif next_char == '{':
            return self._parse_brace_expansion(input_text, start_pos, quote_context)
        else:
            return self._parse_simple_variable(input_text, start_pos, quote_context)
    
    def _parse_command_or_arithmetic(
        self,
        input_text: str,
        start_pos: int,
        quote_context: Optional[str]
    ) -> Tuple[TokenPart, int]:
        """Parse $(...) or $((...))."""
        if start_pos + 2 < len(input_text) and input_text[start_pos + 2] == '(':
            # Arithmetic expansion $((
            end_pos, found = find_closing_delimiter(
                input_text, start_pos + 3, '(', '))'
            )
            value = input_text[start_pos:end_pos] if found else input_text[start_pos:]
            return TokenPart(
                value=value,
                quote_type=quote_context,
                is_expansion=True,
                expansion_type='arithmetic',
                start_pos=start_pos,
                end_pos=end_pos
            ), end_pos
        else:
            # Command substitution $(
            end_pos, found = find_closing_delimiter(
                input_text, start_pos + 2, '(', ')'
            )
            value = input_text[start_pos:end_pos] if found else input_text[start_pos:]
            return TokenPart(
                value=value,
                quote_type=quote_context,
                is_expansion=True,
                expansion_type='command',
                start_pos=start_pos,
                end_pos=end_pos
            ), end_pos
```

### Phase 4: Modularize Token Recognition (Priority: MEDIUM)

**Goal**: Create a plugin-based token recognition system.

#### 4.1 Token Recognizer Interface

```python
# lexer/recognizers/base.py
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from ..state_context import LexerContext
from ...token_types import Token

class TokenRecognizer(ABC):
    """Base class for token recognizers."""
    
    @abstractmethod
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if this recognizer can handle the current position."""
        pass
    
    @abstractmethod
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """
        Attempt to recognize a token.
        
        Returns:
            Tuple of (token, new_position) or None if not recognized
        """
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Recognition priority (higher = checked first)."""
        pass
```

#### 4.2 Specialized Recognizers

```python
# lexer/recognizers/operator.py
from typing import Dict, Optional, Tuple
from .base import TokenRecognizer
from ..state_context import LexerContext
from ...token_types import Token, TokenType

class OperatorRecognizer(TokenRecognizer):
    """Recognizes shell operators."""
    
    # Operators sorted by length (longest first)
    OPERATORS = {
        3: {'<<<': TokenType.HERE_STRING, '&>>': TokenType.REDIRECT_APPEND_ERR},
        2: {'>>': TokenType.REDIRECT_APPEND, '<<': TokenType.HEREDOC, 
            '&&': TokenType.AND_AND, '||': TokenType.OR_OR,
            '[[': TokenType.DOUBLE_LBRACKET, ']]': TokenType.DOUBLE_RBRACKET},
        1: {'|': TokenType.PIPE, '&': TokenType.AMPERSAND,
            ';': TokenType.SEMICOLON, '(': TokenType.LPAREN,
            ')': TokenType.RPAREN, '<': TokenType.REDIRECT_IN,
            '>': TokenType.REDIRECT_OUT}
    }
    
    @property
    def priority(self) -> int:
        return 100  # High priority
    
    def can_recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> bool:
        """Check if current position might be an operator."""
        if pos >= len(input_text):
            return False
        
        # Quick check for operator start characters
        return input_text[pos] in '<>&|;()[]'
    
    def recognize(
        self, 
        input_text: str, 
        pos: int, 
        context: LexerContext
    ) -> Optional[Tuple[Token, int]]:
        """Recognize operators."""
        # Try longest operators first
        for length in sorted(self.OPERATORS.keys(), reverse=True):
            if pos + length <= len(input_text):
                candidate = input_text[pos:pos + length]
                if candidate in self.OPERATORS[length]:
                    # Apply context-specific rules
                    if self._is_valid_in_context(candidate, context):
                        token_type = self.OPERATORS[length][candidate]
                        token = Token(token_type, candidate, pos, pos + length)
                        return token, pos + length
        
        return None
    
    def _is_valid_in_context(
        self, 
        operator: str, 
        context: LexerContext
    ) -> bool:
        """Check if operator is valid in current context."""
        # Example: [[ is only valid at command position
        if operator == '[[':
            return context.command_position
        # Add more context rules as needed
        return True
```

### Phase 5: Improve Error Recovery (Priority: MEDIUM)

**Goal**: Centralize error recovery with pluggable strategies.

#### 5.1 Error Recovery Framework

```python
# lexer/error_recovery.py
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from .state_context import LexerContext
from .position import Position

class RecoveryPoint:
    """Represents a safe point to resume lexing."""
    def __init__(self, position: int, context: LexerContext):
        self.position = position
        self.context = context.copy()  # Snapshot of context

class ErrorRecoveryStrategy(ABC):
    """Base class for error recovery strategies."""
    
    @abstractmethod
    def can_handle(self, error_type: str) -> bool:
        """Check if this strategy can handle the error type."""
        pass
    
    @abstractmethod
    def recover(
        self, 
        lexer: 'StateMachineLexer',
        error_type: str,
        error_message: str
    ) -> Optional[RecoveryPoint]:
        """
        Attempt to recover from error.
        
        Returns:
            RecoveryPoint to resume from, or None if unrecoverable
        """
        pass

class UnclosedQuoteRecovery(ErrorRecoveryStrategy):
    """Handles unclosed quote errors."""
    
    def can_handle(self, error_type: str) -> bool:
        return error_type in {'unclosed_single_quote', 'unclosed_double_quote'}
    
    def recover(
        self,
        lexer: 'StateMachineLexer',
        error_type: str,
        error_message: str
    ) -> Optional[RecoveryPoint]:
        """Try to find a reasonable point to resume."""
        # In interactive mode, return to end for continuation
        if not lexer.config.strict_mode:
            return RecoveryPoint(
                position=len(lexer.input),
                context=LexerContext(state=LexerState.NORMAL)
            )
        
        # In batch mode, find next line or command separator
        sync_chars = {'\n', ';', '|', '&'}
        pos = lexer.position
        while pos < len(lexer.input):
            if lexer.input[pos] in sync_chars:
                return RecoveryPoint(
                    position=pos + 1,
                    context=LexerContext(state=LexerState.NORMAL)
                )
            pos += 1
        
        return None

class ErrorRecoveryManager:
    """Manages error recovery strategies."""
    
    def __init__(self):
        self.strategies: List[ErrorRecoveryStrategy] = [
            UnclosedQuoteRecovery(),
            # Add more strategies
        ]
    
    def recover_from_error(
        self,
        lexer: 'StateMachineLexer',
        error_type: str,
        error_message: str
    ) -> Optional[RecoveryPoint]:
        """Find and apply appropriate recovery strategy."""
        for strategy in self.strategies:
            if strategy.can_handle(error_type):
                return strategy.recover(lexer, error_type, error_message)
        return None
```

### Phase 6: Scanner-Based Approach (Priority: LONG-TERM)

**Goal**: Replace character iteration with regex-based scanning.

#### 6.1 Token Scanner Implementation

```python
# lexer/scanner.py
import re
from typing import Iterator, List, Tuple, Optional
from ..token_types import Token, TokenType
from .state_context import LexerContext

class TokenPattern:
    """Represents a token pattern for scanning."""
    def __init__(
        self,
        name: str,
        pattern: str,
        token_type: TokenType,
        context_check: Optional[Callable[[LexerContext], bool]] = None
    ):
        self.name = name
        self.pattern = pattern
        self.token_type = token_type
        self.context_check = context_check
        self.regex = re.compile(pattern)

class RegexScanner:
    """Regex-based token scanner."""
    
    # Define token patterns in priority order
    TOKEN_PATTERNS = [
        TokenPattern('COMMENT', r'#[^\n]*', TokenType.COMMENT),
        TokenPattern('DOUBLE_BRACKET', r'\[\[', TokenType.DOUBLE_LBRACKET,
                    lambda ctx: ctx.command_position),
        TokenPattern('HEREDOC', r'<<-?\s*\w+', TokenType.HEREDOC),
        TokenPattern('DOUBLE_QUOTED_STRING', r'"([^"\\\\]|\\\\.)*"', TokenType.STRING),
        TokenPattern('SINGLE_QUOTED_STRING', r"'[^']*'", TokenType.STRING),
        TokenPattern('VARIABLE', r'\$[A-Za-z_]\w*', TokenType.VARIABLE),
        TokenPattern('COMMAND_SUB', r'\$\([^)]*\)', TokenType.COMMAND_SUB),
        TokenPattern('NUMBER', r'\d+', TokenType.WORD),
        TokenPattern('WORD', r'[^\s|&;<>()]+', TokenType.WORD),
        TokenPattern('WHITESPACE', r'\s+', None),  # Skip
        # Add more patterns
    ]
    
    def __init__(self, context: LexerContext):
        self.context = context
        self._compile_scanner()
    
    def _compile_scanner(self):
        """Compile patterns into a scanner."""
        pattern_list = []
        self.pattern_map = {}
        
        for i, token_pattern in enumerate(self.TOKEN_PATTERNS):
            group_name = f'g{i}'
            pattern_list.append(f'(?P<{group_name}>{token_pattern.pattern})')
            self.pattern_map[group_name] = token_pattern
        
        self.scanner_regex = re.compile('|'.join(pattern_list))
    
    def scan(self, text: str) -> Iterator[Token]:
        """Scan text and yield tokens."""
        pos = 0
        
        while pos < len(text):
            match = self.scanner_regex.match(text, pos)
            
            if not match:
                # No pattern matched - error or single character
                yield Token(TokenType.WORD, text[pos], pos, pos + 1)
                pos += 1
                continue
            
            # Find which pattern matched
            for group_name, token_pattern in self.pattern_map.items():
                if match.group(group_name):
                    # Check context if needed
                    if (token_pattern.context_check and 
                        not token_pattern.context_check(self.context)):
                        # Context check failed, treat as word
                        yield Token(
                            TokenType.WORD,
                            match.group(0),
                            match.start(),
                            match.end()
                        )
                    elif token_pattern.token_type:  # Skip whitespace
                        yield Token(
                            token_pattern.token_type,
                            match.group(0),
                            match.start(),
                            match.end()
                        )
                    break
            
            pos = match.end()
```

### Phase 7: Configuration and Validation (Priority: MEDIUM)

**Goal**: Add validation for lexer configuration to prevent invalid states.

#### 7.1 Configuration Validator

```python
# lexer/config_validator.py
from typing import List, Dict, Callable
from .position import LexerConfig

class ConfigurationRule:
    """Represents a configuration validation rule."""
    def __init__(
        self,
        name: str,
        check: Callable[[LexerConfig], bool],
        error_message: str
    ):
        self.name = name
        self.check = check
        self.error_message = error_message

class LexerConfigValidator:
    """Validates lexer configuration for consistency."""
    
    RULES = [
        ConfigurationRule(
            "arithmetic_requires_parameter",
            lambda cfg: not cfg.enable_arithmetic_expansion or cfg.enable_parameter_expansion,
            "Arithmetic expansion requires parameter expansion to be enabled"
        ),
        ConfigurationRule(
            "command_sub_requires_variable",
            lambda cfg: not cfg.enable_command_substitution or cfg.enable_variable_expansion,
            "Command substitution requires variable expansion to be enabled"
        ),
        ConfigurationRule(
            "heredoc_requires_redirections",
            lambda cfg: not cfg.enable_heredocs or cfg.enable_redirections,
            "Heredocs require redirections to be enabled"
        ),
        ConfigurationRule(
            "process_sub_requires_redirections",
            lambda cfg: not cfg.enable_process_substitution or cfg.enable_redirections,
            "Process substitution requires redirections to be enabled"
        ),
    ]
    
    def validate(self, config: LexerConfig) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        for rule in self.RULES:
            if not rule.check(config):
                errors.append(f"{rule.name}: {rule.error_message}")
        
        return errors
    
    def validate_or_raise(self, config: LexerConfig) -> None:
        """Validate configuration and raise exception if invalid."""
        errors = self.validate(config)
        if errors:
            raise ValueError(
                f"Invalid lexer configuration:\n" + "\n".join(f"  - {e}" for e in errors)
            )
```

## Implementation Timeline

### Phase 1 (Weeks 1-2): Foundation ✅ COMPLETED
- [x] Implement unified LexerContext
- [x] Create state transition framework  
- [x] Refactor StateMachineLexer to use new context
- [x] Add comprehensive test suite (18 tests)
- **Status**: Complete with EnhancedStateMachineLexer maintaining full backward compatibility

### Phase 2 (Weeks 3-4): Pure Functions ✅ COMPLETED
- [x] Extract pure helper functions (15+ functions in pure_helpers.py)
- [x] Update existing helpers to use pure functions (EnhancedLexerHelpers)
- [x] Add comprehensive tests for pure functions (55 tests, 100% passing)
- **Status**: Complete with stateless, testable functions for all lexing operations

### Phase 3 (Weeks 5-6): Quote and Expansion Unification ✅ COMPLETED
- [x] Implement UnifiedQuoteParser for all quote types with configurable rules
- [x] Implement ExpansionParser for variables, command substitution, arithmetic
- [x] Integrate unified parsers with main lexer (UnifiedLexer)
- [x] Add comprehensive test suite (34 tests, 100% passing)
- **Status**: Complete with unified quote and expansion parsing, eliminating code duplication

### Phase 4 (Weeks 7-8): Token Recognition ✅ COMPLETED
- [x] Create TokenRecognizer interface with priority-based system
- [x] Implement specialized recognizers (operators, keywords, literals, whitespace, comments)
- [x] Create recognizer registry and dispatch system with priority ordering
- [x] Integrate modular recognition system with lexer (ModularLexer)
- [x] Add comprehensive test suite (29 tests, 100% passing)
- **Status**: Complete with pluggable token recognition system, maintaining full backward compatibility

### Integration Phase (Current): 🚧 IN PROGRESS
- [x] Create integration plan (LEXER_INTEGRATION_PLAN.md)
- [x] Add configuration flag for lexer selection
- [x] Create compatibility test suite
- [ ] Fix compatibility issues (see LEXER_COMPATIBILITY_ISSUES.md)
- [ ] Complete integration testing
- [ ] Make ModularLexer the default
- **Status**: Integration testing revealed compatibility issues that need resolution

### Phase 5 (Deferred): Error Recovery 📅 FUTURE
- [ ] Implement error recovery framework
- [ ] Create recovery strategies
- [ ] Integrate with lexer error handling
- **Status**: DEFERRED - To be implemented after successful integration and production experience

### Phase 6 (Deferred): Scanner Implementation 📅 FUTURE
- [ ] Design regex patterns for all tokens
- [ ] Implement RegexScanner
- [ ] Performance testing and optimization
- [ ] Migration strategy from current lexer
- **Status**: DEFERRED - Future optimization opportunity based on performance needs

### Phase 7 (Deferred): Configuration and Testing 📅 FUTURE
- [ ] Implement configuration validator
- [ ] Add debug/introspection tools
- [ ] Comprehensive test suite updates
- **Status**: DEFERRED - To be implemented as needed

## Testing Strategy

### Unit Tests
- Pure functions with property-based testing
- Individual recognizers with edge cases
- State transition correctness
- Error recovery scenarios

### Integration Tests
- Full lexer with complex inputs
- Unicode handling across all components
- Performance benchmarks
- Compatibility with existing parser

### Regression Tests
- Ensure all existing functionality preserved
- Compare output with current lexer
- Validate against bash for conformance

## Success Metrics

1. **Code Quality**
   - Reduced coupling (measure with dependency analysis)
   - Increased test coverage (target: >90%)
   - Reduced cyclomatic complexity

2. **Performance**
   - Lexing speed improvement (target: 2x faster)
   - Memory usage reduction (target: 20% less)
   - Better scaling with input size

3. **Maintainability**
   - Easier to add new token types
   - Clear separation of concerns
   - Comprehensive documentation

## Risk Mitigation

1. **Backward Compatibility**
   - Maintain current public API
   - Extensive regression testing
   - Phased rollout with feature flags

2. **Performance Regression**
   - Benchmark at each phase
   - Profile critical paths
   - Keep optimized paths for common cases

3. **Integration Issues**
   - Early integration testing with parser
   - Maintain compatibility layer if needed
   - Document all interface changes

## Current Status and Next Steps

### Completed Work
- **Phases 1-4**: All architectural improvements have been implemented and tested
- **Test Coverage**: 136+ tests across all refactored components
- **Architecture**: Clean, modular design with clear separation of concerns

### Integration Status
The integration phase has begun but revealed compatibility issues between the original StateMachineLexer and the new ModularLexer. These issues are documented in LEXER_COMPATIBILITY_ISSUES.md and need to be resolved before the new lexer can replace the old one.

### Decision to Defer Phases 5-6
Based on the principle of iterative development and the need to validate the current architecture in production:
- **Phase 5 (Error Recovery)** and **Phase 6 (Scanner Implementation)** have been deferred
- These phases will be reconsidered after successful integration and production experience
- This allows us to focus on making the current improvements stable and production-ready

### Immediate Next Steps
1. Fix the compatibility issues identified during integration testing
2. Ensure ModularLexer produces identical output to StateMachineLexer for all inputs
3. Complete integration with the configuration flag system
4. Gradually roll out the new lexer with monitoring
5. Gather production feedback before considering additional phases

## Conclusion

This refactoring has successfully created a modular, extensible lexer architecture with comprehensive test coverage. While integration revealed some compatibility challenges, these are solvable issues that will lead to a more maintainable and robust lexer. The decision to defer additional phases allows us to focus on quality and stability while still achieving significant architectural improvements.