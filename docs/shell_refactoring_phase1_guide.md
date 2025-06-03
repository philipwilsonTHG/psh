# Phase 1 Implementation Guide: Core Infrastructure

## Overview
This guide provides detailed steps for implementing Phase 1 of the shell.py refactoring, focusing on establishing the core infrastructure without breaking any functionality.

## Step 1: Create Directory Structure

```bash
mkdir -p psh/core
mkdir -p psh/executor
mkdir -p psh/expansion
mkdir -p psh/io_redirect
mkdir -p psh/scripting
mkdir -p psh/interactive
mkdir -p psh/utils

# Create __init__.py files
touch psh/core/__init__.py
touch psh/executor/__init__.py
touch psh/expansion/__init__.py
touch psh/io_redirect/__init__.py
touch psh/scripting/__init__.py
touch psh/interactive/__init__.py
touch psh/utils/__init__.py
```

## Step 2: Extract Core Exceptions

### Create `psh/core/exceptions.py`:
```python
"""Core exceptions for shell execution flow control."""

class LoopBreak(Exception):
    """Exception used to implement break statement."""
    def __init__(self, level=1):
        self.level = level
        super().__init__()

class LoopContinue(Exception):
    """Exception used to implement continue statement."""
    def __init__(self, level=1):
        self.level = level
        super().__init__()
```

### Update shell.py imports:
```python
# Replace:
# class LoopBreak(Exception): ...
# class LoopContinue(Exception): ...

# With:
from .core.exceptions import LoopBreak, LoopContinue
```

## Step 3: Create ShellState Class

### Create `psh/core/state.py`:
```python
"""Shell state management."""
import os
import sys
from typing import List, Dict, Optional, Any

class ShellState:
    """Container for shell state that can be shared across components."""
    
    def __init__(self, args=None, script_name=None, debug_ast=False, 
                 debug_tokens=False, norc=False, rcfile=None):
        # Environment and variables
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported)
        
        # Default prompt variables
        self.variables['PS1'] = 'psh$ '
        self.variables['PS2'] = '> '
        
        # Positional parameters and script info
        self.positional_params = args if args else []
        self.script_name = script_name or "psh"
        self.is_script_mode = script_name is not None and script_name != "psh"
        
        # Debug flags
        self.debug_ast = debug_ast
        self.debug_tokens = debug_tokens
        
        # RC file options
        self.norc = norc
        self.rcfile = rcfile
        
        # Execution state
        self.last_exit_code = 0
        self.last_bg_pid = None
        self.foreground_pgid = None
        self.command_number = 0
        
        # History settings
        self.history = []
        self.history_file = os.path.expanduser("~/.psh_history")
        self.max_history_size = 1000
        self.history_index = -1
        self.current_line = ""
        
        # Editor configuration
        self.edit_mode = 'emacs'
        
        # Function call stack
        self.function_stack = []
        
        # Process state
        self._in_forked_child = False
        
        # I/O streams (for backward compatibility)
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stdin = sys.stdin
    
    def get_variable(self, name: str, default: str = '') -> str:
        """Get variable value, checking shell variables first, then environment."""
        return self.variables.get(name, self.env.get(name, default))
    
    def set_variable(self, name: str, value: str):
        """Set a shell variable."""
        self.variables[name] = value
    
    def export_variable(self, name: str, value: str):
        """Export a variable to the environment."""
        self.variables[name] = value
        self.env[name] = value
    
    def get_positional_param(self, index: int) -> str:
        """Get positional parameter by index (1-based)."""
        if 1 <= index <= len(self.positional_params):
            return self.positional_params[index - 1]
        return ''
    
    def get_special_variable(self, name: str) -> str:
        """Get special variable value ($?, $$, $!, etc.)."""
        if name == '?':
            return str(self.last_exit_code)
        elif name == '$':
            return str(os.getpid())
        elif name == '!':
            return str(self.last_bg_pid) if self.last_bg_pid else ''
        elif name == '#':
            return str(len(self.positional_params))
        elif name == '0':
            return self.script_name
        elif name == '@':
            return ' '.join(self.positional_params)
        elif name == '*':
            return ' '.join(self.positional_params)
        elif name.isdigit():
            return self.get_positional_param(int(name))
        return ''
```

## Step 4: Create Component Base Classes

### Create `psh/executor/base.py`:
```python
"""Base classes for executor components."""
from abc import ABC, abstractmethod
from ..core.state import ShellState

class ExecutorComponent(ABC):
    """Base class for all executor components."""
    
    def __init__(self, shell_state: ShellState):
        self.state = shell_state
    
    @abstractmethod
    def execute(self, node):
        """Execute the given AST node."""
        pass
```

### Create `psh/expansion/base.py`:
```python
"""Base classes for expansion components."""
from abc import ABC, abstractmethod
from ..core.state import ShellState

class ExpansionComponent(ABC):
    """Base class for all expansion components."""
    
    def __init__(self, shell_state: ShellState):
        self.state = shell_state
    
    @abstractmethod
    def expand(self, value: str) -> str:
        """Expand the given value."""
        pass
```

## Step 5: Update Shell Class (Minimal Changes)

### Modify shell.py constructor:
```python
class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, 
                 debug_tokens=False, norc=False, rcfile=None):
        # Initialize state
        from .core.state import ShellState
        self.state = ShellState(args, script_name, debug_ast, 
                              debug_tokens, norc, rcfile)
        
        # Create backward compatibility properties
        self._setup_compatibility_properties()
        
        # Initialize managers (existing code)
        self.alias_manager = AliasManager()
        self.function_manager = FunctionManager()
        self.job_manager = JobManager()
        self.builtin_registry = builtin_registry
        self.builtins = {}
        
        # Load history
        self._load_history()
        
        # Set up process group and signals (existing code)
        # ...
    
    def _setup_compatibility_properties(self):
        """Set up properties for backward compatibility."""
        # These will be removed in later phases
        self._state_properties = [
            'env', 'variables', 'positional_params', 'script_name',
            'is_script_mode', 'debug_ast', 'debug_tokens', 'norc', 'rcfile',
            'last_exit_code', 'last_bg_pid', 'foreground_pgid', 'command_number',
            'history', 'history_file', 'max_history_size', 'history_index',
            'current_line', 'edit_mode', 'function_stack', '_in_forked_child',
            'stdout', 'stderr', 'stdin'
        ]
        
    def __getattr__(self, name):
        """Delegate attribute access to state for compatibility."""
        if hasattr(self.state, name):
            return getattr(self.state, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Delegate attribute setting to state for compatibility."""
        if name == 'state' or name == '_state_properties':
            super().__setattr__(name, value)
        elif hasattr(self, '_state_properties') and name in self._state_properties:
            setattr(self.state, name, value)
        else:
            super().__setattr__(name, value)
```

## Step 6: Create Utility Extractors

### Create `psh/utils/ast_formatter.py`:
```python
"""AST formatting utilities for debugging."""
from ..ast_nodes import *

class ASTFormatter:
    """Formats AST nodes for debug output."""
    
    @staticmethod
    def format(node, indent=0):
        """Format AST node for debugging output."""
        spaces = "  " * indent
        
        if isinstance(node, TopLevel):
            result = f"{spaces}TopLevel:\n"
            for item in node.items:
                result += ASTFormatter.format(item, indent + 1)
            return result
        
        # ... (rest of _format_ast logic from shell.py)
```

### Create `psh/utils/token_formatter.py`:
```python
"""Token formatting utilities for debugging."""
from ..tokenizer import Token

class TokenFormatter:
    """Formats token lists for debug output."""
    
    @staticmethod
    def format(tokens):
        """Format token list for debugging output."""
        result = []
        for i, token in enumerate(tokens):
            if isinstance(token, Token):
                result.append(f"  [{i:3d}] {token.type.name:20s} '{token.value}'")
            else:
                result.append(f"  [{i:3d}] {str(token)}")
        return "\n".join(result)
```

## Step 7: Update Tests

### Create test helper:
```python
# tests/helpers/shell_factory.py
from psh.shell import Shell

def create_test_shell(**kwargs):
    """Factory function to create shells for testing."""
    # This allows us to easily update test shell creation later
    return Shell(**kwargs)
```

### Update a sample test:
```python
# Before:
# shell = Shell()

# After:
from .helpers.shell_factory import create_test_shell
shell = create_test_shell()
```

## Validation Steps

1. **Run all tests**:
   ```bash
   python -m pytest tests/
   ```

2. **Verify no functionality changes**:
   ```bash
   # Test interactive mode
   python -m psh
   
   # Test script execution
   python -m psh test_script.sh
   
   # Test command execution
   python -m psh -c "echo hello"
   ```

3. **Check imports**:
   ```bash
   # Ensure no import errors
   python -c "from psh.shell import Shell; Shell()"
   ```

## Next Steps

After Phase 1 is complete and all tests pass:
1. Commit changes with message: "refactor: Phase 1 - Core infrastructure setup"
2. Create PR for review
3. Once merged, proceed to Phase 2 (Expansion System)

## Notes

- This phase focuses on infrastructure without moving functionality
- All tests should continue to pass unchanged
- The compatibility layer ensures existing code works
- Future phases will gradually move functionality to new components