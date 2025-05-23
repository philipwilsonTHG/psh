# Parser Architecture Recommendations

## Recommended Approach: Hand-Written Recursive Descent

### Why Recursive Descent for a Teaching Shell
1. **Readable**: Each grammar rule maps directly to a function
2. **Debuggable**: Easy to step through and understand parsing flow
3. **Flexible**: Can add helpful error messages at each parsing stage
4. **No Dependencies**: No external parser generator needed

## Proposed Architecture

### 1. Tokenizer/Lexer
```python
class TokenType(Enum):
    WORD = "WORD"
    PIPE = "PIPE"
    REDIRECT_IN = "REDIRECT_IN"
    REDIRECT_OUT = "REDIRECT_OUT"
    REDIRECT_APPEND = "REDIRECT_APPEND"
    SEMICOLON = "SEMICOLON"
    AMPERSAND = "AMPERSAND"
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    STRING = "STRING"  # Quoted strings
    VARIABLE = "VARIABLE"  # $VAR
    BACKGROUND = "BACKGROUND"
```

### 2. Token Class
```python
@dataclass
class Token:
    type: TokenType
    value: str
    position: int  # For error reporting
```

### 3. AST Node Structure
```python
# Base class
class ASTNode:
    pass

# Command node
@dataclass
class Command(ASTNode):
    args: List[str]
    redirects: List[Redirect]
    background: bool = False

# Pipeline node
@dataclass
class Pipeline(ASTNode):
    commands: List[Command]

# Command list (semicolon-separated)
@dataclass
class CommandList(ASTNode):
    pipelines: List[Pipeline]

# Redirection node
@dataclass
class Redirect(ASTNode):
    type: str  # '<', '>', '>>'
    target: str
```

## Grammar (Simplified)

```
command_list    → pipeline (SEMICOLON pipeline)* [SEMICOLON]
pipeline        → command (PIPE command)*
command         → word+ redirect* [AMPERSAND]
redirect        → REDIRECT_OP word
word            → WORD | STRING | VARIABLE
```

## Parser Structure

### 1. Tokenizer Class
```python
class Tokenizer:
    def __init__(self, input_string):
        self.input = input_string
        self.position = 0
        self.tokens = []
    
    def tokenize(self) -> List[Token]:
        # Main tokenization loop
        # Handle quotes, escapes, operators
        pass
```

### 2. Parser Class
```python
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0
    
    def parse(self) -> CommandList:
        return self.parse_command_list()
    
    def parse_command_list(self) -> CommandList:
        # Parse semicolon-separated commands
        pass
    
    def parse_pipeline(self) -> Pipeline:
        # Parse pipe-separated commands
        pass
    
    def parse_command(self) -> Command:
        # Parse single command with args and redirects
        pass
```

## Key Design Decisions

### 1. Two-Phase Parsing
- **Phase 1**: Tokenize (handle quotes, escapes, split on operators)
- **Phase 2**: Parse tokens into AST
- This separation makes each phase simpler and more testable

### 2. Error Recovery
- Add synchronization points (semicolons, newlines)
- Provide clear error messages with position info
- Consider continuing parsing after errors for better diagnostics

### 3. Lookahead Strategy
- Use one-token lookahead for simplicity
- Implement `peek()` and `consume()` methods
- This handles most shell syntax without backtracking

### 4. Quote Handling
- Process quotes during tokenization
- Preserve quote information for proper variable expansion
- Support single quotes (literal), double quotes (with expansion)

### 5. Operator Precedence
- Pipes bind tighter than semicolons
- Redirections bind to individual commands
- Background & applies to entire pipeline

## Implementation Tips

1. **Start Simple**: Begin with just command execution, then add features
2. **Test-Driven**: Write parser tests for each grammar rule
3. **Error Messages**: Include the problematic token and position
4. **Debugging**: Add optional parse tree printing for visualization

## Example Implementation Order

1. Basic tokenizer (words and spaces)
2. Simple command parser (command with arguments)
3. Add pipes
4. Add redirections
5. Add semicolons and command lists
6. Add quotes and escaping
7. Add variables and expansion
8. Add background execution

## Testing Strategy

Create test cases for:
- Single commands: `ls -la`
- Pipelines: `ls | grep foo`
- Redirections: `echo hello > file.txt`
- Complex: `cat < input.txt | sort | uniq > output.txt`
- Edge cases: Empty input, unclosed quotes, invalid syntax