# Function Inheritance in Subshells - Implementation Plan

## Overview

Currently, psh creates new shell instances for command substitution without inheriting function definitions from the parent shell. This differs from bash/zsh behavior where functions are inherited by subshells. This document outlines a plan to implement function inheritance.

## Current Architecture

### Problem Areas

1. **Command Substitution** (`psh/expansion/command_sub.py`):
   ```python
   temp_shell = Shell(debug_ast=self.state.debug_ast, debug_tokens=self.state.debug_tokens)
   temp_shell.env = self.state.env.copy()
   temp_shell.variables = self.state.variables.copy()
   # Functions are NOT copied
   ```

2. **Process Substitution** (`psh/io_redirect/process_sub.py`):
   - Similar issue - creates new shell without function inheritance

3. **Pipeline Execution** (`psh/executor/pipeline.py`):
   - Each pipeline component may need access to parent functions

4. **Background Jobs** (`psh/job_control.py`):
   - Background processes should inherit functions from parent

## Implementation Plan

### Phase 1: Add Function Copying to Subshells

1. **Update Shell Constructor**
   - Add optional `parent_shell` parameter to Shell.__init__()
   - Copy functions when parent_shell is provided
   
2. **Modify Command Substitution**
   ```python
   # In command_sub.py
   temp_shell = Shell(
       parent_shell=self.shell,  # Pass parent reference
       debug_ast=self.state.debug_ast,
       debug_tokens=self.state.debug_tokens
   )
   ```

3. **Update Function Manager**
   - Add `copy()` method to FunctionManager to create deep copies
   - Ensure AST nodes are properly copied (not just references)

### Phase 2: Handle Different Subshell Types

1. **Command Substitution** - Full function inheritance
2. **Process Substitution** - Full function inheritance  
3. **Subshells `()` ** - Full function inheritance
4. **Background Jobs `&`** - Full function inheritance
5. **Pipelines** - Special handling (see Phase 3)

### Phase 3: Pipeline Function Inheritance

Pipelines are tricky because each component runs in a separate process:

1. **Analyze Current Pipeline Implementation**
   - How are builtins handled in pipelines?
   - When do we fork vs. create new shells?

2. **Implement Function Serialization**
   - For external commands in pipelines, we may need to serialize functions
   - Consider using pickle or custom AST serialization

3. **Update Pipeline Executor**
   - Pass function definitions to child processes
   - Handle builtin vs. external command cases differently

### Phase 4: Optimize Performance

1. **Lazy Copying**
   - Only copy functions when actually needed
   - Use copy-on-write semantics where possible

2. **Function Cache**
   - Cache parsed function ASTs to avoid re-parsing
   - Share immutable AST nodes between shells

3. **Memory Management**
   - Ensure proper cleanup of copied functions
   - Avoid memory leaks in long-running shells

## Detailed Implementation Steps

### Step 1: Extend FunctionManager

```python
# In psh/functions.py
class FunctionManager:
    def copy(self) -> 'FunctionManager':
        """Create a deep copy of all functions."""
        new_manager = FunctionManager()
        for name, func_def in self.functions.items():
            # Deep copy the AST node
            new_manager.functions[name] = self._deep_copy_ast(func_def)
        return new_manager
    
    def _deep_copy_ast(self, ast_node):
        """Deep copy an AST node."""
        # Implementation depends on AST structure
        pass
```

### Step 2: Update Shell Constructor

```python
# In psh/shell.py
class Shell:
    def __init__(self, parent_shell=None, **kwargs):
        # ... existing init code ...
        
        if parent_shell:
            # Inherit from parent
            self.env = parent_shell.env.copy()
            self.variables = parent_shell.variables.copy()
            self.function_manager = parent_shell.function_manager.copy()
            # Copy other relevant state
        else:
            # Fresh initialization
            self.function_manager = FunctionManager()
```

### Step 3: Update Command Substitution

```python
# In psh/expansion/command_sub.py
def expand_command_substitution(self, command: str) -> str:
    # Create subshell with parent reference
    temp_shell = Shell(parent_shell=self.shell)
    # ... rest of implementation
```

### Step 4: Add Tests

Create comprehensive tests in `tests/test_function_inheritance.py`:

1. Test command substitution with functions
2. Test nested command substitutions
3. Test process substitution with functions
4. Test background jobs with functions
5. Test pipelines with functions
6. Test function modifications in subshells don't affect parent
7. Test performance with many functions

## Potential Challenges

1. **AST Deep Copying**
   - AST nodes may have complex references
   - Need to ensure proper copying without breaking functionality

2. **Performance Impact**
   - Copying functions for every subshell could be expensive
   - Need benchmarking and optimization

3. **Memory Usage**
   - Many subshells with large functions could use significant memory
   - Consider reference counting or garbage collection

4. **Serialization for Forked Processes**
   - External commands in pipelines run in separate processes
   - May need to serialize/deserialize function definitions

## Testing Strategy

1. **Unit Tests**
   - Test FunctionManager.copy() method
   - Test Shell inheritance behavior
   - Test each subshell type

2. **Integration Tests**
   - Test complex scenarios with nested functions
   - Test recursive functions in subshells
   - Test function modifications in subshells

3. **Performance Tests**
   - Measure overhead of function copying
   - Test with many functions
   - Test deeply nested subshells

4. **Compatibility Tests**
   - Compare behavior with bash/zsh
   - Ensure POSIX compliance where applicable

## Success Criteria

1. All function command substitution tests pass
2. Functions work in all subshell contexts
3. No significant performance regression
4. Memory usage remains reasonable
5. Existing tests continue to pass

## Alternative Approaches Considered

1. **Shared Function Storage**
   - Use a global function store with reference counting
   - More complex but potentially more efficient

2. **Lazy Function Loading**
   - Only copy functions when they're actually called
   - Requires more complex tracking

3. **Parent Shell Reference**
   - Keep reference to parent shell instead of copying
   - Simpler but could cause issues with shell lifetime

## Recommendation

Start with the straightforward approach of copying functions to subshells. This matches bash/zsh semantics and is easier to reason about. Optimize later if performance becomes an issue.

## Timeline Estimate

- Phase 1: 2-3 hours (basic function copying)
- Phase 2: 2-3 hours (different subshell types)
- Phase 3: 3-4 hours (pipeline handling)
- Phase 4: 2-3 hours (optimization)
- Testing: 2-3 hours

Total: ~12-16 hours of development time