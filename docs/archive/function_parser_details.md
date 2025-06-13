# Function Parser Implementation Details

## Parser Lookahead Requirements

The main challenge in parsing functions is disambiguating function definitions from regular commands, especially since we need to support multiple syntaxes.

### Patterns to Recognize

```bash
# POSIX function definition
name() { commands; }
name() { 
    commands
}
name(){ commands; }  # No spaces required

# Bash function keyword
function name { commands; }
function name() { commands; }
function name { 
    commands 
}

# Edge cases to handle
name() # Error: missing body
function # Error: missing name
function name # Error: missing body
name() echo hi # Error: body must be compound command
```

### Lookahead Strategy

We need to look ahead to determine if we're parsing a function definition:

1. If we see `function` keyword → definitely a function definition
2. If we see `WORD '(' ')'` → definitely a function definition  
3. Otherwise → regular command

```python
def _is_function_definition(self):
    """Check if current position starts a function definition."""
    if not self.current_token:
        return False
    
    # Check for 'function' keyword
    if self.current_token.value == 'function':
        return True
    
    # Check for name() pattern
    if self.current_token.type == TokenType.WORD:
        # Need to peek ahead
        next_pos = self.pos + 1
        if next_pos < len(self.tokens):
            next_token = self.tokens[next_pos]
            if next_token.type == TokenType.LPAREN:
                # Check for closing paren
                next_next_pos = next_pos + 1
                if next_next_pos < len(self.tokens):
                    next_next_token = self.tokens[next_next_pos]
                    if next_next_token.type == TokenType.RPAREN:
                        return True
    
    return False
```

## Compound Command Parsing

Functions require a compound command as their body. Initially, we'll support brace groups:

```python
def parse_compound_command(self):
    """Parse a compound command { ... }"""
    if not self.current_token or self.current_token.type != TokenType.LBRACE:
        raise ParseError("Expected '{' to start compound command")
    
    self.consume(TokenType.LBRACE)
    
    # Parse the command list inside
    command_list = self.parse_command_list()
    
    if not self.current_token or self.current_token.type != TokenType.RBRACE:
        raise ParseError("Expected '}' to end compound command")
    
    self.consume(TokenType.RBRACE)
    
    return command_list
```

## Token Type Additions

```python
# In tokenizer.py
class TokenType(Enum):
    # ... existing types ...
    LPAREN = 'LPAREN'        # (
    RPAREN = 'RPAREN'        # )
    LBRACE = 'LBRACE'        # {
    RBRACE = 'RBRACE'        # }
    FUNCTION = 'FUNCTION'    # function keyword

# Update tokenizer operators
OPERATORS = {
    # ... existing operators ...
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
    '{': TokenType.LBRACE,
    '}': TokenType.RBRACE,
}

# Add to keywords
KEYWORDS = {'function'}
```

## Modified Parser Flow

```python
class Parser:
    def parse(self):
        """Main entry point - now handles functions."""
        items = []
        
        while self.current_token:
            if self._is_function_definition():
                items.append(self.parse_function_def())
            else:
                # Regular command list
                cmd_list = self.parse_command_list()
                if cmd_list.and_or_lists:  # Not empty
                    items.append(cmd_list)
            
            # Consume optional semicolon between items
            if self.current_token and self.current_token.type == TokenType.SEMICOLON:
                self.consume(TokenType.SEMICOLON)
        
        # Return a new top-level AST node
        return TopLevel(items)
```

## AST Structure Updates

```python
# In ast_nodes.py
class TopLevel:
    """Root node that can contain functions and commands."""
    def __init__(self, items):
        self.items = items  # List of FunctionDef or CommandList

class FunctionDef:
    """Function definition."""
    def __init__(self, name, body):
        self.name = name
        self.body = body  # CommandList from compound command
```

## Execution Flow Updates

When executing a TopLevel node:

```python
def execute_toplevel(self, toplevel: TopLevel):
    """Execute a top-level script/input."""
    last_exit = 0
    
    for item in toplevel.items:
        if isinstance(item, FunctionDef):
            # Register the function
            self.function_manager.define_function(item.name, item.body)
            last_exit = 0
        elif isinstance(item, CommandList):
            # Execute commands
            last_exit = self.execute_command_list(item)
        
    return last_exit
```

## Special Parsing Considerations

### 1. Brace Handling

Braces `{` and `}` are tricky because they can mean:
- Compound command delimiters (for functions)
- Brace expansion: `{a,b,c}`
- Literal braces in strings

Strategy: Only treat as compound command delimiters when:
- Following a function header
- At statement level (not inside command arguments)

### 2. Newline Handling

Newlines are significant in function definitions:

```bash
# Valid
name() {
    echo hi
}

# Also valid  
name() { echo hi; }

# Invalid (missing semicolon)
name() { echo hi }
```

### 3. Nested Functions

Bash allows defining functions inside functions:

```bash
outer() {
    inner() {
        echo "inner"
    }
    inner
}
```

Our recursive parser structure naturally handles this.

## Error Messages

Provide clear error messages for common mistakes:

```python
# Missing body
"Syntax error: expected compound command after function header"

# Missing closing brace
"Syntax error: unexpected end of input, expected '}'"

# Invalid function name
"Syntax error: invalid function name 'if' (reserved word)"

# Missing parentheses 
"Syntax error: expected '(' after function name"
```

## Testing the Parser

Test cases for the parser:

```python
def test_parse_simple_function():
    tokens = tokenize('greet() { echo "Hello"; }')
    ast = parse(tokens)
    assert isinstance(ast.items[0], FunctionDef)
    assert ast.items[0].name == "greet"

def test_parse_function_keyword():
    tokens = tokenize('function greet { echo "Hello"; }')
    ast = parse(tokens)
    assert isinstance(ast.items[0], FunctionDef)

def test_parse_multiline_function():
    tokens = tokenize('''
    greet() {
        echo "Hello"
        echo "World"
    }
    ''')
    ast = parse(tokens)
    assert isinstance(ast.items[0], FunctionDef)

def test_function_and_command():
    tokens = tokenize('greet() { echo "hi"; }; greet')
    ast = parse(tokens)
    assert len(ast.items) == 2
    assert isinstance(ast.items[0], FunctionDef)
    assert isinstance(ast.items[1], CommandList)
```

This detailed parser design provides a clear path for implementing function definitions while maintaining backward compatibility with existing command parsing.