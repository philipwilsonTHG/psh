# Alias Implementation Summary for PSH

## Quick Overview

Aliases in shells are text substitutions that replace command names with their definitions before execution. For example:
- `alias ll='ls -l'` creates an alias where `ll` expands to `ls -l`
- `alias grep='grep --color=auto'` adds default options to grep

## Key Design Decisions

### 1. **Where to Implement Alias Expansion**
- **After tokenization, before parsing** (between lines 610-611 in shell.py)
- This is cleaner than bash's approach of text substitution before tokenization
- Allows us to work with structured tokens rather than raw strings

### 2. **Core Components**

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Command   │────▶│  Tokenizer   │────▶│   Alias     │
│   String    │     │              │     │  Expander   │
└─────────────┘     └──────────────┘     └─────────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Executor   │◀────│    Parser    │◀────│  Expanded   │
│             │     │              │     │   Tokens    │
└─────────────┘     └──────────────┘     └─────────────┘
```

### 3. **Key Features to Implement**

1. **Basic Aliases**: `alias name='value'`
2. **Chained Aliases**: Aliases can reference other aliases
3. **Recursive Prevention**: `alias ls='ls --color'` won't loop infinitely
4. **Trailing Space**: `alias sudo='sudo '` enables expansion of next word
5. **Command Position Only**: Only expand aliases in command position (after pipes, semicolons, etc.)

### 4. **Implementation Phases**

**Phase 1 - Basic (2-3 hours)**
- Create AliasManager class
- Implement alias/unalias builtins
- Simple command-position expansion
- Basic tests

**Phase 2 - Advanced (2-3 hours)**
- Recursive expansion with loop detection
- Trailing space handling
- Position-aware expansion
- Integration tests

**Phase 3 - Polish (1-2 hours)**
- Alias persistence (~/.psh_aliases)
- Performance optimization
- Documentation

## Code Integration Points

### 1. **In shell.py**
```python
def run_command(self, command_string: str, add_to_history=True):
    # ... existing code ...
    try:
        tokens = tokenize(command_string)
        # NEW: Expand aliases here
        tokens = self.alias_manager.expand_aliases(tokens)
        ast = parse(tokens)
        # ... rest of execution ...
```

### 2. **New file: psh/aliases.py**
```python
class AliasManager:
    def __init__(self):
        self.aliases = {}
        self.expanding = set()  # Prevent infinite recursion
    
    def expand_aliases(self, tokens: List[Token]) -> List[Token]:
        # Main expansion logic
```

### 3. **New builtins in shell.py**
```python
self.builtins['alias'] = self._builtin_alias
self.builtins['unalias'] = self._builtin_unalias
```

## Testing Examples

```bash
# Basic usage
alias ll='ls -l'
ll /tmp                    # → ls -l /tmp

# Chained aliases
alias la='ls -a'
alias ll='la -l'
ll                        # → ls -a -l

# Options
alias grep='grep --color=auto'
grep pattern file         # → grep --color=auto pattern file

# Trailing space
alias sudo='sudo '
sudo ll                   # → sudo ls -l (ll is expanded)

# Show all aliases
alias

# Show specific alias
alias ll

# Remove alias
unalias ll
```

## Why This Design?

1. **Clean Architecture**: Works with tokens instead of raw text
2. **Predictable**: Expansion happens at a well-defined point
3. **Efficient**: No need to re-tokenize entire commands
4. **Testable**: Each component can be tested independently
5. **Compatible**: Behaves like bash/zsh from user perspective

## Next Steps

1. Review the architectural plan
2. Create feature branch for implementation
3. Start with Phase 1 (basic alias support)
4. Iterate through phases with tests at each step