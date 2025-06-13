# Function Inheritance Implementation Guide

## Quick Summary

Functions should be inherited by subshells in psh, matching bash/zsh behavior. Currently, command substitution and process substitution create new Shell instances without copying functions.

## Minimal Implementation (Phase 1)

### 1. Add copy method to FunctionManager

```python
# In psh/functions.py, add to FunctionManager class:

def copy(self) -> 'FunctionManager':
    """Create a shallow copy of all functions.
    
    Note: For now, we share AST nodes between instances since they're
    immutable once created. If we need true isolation later, we can
    implement deep copying.
    """
    new_manager = FunctionManager()
    # Shallow copy is sufficient since we don't modify AST nodes
    new_manager.functions = self.functions.copy()
    return new_manager
```

### 2. Update Shell to accept parent_shell parameter

```python
# In psh/shell.py, modify __init__:

def __init__(self, debug_ast=False, debug_tokens=False, parent_shell=None):
    """Initialize a new shell instance.
    
    Args:
        debug_ast: Enable AST debugging
        debug_tokens: Enable token debugging
        parent_shell: Parent shell to inherit state from
    """
    # Core state management
    self.state = ShellState()
    
    # Component managers
    self.builtin_registry = BuiltinRegistry()
    self.alias_manager = AliasManager()
    self.function_manager = FunctionManager()
    self.job_manager = JobManager(self.state)
    
    # ... rest of existing init code ...
    
    # Inherit from parent if provided
    if parent_shell:
        self.env = parent_shell.env.copy()
        self.variables = parent_shell.variables.copy()
        self.function_manager = parent_shell.function_manager.copy()
        # Note: We don't copy aliases or jobs - those are shell-specific
```

### 3. Update command substitution

```python
# In psh/expansion/command_sub.py, modify expand_command_substitution:

# Change this:
temp_shell = Shell(debug_ast=self.state.debug_ast, debug_tokens=self.state.debug_tokens)
temp_shell.env = self.state.env.copy()
temp_shell.variables = self.state.variables.copy()

# To this:
temp_shell = Shell(
    debug_ast=self.state.debug_ast,
    debug_tokens=self.state.debug_tokens,
    parent_shell=self.shell
)
```

### 4. Update process substitution

```python
# In psh/io_redirect/process_sub.py, modify execute:

# Change this:
temp_shell = Shell()
temp_shell.env = self.state.env.copy()
temp_shell.variables = self.state.variables.copy()

# To this:
temp_shell = Shell(parent_shell=self.shell)
```

### 5. Add reference to shell in expansion components

The expansion components need access to the shell instance. We need to check how they currently access it.

```python
# In psh/expansion/manager.py or wherever ExpansionManager is initialized
# Ensure it has a reference to the shell, not just the state
```

## Testing

### 1. Update existing test

Remove the `@pytest.mark.xfail` decorators from `test_function_command_substitution.py` and verify tests pass.

### 2. Add edge case tests

```python
def test_function_modification_isolation(self, shell, capsys):
    """Test that function modifications in subshells don't affect parent."""
    shell.run_command('''
    greet() {
        echo "Hello"
    }
    ''')
    
    # Modify function in subshell
    shell.run_command('''
    result=$(greet() { echo "Modified"; }; greet)
    echo "Subshell: $result"
    ''')
    
    # Original function should be unchanged
    shell.run_command('greet')
    captured = capsys.readouterr()
    assert "Hello" in captured.out
    assert "Modified" not in captured.out
```

## Phase 2 Considerations

### 1. Deep copying for true isolation

If we need true isolation (subshell function modifications shouldn't affect parent), we'll need to implement AST deep copying:

```python
def _deep_copy_function(self, func: Function) -> Function:
    """Create a deep copy of a function including its AST."""
    # This requires implementing __deepcopy__ on all AST node classes
    # or a custom AST copier
    pass
```

### 2. Performance optimization

- Lazy copying: Only copy functions when they're accessed
- Reference counting: Share AST nodes with copy-on-write semantics

### 3. Other subshell contexts

- Subshells created with `(command)`
- Background jobs with `&`
- Pipelines (may need special handling)

## Implementation Order

1. Implement FunctionManager.copy() method (5 minutes)
2. Update Shell.__init__ to accept parent_shell (10 minutes)
3. Find where ExpansionManager gets access to shell (15 minutes)
4. Update command_sub.py (5 minutes)
5. Update process_sub.py (5 minutes)
6. Run tests and fix any issues (20 minutes)

Total: ~1 hour for basic implementation

## Potential Issues

1. **Circular imports**: May need to be careful about import order
2. **State references**: Ensure all components have proper references
3. **Memory leaks**: Ensure subshells are properly garbage collected
4. **Performance**: Monitor impact of copying functions

## Success Metrics

1. All command substitution tests with functions pass
2. Process substitution works with functions
3. No performance regression in existing tests
4. No memory leaks in long-running shells