# Parser Subsystem

This document provides guidance for working with the PSH parser subsystem.

## Architecture Overview

The parser transforms token streams into Abstract Syntax Trees (ASTs). PSH uses a **recursive descent parser** with specialized sub-parsers for different language constructs.

```
Tokens → Parser → AST (CommandList/TopLevel)
              ↓
    ┌─────────┼─────────┬──────────┬─────────┐
    ↓         ↓         ↓          ↓         ↓
Statements Commands  Control   Functions  Tests
                    Structures
```

## Key Files

### Core Parser (`recursive_descent/`)

| File | Purpose |
|------|---------|
| `parser.py` | Main `Parser` class - orchestrates all parsing |
| `context.py` | `ParserContext` - centralized state management |
| `base_context.py` | `ContextBaseParser` - base class with context integration |
| `helpers.py` | `TokenGroups`, `ErrorContext`, `ParseError` |

### Specialized Parsers (`recursive_descent/parsers/`)

| File | Parses |
|------|--------|
| `statements.py` | Statement lists, command lists, pipelines |
| `commands.py` | Simple commands, arguments, redirections |
| `control_structures.py` | `if`, `while`, `for`, `case`, `select` |
| `tests.py` | `[[ ]]` test expressions |
| `arithmetic.py` | `(( ))` arithmetic expressions |
| `functions.py` | Function definitions |
| `redirections.py` | I/O redirections, heredocs |
| `arrays.py` | Array assignments |

### Support Infrastructure (`recursive_descent/support/`)

| File | Purpose |
|------|---------|
| `context_factory.py` | `ParserContextFactory` for creating configured contexts |
| `error_collector.py` | Multi-error collection and recovery |
| `word_builder.py` | Build Word AST nodes from tokens |
| `utils.py` | Parser utilities |

### Parser Combinators (`combinators/`)

Alternative parsing approach using functional combinators:

| File | Purpose |
|------|---------|
| `core.py` | Combinator primitives (`token`, `many`, `sequence`, etc.) |
| `parser.py` | Combinator-based parser implementation |
| `control_structures.py` | Control structure combinators |

### Validation (`validation/`)

| File | Purpose |
|------|---------|
| `validation_pipeline.py` | AST validation after parsing |
| `semantic_analyzer.py` | Semantic analysis |
| `validation_rules.py` | Specific validation rules |

## Core Patterns

### 1. Delegating Parser Pattern

The main `Parser` delegates to specialized sub-parsers:

```python
class Parser(ContextBaseParser):
    def __init__(self, ...):
        # Sub-parsers for different constructs
        self.statements = StatementParser(self)
        self.commands = CommandParser(self)
        self.control_structures = ControlStructureParser(self)
        self.tests = TestParser(self)
        self.arithmetic = ArithmeticParser(self)
        self.functions = FunctionParser(self)
        self.redirections = RedirectionParser(self)
        self.arrays = ArrayParser(self)
```

### 2. ParserContext State Management

`ParserContext` tracks all parsing state:

```python
class ParserContext:
    tokens: List[Token]      # Token stream
    current: int             # Current position

    # Parsing state flags
    in_function_body: bool
    in_arithmetic: bool
    in_test_expr: bool
    in_case_pattern: bool
    in_command_substitution: bool

    # Scope tracking
    scope_stack: List[str]   # ["function", "loop", ...]

    # Error handling
    config: ParserConfig
    errors: List[ParseError]
```

### 3. Context Manager for State Preservation

Use `with parser.context:` to save/restore parsing state flags:

```python
# In control_structures.py
def parse_case_item(self):
    with self.parser.context:  # Saves state
        self.parser.context.in_case_pattern = True
        pattern = self.parse_pattern()
    # State automatically restored
```

### 4. TokenGroups for Matching

Predefined token sets for common checks:

```python
class TokenGroups:
    WORD_LIKE = frozenset({WORD, STRING, VARIABLE, ...})
    REDIRECTS = frozenset({REDIRECT_IN, REDIRECT_OUT, ...})
    STATEMENT_SEPARATORS = frozenset({SEMICOLON, NEWLINE, ...})
    CONTROL_KEYWORDS = frozenset({IF, WHILE, FOR, ...})
```

## Parsing Flow

### Top-Level Parsing

```python
def parse(self) -> TopLevel:
    top_level = TopLevel()
    while not self.at_end():
        item = self._parse_top_level_item()  # Function def or statement
        top_level.items.append(item)
    return self._simplify_result(top_level)
```

### Statement Parsing

```
Statement → AndOrList (&&/|| chains)
AndOrList → Pipeline (| chains)
Pipeline → Command (simple or compound)
Command → SimpleCommand | IfConditional | WhileLoop | ...
```

## Common Tasks

### Adding a New Control Structure

1. Add token types in `psh/token_types.py`

2. Add AST node in `psh/ast_nodes.py`:
```python
@dataclass
class MyNewStructure(Command):
    condition: Command
    body: List[Statement]
```

3. Add parser method in `parsers/control_structures.py`:
```python
def parse_my_structure(self) -> MyNewStructure:
    self.parser.expect(TokenType.MY_KEYWORD)
    condition = self.parser.commands.parse_command()
    self.parser.expect(TokenType.DO)
    body = self.parser.statements.parse_command_list_until(TokenType.DONE)
    self.parser.expect(TokenType.DONE)
    return MyNewStructure(condition=condition, body=body)
```

4. Add to `parse_pipeline_component()` in `commands.py`:
```python
elif self.parser.match(TokenType.MY_KEYWORD):
    return self.parse_my_structure_command()
```

5. Add executor method in `psh/executor/control_flow.py`

6. Add tests in `tests/unit/parser/`

### Adding a New Expression Type

1. Create or extend parser in `parsers/`

2. Add AST node in `psh/ast_nodes.py`

3. Wire into appropriate parsing method

4. Add visitor method in executor

## Key Implementation Details

### Keyword vs Word Distinction

Keywords are only recognized at command position:
- `if echo` → IF keyword, WORD "echo"
- `echo if` → WORD "echo", WORD "if"

The parser uses `TokenGroups.CONTROL_KEYWORDS` to identify keywords.

### Compound Command Handling

Compound commands can appear in pipelines:
```python
def parse_pipeline_component(self) -> Command:
    if self.parser.match(TokenType.WHILE):
        return self.parse_while_command()
    elif self.parser.match(TokenType.IF):
        return self.parse_if_command()
    # ... other compound commands
    else:
        return self.parse_command()  # Simple command
```

### Heredoc Collection

Heredocs are parsed in two phases:
1. Tokenization collects the `<<EOF` marker
2. Parser collects heredoc content after the command line

### Error Recovery

Multi-error mode collects errors instead of stopping:

```python
parser = Parser(tokens, config=ParserConfig(collect_errors=True))
result = parser.parse_with_error_collection()
# result.ast may be partial, result.errors contains all errors
```

## Testing

```bash
# Run parser unit tests
python -m pytest tests/unit/parser/ -v

# Test specific feature
python -m pytest tests/unit/parser/test_parser_migration.py -v

# Debug AST output
python -m psh --debug-ast -c "if true; then echo yes; fi"
```

## Common Pitfalls

1. **Token Advancement**: Always call `advance()` to consume tokens after matching. `match()` only peeks.

2. **Newline Handling**: Use `skip_newlines()` appropriately - some constructs allow them, others don't.

3. **Heredoc State**: Heredocs require special handling; they're collected after the statement.

4. **Context Preservation**: Use `with parser.context:` when entering nested parsing contexts.

5. **Error Position**: Always include token position in error messages for debugging.

## Debug Options

```bash
python -m psh --debug-ast      # Show parsed AST structure
python -m psh --debug-tokens   # Show tokens before parsing
python -m psh --validate       # Parse and validate without executing
```

## Word AST

The parser always builds **Word AST nodes** for command arguments. Each
`SimpleCommand.words` list contains `Word` objects with `LiteralPart` and
`ExpansionPart` nodes carrying per-part quote context (`quoted`, `quote_char`).

```python
# "hello $USER!" becomes:
Word(parts=[
    LiteralPart("hello ", quoted=True, quote_char='"'),
    ExpansionPart(VariableExpansion("USER"), quoted=True, quote_char='"'),
    LiteralPart("!", quoted=True, quote_char='"'),
], quote_type='"')
```

`WordBuilder` (`support/word_builder.py`) constructs Word nodes from tokens:
- Decomposes double-quoted STRING tokens with RichToken parts into expansion nodes
- Detects parameter expansion operators in VARIABLE tokens (e.g. `${x:6}`)
- Handles composite words by building multi-part Words with per-part quote context

## Configuration

`ParserConfig` controls parser behavior:

```python
@dataclass
class ParserConfig:
    strict_posix: bool = False        # POSIX-only syntax
    enable_bash_extensions: bool = True
    collect_errors: bool = False      # Multi-error mode
    max_errors: int = 10
```
