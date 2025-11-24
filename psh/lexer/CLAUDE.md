# Lexer Subsystem

This document provides guidance for working with the PSH lexer subsystem.

## Architecture Overview

The lexer transforms shell command strings into token streams using a **modular recognizer pattern**. The main entry point is `tokenize()` in `__init__.py`, which orchestrates:

1. Brace expansion (preprocessing)
2. Tokenization via `ModularLexer`
3. Keyword normalization
4. Token transformation

```
Input String → BraceExpander → ModularLexer → KeywordNormalizer → TokenTransformer → Tokens
```

## Key Files

| File | Purpose |
|------|---------|
| `__init__.py` | Entry point: `tokenize()` and `tokenize_with_heredocs()` |
| `modular_lexer.py` | Core tokenization engine (~900 lines) |
| `state_context.py` | `LexerContext` - unified state management |
| `constants.py` | Keywords, operators, special variables |
| `position.py` | Position tracking, `LexerConfig`, error classes |

### Recognizers (`recognizers/`)

| File | Recognizes |
|------|-----------|
| `operator.py` | Shell operators (`|`, `&&`, `>>`, etc.) |
| `keyword.py` | Reserved words (`if`, `while`, `for`, etc.) |
| `literal.py` | Words, identifiers, assignments (~850 lines) |
| `whitespace.py` | Spaces, tabs |
| `comment.py` | `# comments` |
| `process_sub.py` | Process substitution `<()` and `>()` |
| `arithmetic.py` | Arithmetic expressions `$(())` |
| `registry.py` | Recognizer registration and priority |

### Support Modules

| File | Purpose |
|------|---------|
| `expansion_parser.py` | Parse `${}`, `$()`, `$(())`, backticks |
| `quote_parser.py` | Parse quoted strings (single, double, ANSI-C) |
| `heredoc_lexer.py` | Heredoc tokenization |
| `token_parts.py` | `RichToken` with expansion metadata |
| `unicode_support.py` | Unicode identifier handling |

## Core Patterns

### 1. Modular Recognizer Pattern

Recognizers are registered with priorities and tried in order:

```python
# In recognizers/registry.py
class RecognizerRegistry:
    def register(self, recognizer, priority): ...
    def try_recognize(self, input_text, pos, context): ...

# Priorities (higher = tried first):
# - Operators: 150 (greedy matching for multi-char operators)
# - Keywords: 80 (only at command position)
# - Literals: 70 (fallback for words)
```

### 2. LexerContext State Machine

`LexerContext` tracks all parsing state:

```python
class LexerContext:
    # Nesting depths
    paren_depth: int      # ( )
    bracket_depth: int    # [ ]
    brace_depth: int      # { }

    # Quote state
    in_single_quote: bool
    in_double_quote: bool
    quote_stack: List[str]

    # Parsing context
    in_arithmetic: bool
    in_command_substitution: bool
    at_command_position: bool

    # Array assignment tracking
    in_array_assignment: bool
```

### 3. Token Recognition Flow

```python
# In modular_lexer.py
def _tokenize_next(self):
    # 1. Skip whitespace (unless significant)
    # 2. Check for quotes → delegate to quote_parser
    # 3. Check for expansions ($, `) → delegate to expansion_parser
    # 4. Try each recognizer in priority order
    # 5. Fall back to word tokenization
```

## Common Tasks

### Adding a New Operator

1. Add to `OPERATORS_BY_LENGTH` in `constants.py`:
```python
OPERATORS_BY_LENGTH = {
    3: {'&&=': TokenType.AND_ASSIGN, ...},  # Add here
    2: {'&&': TokenType.AND_AND, ...},
    1: {'&': TokenType.AMPERSAND, ...},
}
```

2. Add `TokenType` in `psh/token_types.py` if needed

3. Add tests in `tests/unit/lexer/`

### Adding a New Keyword

1. Add to `KEYWORDS` in `constants.py`:
```python
KEYWORDS = {
    'if': TokenType.IF,
    'mynewkeyword': TokenType.MY_NEW_KEYWORD,  # Add here
}
```

2. Add `TokenType` in `psh/token_types.py`

3. The `KeywordRecognizer` will automatically recognize it at command position

### Adding a New Recognizer

1. Create class inheriting from `TokenRecognizer`:
```python
# In recognizers/my_recognizer.py
class MyRecognizer(TokenRecognizer):
    priority = 75  # Between keywords (80) and literals (70)

    def can_recognize(self, input_text, pos, context) -> bool:
        # Quick check if this recognizer applies
        return input_text[pos] == '@'

    def recognize(self, input_text, pos, context) -> Optional[Tuple[Token, int]]:
        # Return (token, new_position) or None
        ...
```

2. Register in `recognizers/__init__.py`

## Key Implementation Details

### Quote Handling

- Single quotes: No expansion, literal content
- Double quotes: Variable expansion, command substitution, escape sequences
- ANSI-C quotes (`$'...'`): Escape sequences like `\n`, `\t`
- Quote state tracked in `LexerContext.quote_stack`

### Expansion Parsing

`ExpansionParser` handles:
- `$VAR` and `${VAR}` - variable expansion
- `${VAR:-default}` - parameter expansion with operators
- `$(command)` - command substitution
- `$((expr))` - arithmetic expansion
- `` `command` `` - backtick substitution

### Array Assignment Detection

The lexer detects `arr[key]=value` and `arr=(a b c)` patterns:
- `LiteralRecognizer._is_inside_array_assignment()` tracks state
- Special handling prevents breaking on `]`, `=`, quotes inside assignments

## Testing

```bash
# Run lexer unit tests
python -m pytest tests/unit/lexer/ -v

# Test specific recognizer
python -m pytest tests/unit/lexer/test_token_recognizers_comprehensive.py -v

# Debug tokenization
python -m psh --debug-tokens -c "echo hello"
```

## Common Pitfalls

1. **Greedy Operator Matching**: Operators are matched longest-first. `>>=` matches before `>>` before `>`.

2. **Context-Sensitive Keywords**: `if` is only a keyword at command position. `echo if` tokenizes `if` as WORD.

3. **Quote Nesting**: Double quotes can contain `$()` which can contain more quotes. Track depth carefully.

4. **Array Assignment Quotes**: `arr["key"]=value` - quotes inside `[]` are part of the key, not separate tokens.

5. **Heredoc Interaction**: Heredocs are collected separately. Use `tokenize_with_heredocs()` when needed.

## Debug Options

```bash
python -m psh --debug-tokens    # Show all tokens with types and positions
python -m psh --debug-expansion # Trace expansion parsing
```
