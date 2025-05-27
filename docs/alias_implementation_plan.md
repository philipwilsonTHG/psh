# Alias Implementation Plan for PSH

## Overview

Shell aliases are simple text substitutions that occur early in command processing. When the shell sees a command name that matches an alias, it replaces that command with the alias value before further processing.

## How Aliases Work in Bash/Traditional Shells

### 1. Definition and Storage
- Aliases are stored as key-value pairs (alias name → replacement text)
- Defined using: `alias name='replacement'`
- Listed using: `alias` (shows all) or `alias name` (shows specific)
- Removed using: `unalias name` or `unalias -a` (remove all)

### 2. Expansion Timing
- Alias expansion happens **after** the command line is read but **before** parsing
- Only the first word of a simple command is checked for aliases
- Aliases are expanded in interactive shells and when `expand_aliases` is set

### 3. Examples
```bash
# Simple alias
alias ll='ls -la'
ll              # Expands to: ls -la

# Alias with arguments
alias grep='grep --color=auto'
grep pattern    # Expands to: grep --color=auto pattern

# Chained aliases
alias la='ls -a'
alias ll='la -l'
ll              # Expands to: ls -a -l
```

### 4. Recursive Expansion Prevention
- A word that is identical to an alias being expanded is not expanded a second time
- This prevents infinite loops: `alias ls='ls -la'` works correctly

### 5. Special Cases
- Trailing space in alias value causes next word to be checked for alias expansion
- Aliases cannot contain '=' or shell metacharacters in the name
- Aliases are not expanded when quoted

## Architectural Design for PSH

### 1. Storage Layer

Create a new module `psh/aliases.py`:

```python
class AliasManager:
    def __init__(self):
        self.aliases = {}  # name -> value mapping
        self.expanding = set()  # Track aliases being expanded
    
    def define_alias(self, name: str, value: str) -> None:
        """Define or update an alias."""
        
    def undefine_alias(self, name: str) -> bool:
        """Remove an alias. Returns True if existed."""
        
    def get_alias(self, name: str) -> Optional[str]:
        """Get alias value if exists."""
        
    def list_aliases(self) -> List[Tuple[str, str]]:
        """Return all aliases as (name, value) pairs."""
        
    def expand_aliases(self, tokens: List[Token]) -> List[Token]:
        """Expand aliases in token list."""
```

### 2. Integration Points

#### A. Shell Initialization
Add alias manager to Shell class:
```python
class Shell:
    def __init__(self):
        # ... existing init ...
        self.alias_manager = AliasManager()
        self.builtins['alias'] = self._builtin_alias
        self.builtins['unalias'] = self._builtin_unalias
```

#### B. Command Processing Pipeline
Current pipeline:
1. Read input
2. Tokenize
3. Parse
4. Execute

New pipeline:
1. Read input
2. Tokenize
3. **Expand aliases** ← New step
4. Parse
5. Execute

#### C. Alias Expansion Algorithm

```python
def expand_aliases(self, tokens: List[Token]) -> List[Token]:
    """Expand aliases in token stream."""
    result = []
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        
        # Only expand WORD tokens at command position
        if (token.type == TokenType.WORD and 
            self._is_command_position(result) and
            token.value not in self.expanding):
            
            alias_value = self.aliases.get(token.value)
            if alias_value:
                # Prevent recursive expansion
                self.expanding.add(token.value)
                
                # Tokenize the alias value
                alias_tokens = tokenize(alias_value)
                # Remove EOF token
                alias_tokens = [t for t in alias_tokens if t.type != TokenType.EOF]
                
                # Recursively expand aliases in replacement
                expanded = self.expand_aliases(alias_tokens)
                
                # Check for trailing space (enables next word expansion)
                check_next = alias_value.endswith(' ')
                
                self.expanding.remove(token.value)
                
                result.extend(expanded)
                i += 1
                
                # If trailing space, continue expansion
                if check_next and i < len(tokens):
                    continue
            else:
                result.append(token)
                i += 1
        else:
            result.append(token)
            i += 1
    
    return result

def _is_command_position(self, tokens: List[Token]) -> bool:
    """Check if current position is a command position."""
    # Command position is:
    # - Start of input
    # - After pipe, semicolon, &&, ||, &
    # - After opening parenthesis (when we add subshells)
    
    if not tokens:
        return True
    
    last_token = tokens[-1]
    return last_token.type in (
        TokenType.PIPE, 
        TokenType.SEMICOLON,
        TokenType.AND_AND,
        TokenType.OR_OR,
        TokenType.AMPERSAND
    )
```

### 3. Built-in Commands

#### `alias` command
```python
def _builtin_alias(self, args: List[str]) -> int:
    if len(args) == 1:
        # No arguments - list all aliases
        for name, value in sorted(self.alias_manager.list_aliases()):
            print(f"alias {name}='{value}'")
        return 0
    
    for arg in args[1:]:
        if '=' in arg:
            # Define alias
            name, value = arg.split('=', 1)
            # Remove quotes if present
            if value.startswith(("'", '"')) and value.endswith(value[0]):
                value = value[1:-1]
            self.alias_manager.define_alias(name, value)
        else:
            # Show specific alias
            value = self.alias_manager.get_alias(arg)
            if value:
                print(f"alias {arg}='{value}'")
            else:
                print(f"psh: alias: {arg}: not found", file=sys.stderr)
                return 1
    
    return 0
```

#### `unalias` command
```python
def _builtin_unalias(self, args: List[str]) -> int:
    if len(args) == 1:
        print("unalias: usage: unalias [-a] name [name ...]", file=sys.stderr)
        return 1
    
    if args[1] == '-a':
        # Remove all aliases
        self.alias_manager.aliases.clear()
        return 0
    
    exit_code = 0
    for name in args[1:]:
        if not self.alias_manager.undefine_alias(name):
            print(f"psh: unalias: {name}: not found", file=sys.stderr)
            exit_code = 1
    
    return exit_code
```

### 4. Persistence

Add methods to save/load aliases:
```python
def save_aliases(self, filename: str):
    """Save aliases to file."""
    with open(filename, 'w') as f:
        for name, value in sorted(self.aliases.items()):
            f.write(f"alias {name}='{value}'\n")

def load_aliases(self, filename: str):
    """Load aliases from file."""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('alias '):
                    self.run_command(line)
```

Integration with `.pshrc`:
- Load from `~/.psh_aliases` on startup
- Save aliases when defined interactively (optional)

### 5. Testing Strategy

1. **Unit tests** (`tests/test_aliases.py`):
   - Basic alias definition/undefined
   - Alias expansion in various positions
   - Recursive expansion prevention
   - Trailing space handling
   - Quote handling

2. **Integration tests**:
   - Aliases with pipes, redirections
   - Aliases in scripts vs interactive
   - Alias command line parsing
   - Error cases

3. **Test cases**:
   ```bash
   # Basic
   alias ll='ls -l'
   ll /tmp
   
   # Chained
   alias la='ls -a'
   alias ll='la -l'
   
   # With special chars
   alias grep='grep --color=auto'
   alias l.='ls -d .* --color=auto'
   
   # Trailing space
   alias sudo='sudo '  # Allows sudo ll to expand ll
   
   # Prevention of infinite recursion
   alias ls='ls --color'
   ```

### 6. Implementation Order

1. **Phase 1**: Basic alias support
   - AliasManager class
   - Simple alias expansion (command position only)
   - alias/unalias builtins
   - Basic tests

2. **Phase 2**: Advanced features
   - Trailing space handling
   - Recursive expansion with loop prevention
   - Position-aware expansion
   - Quote handling

3. **Phase 3**: Polish
   - Persistence
   - Performance optimization
   - Error messages
   - Documentation

### 7. Edge Cases to Handle

1. **Alias names**:
   - Cannot contain '=', '/', or shell metacharacters
   - Cannot be shell keywords (if, then, etc.)
   - Should validate alias names

2. **Expansion contexts**:
   - Not expanded in non-command positions
   - Not expanded when quoted
   - Not expanded in here documents

3. **Special aliases**:
   - Aliases that end with space
   - Aliases that contain quotes
   - Multi-line aliases (if supported)

### 8. Performance Considerations

- Use dict for O(1) alias lookup
- Cache tokenization results for frequently used aliases
- Minimize re-tokenization during expansion
- Consider lazy expansion for complex aliases

### 9. Compatibility Notes

- Bash expands aliases before parsing, we'll do it after tokenization
- This is cleaner and avoids re-tokenizing the entire command
- Will maintain behavioral compatibility while being more efficient

## Summary

This implementation will provide full alias support compatible with traditional shells while integrating cleanly with psh's architecture. The key insight is to perform alias expansion on the token stream between tokenization and parsing, which is cleaner than bash's approach of text substitution before tokenization.