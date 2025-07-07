# PSH Lexer Architecture

## Overview

The PSH lexer has been refactored into a modular, extensible architecture that separates concerns and improves testability while maintaining full backward compatibility. The new architecture consists of four major subsystems that work together to provide comprehensive lexical analysis.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Input String                             │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Position Tracker                            │
│  - Line/column tracking                                          │
│  - Unicode-aware positioning                                     │
│  - Error location reporting                                      │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    State Management Layer                        │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  LexerContext   │  │ StateManager │  │ TransitionTable │   │
│  │  - Unified state│  │ - History    │  │ - State rules   │   │
│  │  - Nesting info │  │ - Transitions│  │ - Priorities    │   │
│  └─────────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Recognition Pipeline                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Quote & Expansion Parsers                   │   │
│  │  ┌──────────────────┐  ┌─────────────────────────┐     │   │
│  │  │ UnifiedQuoteParser│  │   ExpansionParser      │     │   │
│  │  │ - Single quotes   │  │ - Variables ($VAR)     │     │   │
│  │  │ - Double quotes   │  │ - Parameters (${VAR})  │     │   │
│  │  │ - Backticks      │  │ - Command sub $(...)   │     │   │
│  │  └──────────────────┘  │ - Arithmetic $((...)    │     │   │
│  │                         └─────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            Modular Token Recognizers                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │  Operator    │  │   Keyword    │  │   Literal    │  │   │
│  │  │  Recognizer  │  │  Recognizer  │  │  Recognizer  │  │   │
│  │  │ Priority:150 │  │ Priority:90  │  │ Priority:70  │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │  ┌──────────────┐  ┌──────────────┐                     │   │
│  │  │ Whitespace   │  │   Comment    │                     │   │
│  │  │  Recognizer  │  │  Recognizer  │                     │   │
│  │  │ Priority:30  │  │ Priority:60  │                     │   │
│  │  └──────────────┘  └──────────────┘                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Recognizer Registry                         │   │
│  │  - Priority-based dispatch                               │   │
│  │  - Dynamic registration                                  │   │
│  │  - Error handling                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Token Stream                              │
│  - Rich tokens with metadata                                     │
│  - Composite token support                                       │
│  - Position information                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. State Management (Phase 1)

The state management layer provides unified context tracking across the entire lexing process.

#### LexerContext (`lexer/state_context.py`)
```python
@dataclass
class LexerContext:
    state: LexerState = LexerState.NORMAL
    bracket_depth: int = 0          # Tracks [[ ]] nesting
    paren_depth: int = 0           # Tracks ( ) nesting
    command_position: bool = True   # Whether at command position
    after_regex_match: bool = False # After =~ operator
    quote_stack: List[str] = field(default_factory=list)
    heredoc_delimiters: List[str] = field(default_factory=list)
```

Key features:
- **Unified State**: Single source of truth for lexer state
- **Nesting Tracking**: Maintains depth counters for various constructs
- **Context Awareness**: Tracks parsing context for context-sensitive tokens
- **Immutability Support**: Can create snapshots for backtracking

#### StateManager (`lexer/transitions.py`)
Manages state transitions with history tracking and validation:
- Maintains transition history for debugging
- Validates state transitions
- Provides state summary and statistics

#### TransitionTable
Defines valid state transitions with priorities and conditions:
- Priority-based transition selection
- Conditional transitions based on context
- Action hooks for state entry/exit

### 2. Pure Helper Functions (Phase 2)

The helper layer provides stateless, pure functions for common lexing operations.

#### Pure Helpers (`lexer/pure_helpers.py`)
Collection of 15+ pure functions including:
- `read_until_char()` - Read until target character
- `find_closing_delimiter()` - Find matching brackets/quotes
- `handle_escape_sequence()` - Process escape sequences
- `extract_variable_name()` - Extract valid variable names
- `validate_brace_expansion()` - Validate ${...} syntax
- `find_balanced_parentheses()` - Match nested parentheses

Key principles:
- **No Side Effects**: Pure input → output transformations
- **Explicit Parameters**: No hidden state dependencies
- **Comprehensive Testing**: Each function independently tested
- **Performance Optimized**: Efficient algorithms for common operations

#### EnhancedLexerHelpers (`lexer/enhanced_helpers.py`)
Wrapper that maintains the existing API while using pure functions internally:
```python
class EnhancedLexerHelpers:
    def read_until_char(self, target: str, escape: bool = False) -> str:
        content, new_pos = pure_helpers.read_until_char(
            self.input, self.position, target, escape
        )
        self.position = new_pos
        return content
```

### 3. Unified Quote and Expansion Parsing (Phase 3)

This layer handles all forms of shell quoting and expansion with consistent logic.

#### UnifiedQuoteParser (`lexer/quote_parser.py`)
Handles all quote types with configurable rules:

```python
class QuoteRules:
    quote_char: str              # Quote character (', ", `)
    allow_expansions: bool       # Whether to process expansions
    escape_sequences: Dict[str, str]  # Escape mappings
    allows_newlines: bool        # Whether newlines are allowed
    allows_nested_quotes: bool   # Whether nesting is allowed
```

Predefined rules for:
- **Single Quotes**: No expansions, no escapes
- **Double Quotes**: Allow expansions and escape sequences
- **Backticks**: Command substitution with limited escapes

#### ExpansionParser (`lexer/expansion_parser.py`)
Unified handling of all shell expansions:

```python
class ExpansionParser:
    def parse_expansion(self, input_text: str, start_pos: int, 
                       quote_context: Optional[str] = None) -> Tuple[TokenPart, int]:
        # Handles:
        # - Simple variables: $VAR
        # - Parameter expansion: ${VAR}
        # - Command substitution: $(command)
        # - Arithmetic expansion: $((expr))
        # - Backtick substitution: `command`
```

Features:
- **Context Awareness**: Respects quote context
- **Error Handling**: Graceful handling of unclosed expansions
- **Configuration**: Disable specific expansion types
- **Unicode Support**: Proper variable name validation

### 4. Modular Token Recognition (Phase 4)

The recognition layer provides a pluggable system for identifying tokens.

#### TokenRecognizer Base (`lexer/recognizers/base.py`)
Abstract interface for all recognizers:

```python
class TokenRecognizer(ABC):
    @abstractmethod
    def can_recognize(self, input_text: str, pos: int, 
                     context: LexerContext) -> bool:
        """Fast check if this recognizer might handle the position."""
        
    @abstractmethod
    def recognize(self, input_text: str, pos: int,
                 context: LexerContext) -> Optional[Tuple[Token, int]]:
        """Attempt to recognize a token."""
        
    @property
    @abstractmethod
    def priority(self) -> int:
        """Recognition priority (higher = checked first)."""
```

#### Specialized Recognizers

**OperatorRecognizer** (Priority: 150)
- Handles all shell operators
- Greedy matching (longest first)
- Context-sensitive operators (`[[`, `]]`, `=~`)

**KeywordRecognizer** (Priority: 90)
- Recognizes shell keywords
- Command position validation
- Complete word boundary detection

**LiteralRecognizer** (Priority: 70)
- Words, identifiers, numbers
- Proper termination at operators
- Unicode identifier support

**CommentRecognizer** (Priority: 60)
- Shell comment detection
- Context-aware comment start

**WhitespaceRecognizer** (Priority: 30)
- Whitespace handling
- Excludes newlines (handled as operators)

#### RecognizerRegistry (`lexer/recognizers/registry.py`)
Central dispatch system:

```python
class RecognizerRegistry:
    def recognize(self, input_text: str, pos: int,
                 context: LexerContext) -> Optional[Tuple[Token, int, TokenRecognizer]]:
        """Try recognizers in priority order."""
        
    def register(self, recognizer: TokenRecognizer) -> None:
        """Register a new recognizer."""
```

Features:
- **Priority Ordering**: Higher priority recognizers checked first
- **Dynamic Registration**: Add/remove recognizers at runtime
- **Error Recovery**: Continue on recognizer failures
- **Statistics**: Track recognizer usage and performance

## Integration Points

### ModularLexer (`lexer/modular_lexer.py`)
The main lexer that integrates all components:

```python
class ModularLexer:
    def __init__(self, input_string: str, config: Optional[LexerConfig] = None):
        # Position tracking
        self.position_tracker = PositionTracker(input_string)
        
        # State management
        self.state_manager = StateManager()
        self.context = self.state_manager.context
        
        # Token recognizers
        self.registry = RecognizerRegistry()
        self._setup_recognizers()
        
        # Unified parsers
        self.expansion_parser = ExpansionParser(self.config)
        self.quote_parser = UnifiedQuoteParser(self.expansion_parser)
```

Tokenization flow:
1. Skip whitespace
2. Try quote and expansion parsers
3. Try modular recognizers in priority order
4. Fallback to word tokenization
5. Update context after each token

### Backward Compatibility

The new architecture maintains full backward compatibility through:

1. **Property Delegation**: Legacy properties map to new context
   ```python
   @property
   def in_double_brackets(self) -> int:
       return self.context.bracket_depth
   ```

2. **API Preservation**: All public methods maintain signatures
3. **Behavior Consistency**: Token output matches original lexer
4. **Import Compatibility**: Original import paths still work

## Configuration

### LexerConfig (`lexer/position.py`)
Comprehensive configuration options:

```python
@dataclass
class LexerConfig:
    # Feature flags
    enable_double_quotes: bool = True
    enable_single_quotes: bool = True
    enable_backtick_quotes: bool = True
    enable_variable_expansion: bool = True
    enable_command_substitution: bool = True
    enable_arithmetic_expansion: bool = True
    enable_parameter_expansion: bool = True
    
    # Behavior options
    posix_mode: bool = False
    case_sensitive: bool = True
    strict_mode: bool = False
    max_nesting_depth: int = 100
    
    # Error handling
    error_recovery: bool = True
    max_errors: int = 100
```

## Testing Architecture

The testing strategy ensures reliability at every level:

### Unit Tests
- **State Management**: 18 tests for context and transitions
- **Pure Helpers**: 55 tests for all helper functions
- **Quote/Expansion Parsing**: 34 tests for unified parsers
- **Token Recognition**: 29 tests for recognizers and registry

### Integration Tests
- End-to-end tokenization tests
- Backward compatibility verification
- Performance benchmarks
- Edge case handling

### Test Patterns
```python
# Pure function testing
def test_pure_function():
    result = pure_helpers.read_until_char("test", 0, "s")
    assert result == ("te", 2)

# Recognizer testing
def test_recognizer():
    recognizer = OperatorRecognizer()
    context = LexerContext()
    result = recognizer.recognize("&&", 0, context)
    assert result[0].type == TokenType.AND_AND

# Integration testing
def test_integration():
    lexer = ModularLexer("echo $USER")
    tokens = lexer.tokenize()
    assert len(tokens) == 3
```

## Performance Considerations

### Optimization Strategies

1. **Fast Path Checks**: `can_recognize()` before expensive recognition
2. **Priority Ordering**: Most common tokens checked first
3. **Character Sets**: O(1) lookups for operator start characters
4. **Greedy Matching**: Longest operators matched first
5. **State Caching**: Avoid redundant state calculations

### Memory Efficiency

1. **Lazy Evaluation**: Parse on demand, not ahead
2. **Shared State**: Single context object, not duplicated
3. **String Views**: Avoid unnecessary string copies
4. **Token Pooling**: Reuse common token instances

## Extensibility

### Adding New Token Types

1. Create a new recognizer:
   ```python
   class MyRecognizer(TokenRecognizer):
       @property
       def priority(self) -> int:
           return 75  # Between keywords and literals
           
       def can_recognize(self, input_text, pos, context):
           # Quick check logic
           
       def recognize(self, input_text, pos, context):
           # Full recognition logic
   ```

2. Register with the system:
   ```python
   lexer.registry.register(MyRecognizer())
   ```

### Adding New Expansion Types

1. Extend ExpansionParser:
   ```python
   def _parse_my_expansion(self, input_text, start_pos, quote_context):
       # Custom expansion logic
   ```

2. Update dispatch logic in `parse_expansion()`

### Adding New Quote Types

1. Define quote rules:
   ```python
   MY_QUOTE_RULES = QuoteRules(
       quote_char='@',
       allow_expansions=False,
       escape_sequences={},
       allows_newlines=True
   )
   ```

2. Register in QUOTE_RULES dictionary

## Future Enhancements

### Phase 5: Error Recovery
- Implement recovery strategies
- Add synchronization points
- Provide error correction suggestions

### Phase 6: Performance Optimization
- Implement DFA-based scanner
- Add caching for common patterns
- Parallel tokenization for large files

### Phase 7: Advanced Features
- Syntax highlighting support
- Incremental reparsing
- Language server protocol integration

## Conclusion

The new lexer architecture provides a solid foundation for the PSH shell with:

- **Modularity**: Clear separation of concerns
- **Extensibility**: Easy to add new features
- **Testability**: Comprehensive test coverage
- **Performance**: Optimized recognition pipeline
- **Maintainability**: Clean, documented code

The architecture successfully balances flexibility with performance while maintaining full backward compatibility with the existing PSH codebase.