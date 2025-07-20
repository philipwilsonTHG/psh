# Parser Experimentation Guide

## Overview

PSH includes a parser experimentation framework that allows you to implement and compare different parsing approaches while keeping the production recursive descent parser. This guide explains how to use the framework and implement your own experimental parsers.

## Quick Start

### Listing Available Parsers

```bash
$ parser-select
Available parsers:

  recursive_descent (current)
    Aliases: default, rd, recursive
    Hand-coded recursive descent parser with excellent error messages. This is the 
    primary PSH parser with full shell feature support, comprehensive error recovery, 
    and educational error messages.

  parser_combinator
    Aliases: combinator, pc, functional
    Functional parser built from composable combinators. Demonstrates how complex 
    parsers can be built by combining simple parsing primitives using functional 
    composition.
```

### Switching Parsers

```bash
# Switch to parser combinator implementation
$ parser-select parser_combinator
Switched to parser_combinator parser

# Use an alias
$ parser-select pc
Switched to parser_combinator parser

# Switch back to default
$ parser-select default
Switched to recursive_descent parser
```

### Comparing Parsers

```bash
$ parser-compare 'echo hello | grep world'
Comparing parsers for: echo hello | grep world
============================================================

Parser            | Success | Time (ms) | Tokens | AST Type
------------------------------------------------------------
recursive_descent | ✓       |      0.52 |      5 | CommandList
parser_combinator | ✓       |      1.23 |      5 | CommandList

=== recursive_descent ===
Metrics:
  Parse time: 0.52 ms
  Tokens consumed: 5
  Rules evaluated: 0

Characteristics:
  Type: recursive_descent
  Backtracking: True
  Error recovery: True

=== parser_combinator ===
Metrics:
  Parse time: 1.23 ms
  Tokens consumed: 5
  Rules evaluated: 0

Characteristics:
  Type: parser_combinator
  Backtracking: True
  Error recovery: False
```

### Understanding Parser Behavior

```bash
$ parser-explain 'echo hello | grep world'
=== Recursive Descent Parsing ===

The recursive descent parser works by:
1. Starting from the top-level grammar rule (e.g., 'program')
2. Recursively calling parsing functions for each grammar rule
3. Each function consumes tokens that match its rule
4. Building the AST bottom-up as functions return

For these tokens:
  echo hello | grep world

Parsing steps:
  1. parse() -> parse_statement_list()
  2. parse_statement_list() -> parse_pipeline()
  3. parse_pipeline():
     - Parse first command
     - While we see '|' tokens:
       - Consume '|'
       - Parse next command
     - Return Pipeline AST node

Key advantages:
- Clear, readable code structure
- Excellent error messages with context
- Easy to debug and extend
- Natural mapping from grammar to code
```

## Implementing a New Parser

### Step 1: Create Parser Class

Create a new parser implementation that inherits from `AbstractShellParser`:

```python
# psh/parser/implementations/my_parser.py

from ..abstract_parser import AbstractShellParser, ParserCharacteristics, ParserType
from ...ast_nodes import CommandList
from ...token_types import Token

class MyCustomParser(AbstractShellParser):
    """My custom parser implementation."""
    
    def parse(self, tokens: List[Token]) -> CommandList:
        """Parse tokens into AST."""
        # Your parsing logic here
        pass
    
    def parse_partial(self, tokens: List[Token]) -> Tuple[Optional[ASTNode], int]:
        """Parse as much as possible."""
        # Return (ast_or_none, position_stopped)
        pass
    
    def can_parse(self, tokens: List[Token]) -> bool:
        """Quick check if tokens are parseable."""
        # Return True if likely parseable
        pass
    
    def get_name(self) -> str:
        return "my_parser"
    
    def get_description(self) -> str:
        return "Description of my parsing approach"
    
    def get_characteristics(self) -> ParserCharacteristics:
        return ParserCharacteristics(
            parser_type=ParserType.CUSTOM,
            complexity="medium",
            error_recovery=False,
            backtracking=True,
            # ... other characteristics
        )
```

### Step 2: Register Your Parser

Add registration in `psh/builtins/parser_experiment.py` or your own module:

```python
from ..parser.parser_registry import ParserRegistry
from ..parser.implementations.my_parser import MyCustomParser

# Register the parser
ParserRegistry.register(
    "my_parser",
    MyCustomParser,
    aliases=["mp", "custom"]
)
```

### Step 3: Test Your Parser

```bash
# Select your parser
$ parser-select my_parser
Switched to my_parser parser

# Test basic command
$ echo hello
hello

# Compare with other parsers
$ parser-compare 'echo hello' my_parser recursive_descent

# Benchmark performance
$ parser-benchmark 'echo hello | grep world' 1000
```

## Parser Implementation Examples

### Grammar DSL Parser

Here's an example of implementing a parser using a grammar DSL:

```python
class GrammarDSLParser(AbstractShellParser):
    """Parser generated from grammar specification."""
    
    GRAMMAR = """
    program     = statement_list
    statement_list = statement (separator statement)*
    statement   = pipeline
    pipeline    = command (PIPE command)*
    command     = WORD+
    separator   = SEMICOLON | NEWLINE
    """
    
    def __init__(self):
        super().__init__()
        self.grammar = self._compile_grammar()
    
    def _compile_grammar(self):
        # Parse the grammar DSL and generate parser
        return GrammarCompiler(self.GRAMMAR).compile()
    
    def parse(self, tokens: List[Token]) -> CommandList:
        return self.grammar.parse(tokens)
```

### Pratt Parser (Operator Precedence)

Example of a Pratt parser for handling operators:

```python
class PrattParser(AbstractShellParser):
    """Top-down operator precedence parser."""
    
    def __init__(self):
        super().__init__()
        self.precedences = {
            'PIPE': 10,
            'AND_IF': 20,
            'OR_IF': 20,
            'SEMICOLON': 30,
        }
    
    def parse_expression(self, min_precedence=0):
        left = self.parse_primary()
        
        while self.current_precedence() >= min_precedence:
            op = self.advance()
            right_precedence = self.precedences[op.type]
            if self.is_right_associative(op):
                right_precedence -= 1
            right = self.parse_expression(right_precedence)
            left = self.make_binary(left, op, right)
        
        return left
```

### Packrat Parser (Memoized)

Example with memoization for better performance:

```python
class PackratParser(AbstractShellParser):
    """Parser with memoization for linear time complexity."""
    
    def __init__(self):
        super().__init__()
        self.memo = {}
    
    def parse_rule(self, rule_name, position):
        # Check memo table
        key = (rule_name, position)
        if key in self.memo:
            self.metrics.memoization_hits += 1
            return self.memo[key]
        
        self.metrics.memoization_misses += 1
        
        # Parse and memoize result
        result = self._parse_rule_impl(rule_name, position)
        self.memo[key] = result
        return result
```

## Advanced Features

### Configuration Options

Parsers can expose configuration options:

```python
class ConfigurableParser(AbstractShellParser):
    def __init__(self):
        super().__init__()
        self.strict_mode = False
        self.max_depth = 100
    
    def get_configuration_options(self) -> Dict[str, Any]:
        return {
            "strict_mode": "Enable strict parsing (bool)",
            "max_depth": "Maximum recursion depth (int)"
        }
    
    def configure(self, **options):
        if "strict_mode" in options:
            self.strict_mode = options["strict_mode"]
        if "max_depth" in options:
            self.max_depth = options["max_depth"]
```

### Performance Metrics

Track detailed metrics for comparison:

```python
def parse(self, tokens: List[Token]) -> CommandList:
    self.reset_metrics()
    self.metrics.tokens_consumed = len(tokens)
    
    # Track recursion depth
    self._current_depth = 0
    self._max_depth = 0
    
    # Parse and track metrics
    ast = self._parse_impl(tokens)
    
    self.metrics.max_recursion_depth = self._max_depth
    return ast

def _enter_rule(self):
    self._current_depth += 1
    self._max_depth = max(self._max_depth, self._current_depth)
    self.metrics.rules_evaluated += 1

def _exit_rule(self):
    self._current_depth -= 1
```

### Educational Explanations

Provide step-by-step explanations:

```python
def explain_parse(self, tokens: List[Token]) -> str:
    steps = []
    steps.append(f"Parsing {len(tokens)} tokens")
    
    # Simulate parsing with explanations
    for i, token in enumerate(tokens):
        if token.type == 'WORD':
            steps.append(f"  Step {i+1}: Found word '{token.value}'")
        elif token.type == 'PIPE':
            steps.append(f"  Step {i+1}: Found pipe operator")
            steps.append(f"    Creating pipeline node")
    
    return "\n".join(steps)
```

## Best Practices

### 1. Consistent AST Output

All parsers must produce the same AST format for the same input:

```python
# All parsers should produce identical AST for:
# "echo hello"
SimpleCommand(
    args=['echo', 'hello'],
    arg_types=['WORD', 'WORD'],
    redirects=[]
)
```

### 2. Error Handling

Implement meaningful error messages:

```python
def parse(self, tokens: List[Token]) -> CommandList:
    try:
        return self._parse_internal(tokens)
    except Exception as e:
        # Convert to ParseError with context
        if self.position < len(tokens):
            token = tokens[self.position]
            raise ParseError(
                f"Unexpected {token.type} at position {self.position}",
                position=self.position,
                token=token
            )
        else:
            raise ParseError("Unexpected end of input")
```

### 3. Testing

Test your parser against the reference implementation:

```python
def test_parser_compatibility():
    """Ensure parser produces same AST as reference."""
    test_cases = [
        "echo hello",
        "echo hello | grep world",
        "if true; then echo yes; fi",
    ]
    
    reference = RecursiveDescentAdapter()
    my_parser = MyCustomParser()
    
    for command in test_cases:
        tokens = tokenize(command)
        ref_ast = reference.parse(tokens)
        my_ast = my_parser.parse(tokens)
        assert ast_equal(ref_ast, my_ast)
```

## Common Patterns

### Token Stream Management

```python
class TokenStream:
    """Helper for managing token position."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
    
    def peek(self, offset=0):
        pos = self.position + offset
        return self.tokens[pos] if pos < len(self.tokens) else None
    
    def advance(self):
        token = self.peek()
        if token:
            self.position += 1
        return token
    
    def match(self, *types):
        token = self.peek()
        return token and token.type in types
```

### Error Recovery

```python
def parse_with_recovery(self):
    """Parse with error recovery."""
    statements = []
    
    while not self.at_end():
        try:
            stmt = self.parse_statement()
            statements.append(stmt)
        except ParseError as e:
            # Record error
            self.errors.append(e)
            
            # Synchronize to next statement
            self.synchronize()
            
    return CommandList(statements=statements)

def synchronize(self):
    """Skip tokens until statement boundary."""
    while not self.at_end():
        if self.previous().type in ['SEMICOLON', 'NEWLINE']:
            return
        if self.peek().type in ['IF', 'WHILE', 'FOR']:
            return
        self.advance()
```

## Summary

The parser experimentation framework enables:

1. **Educational Comparison**: Compare different parsing approaches
2. **Performance Analysis**: Benchmark parser implementations
3. **Algorithm Research**: Test new parsing algorithms
4. **Feature Development**: Prototype new syntax features

The framework maintains the stability of the production parser while allowing unlimited experimentation with alternative approaches.