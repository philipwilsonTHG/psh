# Shell Functions Architecture Summary for psh

## Executive Summary

Shell functions are a critical feature that transforms psh from a simple command executor to a programmable shell. This document provides specific architectural recommendations for implementing functions in psh.

## Key Design Decisions

### 1. **Parser Architecture**
- **Approach**: Extend the recursive descent parser with lookahead for function detection
- **Rationale**: Maintains the educational clarity while handling the grammar ambiguity
- **Impact**: Minimal changes to existing parser structure

### 2. **Storage Architecture**
- **Approach**: Separate FunctionManager class similar to AliasManager
- **Rationale**: Clean separation of concerns, easier testing
- **Storage**: In-memory dictionary, no persistence by default

### 3. **Execution Model**
- **Approach**: Functions execute in current shell process (no fork)
- **Context**: Save/restore positional parameters, maintain call stack
- **Precedence**: Function > External command, but Builtin > Function

### 4. **AST Design**
- **New Nodes**: `FunctionDef` for definitions, reuse `CommandList` for body
- **Top Level**: Introduce `TopLevel` node to handle mixed functions/commands
- **Minimal Change**: Reuse existing command execution infrastructure

## Specific Implementation Steps

### Step 1: Token Types (tokenizer.py)
```python
# Add to TokenType enum
LPAREN = auto()      # (
RPAREN = auto()      # )
LBRACE = auto()      # {
RBRACE = auto()      # }
FUNCTION = auto()    # function keyword
```

### Step 2: Tokenizer Updates (tokenizer.py)
```python
# In tokenize_operator method, add:
elif char == '(':
    return Token(TokenType.LPAREN, char, self.position)
elif char == ')':
    return Token(TokenType.RPAREN, char, self.position)
elif char == '{':
    return Token(TokenType.LBRACE, char, self.position)
elif char == '}':
    return Token(TokenType.RBRACE, char, self.position)

# In tokenize_word, check for 'function' keyword
```

### Step 3: AST Nodes (ast_nodes.py)
```python
class TopLevel:
    """Root node containing functions and/or commands."""
    def __init__(self):
        self.items = []  # List of FunctionDef or CommandList

class FunctionDef:
    """Function definition."""
    def __init__(self, name: str, body: CommandList):
        self.name = name
        self.body = body
```

### Step 4: Parser Extensions (parser.py)
```python
class Parser:
    def parse(self) -> TopLevel:
        """Modified to return TopLevel instead of CommandList."""
        top_level = TopLevel()
        
        while self.peek().type != TokenType.EOF:
            # Skip newlines
            while self.match(TokenType.NEWLINE):
                self.advance()
            
            if self.peek().type == TokenType.EOF:
                break
                
            if self._is_function_def():
                func_def = self.parse_function_def()
                top_level.items.append(func_def)
            else:
                cmd_list = self.parse_command_list()
                if cmd_list.and_or_lists:
                    top_level.items.append(cmd_list)
            
            # Skip trailing separators
            while self.match(TokenType.SEMICOLON, TokenType.NEWLINE):
                self.advance()
        
        return top_level
    
    def _is_function_def(self) -> bool:
        """Lookahead to detect function definition."""
        # Implementation as shown in detailed plan
        
    def parse_function_def(self) -> FunctionDef:
        """Parse function definition."""
        # Implementation as shown in detailed plan
```

### Step 5: Function Manager (psh/functions.py)
```python
class FunctionManager:
    """Manages shell function definitions."""
    
    def __init__(self):
        self.functions = {}
    
    def define_function(self, name: str, body: CommandList):
        """Define or redefine a function."""
        # Validation
        if name in ('if', 'then', 'else', 'fi', 'while', 'do', 'done', 'for'):
            raise ValueError(f"Cannot use reserved word '{name}' as function name")
        
        self.functions[name] = Function(name, body)
    
    def get_function(self, name: str) -> Optional[Function]:
        """Retrieve a function definition."""
        return self.functions.get(name)
```

### Step 6: Shell Integration (shell.py)
```python
class Shell:
    def __init__(self):
        # ... existing init ...
        self.function_manager = FunctionManager()
        self.function_stack = []  # Track function calls
    
    def run_command(self, command_string: str):
        """Modified to handle TopLevel AST."""
        tokens = tokenize(command_string)
        tokens = self.alias_manager.expand_aliases(tokens)
        ast = parse(tokens)  # Returns TopLevel now
        
        if isinstance(ast, TopLevel):
            return self.execute_toplevel(ast)
        else:
            # Backward compatibility
            return self.execute_command_list(ast)
    
    def execute_command(self, command: Command):
        """Modified to check for function calls."""
        args = self._expand_arguments(command)
        
        if not args:
            return 0
        
        # NEW: Check for function call before builtins
        func = self.function_manager.get_function(args[0])
        if func:
            return self._execute_function(func, args, command)
        
        # Rest of existing logic...
```

## Testing Strategy

### Parser Tests
```python
def test_function_definition_posix():
    """Test POSIX-style function definition."""
    code = 'greet() { echo "Hello, $1"; }'
    tokens = tokenize(code)
    ast = parse(tokens)
    assert isinstance(ast, TopLevel)
    assert len(ast.items) == 1
    assert isinstance(ast.items[0], FunctionDef)
    assert ast.items[0].name == 'greet'

def test_function_with_execution():
    """Test defining and calling a function."""
    shell = Shell()
    shell.run_command('greet() { echo "Hello, $1"; }')
    output = capture_output(lambda: shell.run_command('greet World'))
    assert output == "Hello, World\n"
```

### Integration Tests
```bash
# Test file: tests/test_functions.py
def test_function_positional_params(shell, capsys):
    """Test function receives positional parameters."""
    shell.run_command('f() { echo "$# args: $@"; }')
    shell.run_command('f a b c')
    captured = capsys.readouterr()
    assert captured.out == "3 args: a b c\n"

def test_function_return_value(shell):
    """Test function return values."""
    shell.run_command('f() { return 42; }')
    exit_code = shell.run_command('f')
    assert exit_code == 42
    shell.run_command('echo $?')
    # Should print 42
```

## Migration Path

1. **Phase 1** (Week 1-2): Basic function definition and execution
   - Parser changes
   - FunctionManager implementation
   - Basic execution without local variables

2. **Phase 2** (Week 3): Integration and testing
   - Builtin support (declare -f, unset -f)
   - Comprehensive test suite
   - Documentation

3. **Phase 3** (Week 4): Advanced features
   - Local variables
   - FUNCNAME support
   - Export functions

## Risk Mitigation

1. **Parser Ambiguity**: Use lookahead to disambiguate
2. **Backward Compatibility**: TopLevel node handles both functions and commands
3. **Performance**: Functions stored in dictionary for O(1) lookup
4. **Memory**: No function persistence, cleared on shell exit

## Success Criteria

1. All bash function syntax forms supported
2. Functions can call other functions (including recursion)
3. Proper parameter handling ($1, $2, $@, $#)
4. Return values work correctly
5. No regression in existing functionality
6. Clear error messages for syntax errors
7. Educational value maintained (code remains readable)

This architecture provides a clean, extensible implementation of shell functions that fits naturally into psh's existing design.