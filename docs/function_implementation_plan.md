# Shell Functions Implementation Plan for psh

## Overview

Shell functions are reusable blocks of code that execute in the current shell context (unlike scripts which run in subshells). They are more powerful than aliases as they can contain multiple commands, control structures, and have their own parameters.

## Bash Function Behavior Research

### 1. Definition Syntax

Bash supports two syntaxes for function definition:

```bash
# POSIX style
function_name() {
    commands
}

# Bash style
function function_name {
    commands
}

# Bash also allows
function function_name() {
    commands
}
```

### 2. Function Characteristics

- **Execution Context**: Functions run in the current shell process (no fork)
- **Variable Scope**: Variables are global by default, `local` keyword creates function-local variables
- **Parameters**: Accessed via $1, $2, etc. (like scripts)
- **Return Values**: Via `return n` (0-255) or last command's exit status
- **Output**: Functions can produce stdout/stderr like any command
- **Precedence**: Functions take precedence over external commands but not builtins

### 3. Special Behaviors

```bash
# Functions can be recursive
factorial() {
    if [ $1 -le 1 ]; then
        echo 1
    else
        echo $(( $1 * $(factorial $(( $1 - 1 ))) ))
    fi
}

# Local variables
myfunc() {
    local var="local value"
    echo $var  # prints "local value"
}

# Functions see global variables
global_var="global"
myfunc() {
    echo $global_var  # prints "global"
    global_var="modified"  # modifies global
}

# Special variables
myfunc() {
    echo $FUNCNAME  # function name
    echo $#         # number of arguments
    echo $@         # all arguments
}
```

### 4. Storage and Management

- Functions are stored in shell memory
- `declare -f` lists all functions
- `declare -f name` shows function definition
- `unset -f name` removes a function
- Functions are not inherited by subshells unless exported with `export -f`

## Architectural Design for psh

### 1. Data Structures

```python
# In psh/functions.py
class Function:
    """Represents a shell function definition."""
    def __init__(self, name: str, body: CommandList, params: List[str] = None):
        self.name = name
        self.body = body  # AST node
        self.params = params  # For documentation, bash doesn't use these
        self.source_location = None  # File:line where defined

class FunctionManager:
    """Manages shell functions."""
    def __init__(self):
        self.functions: Dict[str, Function] = {}
    
    def define_function(self, name: str, body: CommandList) -> None:
        """Define or redefine a function."""
        if self._is_reserved_word(name):
            raise ValueError(f"Cannot use reserved word '{name}' as function name")
        self.functions[name] = Function(name, body)
    
    def get_function(self, name: str) -> Optional[Function]:
        """Get a function by name."""
        return self.functions.get(name)
    
    def undefine_function(self, name: str) -> bool:
        """Remove a function. Returns True if removed."""
        return self.functions.pop(name, None) is not None
    
    def list_functions(self) -> List[Tuple[str, Function]]:
        """List all defined functions."""
        return sorted(self.functions.items())
```

### 2. Grammar Extensions

Add to the parser grammar:

```
# Extended grammar
item         → function_def | command_list
function_def → WORD '(' ')' compound_command
             | 'function' WORD compound_command
             | 'function' WORD '(' ')' compound_command
compound_command → '{' command_list '}'

# Modified command to check for function calls
simple_command → WORD+ redirect* [AMPERSAND]
# During execution, check if WORD is a function name
```

### 3. AST Node Addition

```python
# In ast_nodes.py
class FunctionDef:
    """Function definition node."""
    def __init__(self, name: str, body: CommandList):
        self.name = name
        self.body = body
```

### 4. Tokenizer Updates

Add tokens for function syntax:
- Recognize `function` as a keyword
- Already have `(` and `)` for subshells
- Already have `{` and `}` for brace expansion (will dual-purpose)

### 5. Parser Modifications

```python
# In parser.py
def parse_item(self):
    """Parse a top-level item (function def or command list)."""
    if self._check_function_def():
        return self.parse_function_def()
    else:
        return self.parse_command_list()

def parse_function_def(self):
    """Parse function definition."""
    name = None
    
    # Handle 'function' keyword if present
    if self.current_token and self.current_token.value == 'function':
        self.consume('function')
        if not self.current_token or self.current_token.type != TokenType.WORD:
            raise ParseError("Expected function name")
        name = self.current_token.value
        self.consume(TokenType.WORD)
        
        # Optional parentheses
        if self.current_token and self.current_token.value == '(':
            self.consume('(')
            self.consume(')')
    else:
        # POSIX style: name()
        if not self.current_token or self.current_token.type != TokenType.WORD:
            raise ParseError("Expected function name")
        name = self.current_token.value
        self.consume(TokenType.WORD)
        self.consume('(')
        self.consume(')')
    
    # Parse body
    body = self.parse_compound_command()
    return FunctionDef(name, body)
```

### 6. Execution Changes

```python
# In shell.py
class Shell:
    def __init__(self):
        # ... existing init ...
        self.function_manager = FunctionManager()
        self.function_call_stack = []  # Track nested function calls
        
    def execute_command(self, command: Command):
        """Execute a single command."""
        # ... existing expansions ...
        
        if not args:
            return 0
            
        # Check for function call BEFORE builtin check
        func = self.function_manager.get_function(args[0])
        if func:
            return self._execute_function(func, args)
        
        # ... rest of existing logic ...
    
    def _execute_function(self, func: Function, args: List[str]) -> int:
        """Execute a function with given arguments."""
        # Save current positional parameters
        saved_params = self.positional_params
        saved_dollar_at = self.variables.get('@', '')
        saved_dollar_star = self.variables.get('*', '')
        saved_dollar_hash = self.variables.get('#', '')
        
        # Set up function environment
        self.positional_params = args[1:]  # args[0] is function name
        self.function_call_stack.append(func.name)
        
        try:
            # Execute function body
            exit_code = self.execute_command_list(func.body)
            return exit_code
        finally:
            # Restore environment
            self.function_call_stack.pop()
            self.positional_params = saved_params
```

### 7. Built-in Commands

Add function-related builtins:

```python
def _builtin_declare(self, args):
    """Declare variables and functions."""
    if '-f' in args:
        if len(args) == 2:  # declare -f
            # List all functions
            for name, func in self.function_manager.list_functions():
                self._print_function_definition(name, func)
        else:  # declare -f name
            name = args[2]
            func = self.function_manager.get_function(name)
            if func:
                self._print_function_definition(name, func)
            else:
                print(f"bash: declare: {name}: not found", file=sys.stderr)
                return 1
    return 0

def _builtin_unset(self, args):
    """Enhanced to handle functions with -f flag."""
    if '-f' in args:
        # Remove functions
        exit_code = 0
        for arg in args:
            if arg != '-f':
                if not self.function_manager.undefine_function(arg):
                    exit_code = 1
        return exit_code
    # ... existing variable logic ...
```

### 8. Local Variables (Phase 2)

```python
class Shell:
    def __init__(self):
        # ... existing init ...
        self.variable_scopes = [{}]  # Stack of variable scopes
    
    def _builtin_local(self, args):
        """Create function-local variables."""
        if not self.function_call_stack:
            print("local: can only be used in a function", file=sys.stderr)
            return 1
        
        for arg in args[1:]:
            if '=' in arg:
                name, value = arg.split('=', 1)
                self.variable_scopes[-1][name] = value
            else:
                self.variable_scopes[-1][arg] = ''
        return 0
```

## Implementation Phases

### Phase 1: Basic Functions (Core functionality)
1. Add FunctionDef AST node
2. Extend tokenizer for `function` keyword
3. Implement function definition parsing
4. Add FunctionManager class
5. Integrate function execution into command execution
6. Add `declare -f` builtin support
7. Add `unset -f` support
8. Write comprehensive tests

### Phase 2: Advanced Features
1. Local variables with `local` builtin
2. FUNCNAME special variable
3. Export functions with `export -f`
4. Function recursion depth limiting
5. Function tracing/debugging support

### Phase 3: Future Enhancements
1. Function autoloading
2. Function libraries
3. Anonymous functions
4. Function profiling

## Testing Strategy

1. **Basic Definition and Execution**
   ```bash
   # Define and call
   greet() { echo "Hello, $1!"; }
   greet World  # Should output: Hello, World!
   ```

2. **Parameter Handling**
   ```bash
   # Positional parameters
   showargs() { echo "Count: $#, Args: $@"; }
   showargs a b c  # Should output: Count: 3, Args: a b c
   ```

3. **Return Values**
   ```bash
   # Return and exit status
   myfunc() { return 42; }
   myfunc
   echo $?  # Should output: 42
   ```

4. **Nested Functions**
   ```bash
   # Function calling function
   outer() { echo "outer"; inner; }
   inner() { echo "inner"; }
   outer  # Should output: outer\ninner
   ```

5. **Recursion**
   ```bash
   # Recursive factorial
   fact() {
       if [ $1 -le 1 ]; then echo 1; 
       else echo $(( $1 * $(fact $(( $1 - 1 ))) )); fi
   }
   fact 5  # Should output: 120
   ```

## Integration Considerations

1. **Command Precedence**: Function > External command (but not builtin)
2. **Alias Interaction**: Aliases are expanded before function names are resolved
3. **Completion**: Tab completion should include function names
4. **History**: Function definitions should be saved in history
5. **Source**: Functions defined in sourced files should persist

## Example Implementation Timeline

- Week 1: Parser and AST changes
- Week 2: FunctionManager and basic execution
- Week 3: Builtin integration and testing
- Week 4: Advanced features (local variables, special vars)

This design provides a solid foundation for implementing shell functions in psh while maintaining the educational clarity of the codebase.