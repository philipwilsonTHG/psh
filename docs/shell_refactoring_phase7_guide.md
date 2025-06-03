# Phase 7 Implementation Guide: Final Integration and Cleanup

## Overview
Phase 7 is the final phase of the shell.py refactoring, focusing on completing the transformation of shell.py into a clean orchestrator. This phase involves removing redundant delegation methods, final cleanup of remaining logic, and ensuring all components work together seamlessly.

## Current State Analysis

### Refactoring Progress
- **Original size**: 2,712 lines
- **Current size**: 1,432 lines (47% reduction)
- **Target size**: ~300-400 lines

### Completed Phases
1. ✅ Phase 1: Core Infrastructure
2. ✅ Phase 2: Expansion System  
3. ✅ Phase 3: I/O Redirection
4. ✅ Phase 4: Executor Components
5. ✅ Phase 5: Script Handling
6. ✅ Phase 6: Interactive Features (pending commit)

### Remaining in shell.py
1. **Delegation Methods** (~32 lines) - Can be removed
2. **Execution Logic** (~951 lines) - Already exists in executor/ but not fully removed
3. **Utility Methods** (~50 lines) - Should move to utils/
4. **Process Substitution** (~20 lines) - Should move to io_redirect/
5. **Redundant Imports** - Need cleanup

## Step 1: Complete Phase 6

### Commit the interactive refactoring:
```bash
git add psh/interactive/
git add psh/shell.py
git commit -m "feat: Complete Phase 6 shell refactoring - Interactive features extraction"
```

## Step 2: Remove Redundant Delegation Methods

### Methods to remove from shell.py:
```python
# These methods now just delegate and can be removed:
def _expand_string_variables(self, s):
    return self.expansion_manager.expand_string_variables(s)

def _expand_variable(self, var_name):
    return self.expansion_manager.expand_variable(var_name)

def _expand_tilde(self, path):
    return self.expansion_manager.expand_tilde(path)

def _execute_command_substitution(self, command_str):
    return self.expansion_manager.execute_command_substitution(command_str)

def _execute_arithmetic_expansion(self, expr):
    return self.expansion_manager.execute_arithmetic_expansion(expr)

# Script delegation methods:
def _parse_shebang(self, script_path):
    return self.script_manager.shebang_handler.parse_shebang(script_path)

def _should_execute_with_shebang(self, script_path):
    return self.script_manager.shebang_handler.should_execute_with_shebang(script_path)

def _is_binary_file(self, file_path):
    return self.script_manager.validator.is_binary_file(file_path)

def _validate_script_file(self, script_path):
    return self.script_manager.validator.validate_script_file(script_path)

# Interactive delegation methods:
def _load_history(self):
    self.interactive_manager.load_history()

def _save_history(self):
    self.interactive_manager.save_history()

def _add_to_history(self, command):
    self.interactive_manager.history_manager.add_to_history(command)

def _handle_sigint(self, signum, frame):
    self.interactive_manager.signal_manager._handle_sigint(signum, frame)

def _handle_sigchld(self, signum, frame):
    self.interactive_manager.signal_manager._handle_sigchld(signum, frame)

# Formatting delegation methods:
def _format_ast(self, node):
    return format_ast(node)

def _format_tokens(self, tokens):
    return format_tokens(tokens)
```

### Update all callers:
- Search for each removed method and update to call the manager directly
- Example: `self._expand_variable(name)` → `self.expansion_manager.expand_variable(name)`

## Step 3: Extract Remaining Execution Logic

### Move to executor/base.py:
```python
class ExecutorManager:
    """Already exists, but add remaining methods"""
    
    def expand_arguments(self, command: Command) -> Command:
        """Move _expand_arguments logic here"""
        # This is a complex method that handles all argument expansions
        # Move the entire implementation from shell.py
        pass
    
    def handle_variable_assignment(self, parts: List[str]) -> int:
        """Move _handle_variable_assignment logic here"""
        # Variable assignment logic
        pass
```

### Move to executor/command.py:
```python
class CommandExecutor:
    """Already exists, enhance with remaining logic"""
    
    def setup_builtin_redirections(self, builtin_name: str, 
                                  redirections: List[Redirection]) -> tuple:
        """Move _setup_builtin_redirections logic here"""
        pass
    
    def restore_builtin_redirections(self, saved_fds: tuple) -> None:
        """Move _restore_builtin_redirections logic here"""
        pass
    
    def execute_builtin(self, builtin_name: str, args: List[str],
                       redirections: List[Redirection]) -> int:
        """Move _execute_builtin logic here"""
        pass
    
    def execute_external(self, cmd_path: str, args: List[str],
                        redirections: List[Redirection], background: bool) -> int:
        """Move _execute_external logic here"""
        pass
```

## Step 4: Extract Utility Functions

### Create psh/utils/file_tests.py:
```python
"""File test utilities."""
import os
import stat
from typing import Optional

def file_older_than(file1: str, file2: str) -> bool:
    """Check if file1 is older than file2."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        return stat1.st_mtime < stat2.st_mtime
    except OSError:
        return False

def files_same(file1: str, file2: str) -> bool:
    """Check if two files are the same (by inode)."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        return (stat1.st_dev == stat2.st_dev and 
                stat1.st_ino == stat2.st_ino)
    except OSError:
        return False
```

## Step 5: Move Process Substitution Helpers

### Move to io_redirect/process_sub.py:
```python
class ProcessSubstitutionManager:
    """Already exists, add these methods"""
    
    def setup_process_substitutions(self, command: Command) -> Dict[str, str]:
        """Setup process substitutions for a command."""
        # Move implementation from shell.py
        pass
    
    def cleanup_process_substitutions(self, subst_map: Dict[str, str]) -> None:
        """Clean up process substitution fifos."""
        # Move implementation from shell.py
        pass
```

## Step 6: Update Shell Class Structure

### Final shell.py structure:
```python
#!/usr/bin/env python3
"""Python Shell (psh) - Main Shell Class

This module provides the main Shell class that orchestrates all shell
functionality through various managers and components.
"""

import os
import sys
from typing import List, Optional, Dict, Any

# Core imports
from .core.state import ShellState
from .core.exceptions import ShellError, ExitShell

# Component managers
from .expansion.manager import ExpansionManager
from .io_redirect.manager import IOManager
from .executor.base import ExecutorManager
from .scripting.base import ScriptManager
from .interactive.base import InteractiveManager

# Direct component imports
from .alias_manager import AliasManager
from .function_manager import FunctionManager
from .job_control import JobManager
from .builtin_registry import BuiltinRegistry

# Parser imports
from .tokenizer import tokenize
from .parser import parse, ParseError
from .token_transformer import transform_tokens


class Shell:
    """Main shell orchestrator.
    
    The Shell class coordinates all shell functionality through specialized
    managers. It serves as the main entry point for command execution and
    delegates actual work to appropriate components.
    """
    
    def __init__(self, debug_ast=False, debug_tokens=False, is_script_mode=False,
                 norc=False, rcfile=None):
        """Initialize the shell with all component managers."""
        # Core state
        self.state = ShellState(
            debug_ast=debug_ast,
            debug_tokens=debug_tokens,
            is_script_mode=is_script_mode,
            norc=norc,
            rcfile=rcfile
        )
        
        # Initialize registries
        self.builtin_registry = BuiltinRegistry()
        
        # Initialize component managers
        self.alias_manager = AliasManager()
        self.function_manager = FunctionManager()
        self.job_manager = JobManager(self)
        
        # Initialize subsystem managers
        self.expansion_manager = ExpansionManager(self)
        self.io_manager = IOManager(self)
        self.executor_manager = ExecutorManager(self)
        self.script_manager = ScriptManager(self)
        self.interactive_manager = InteractiveManager(self)
        
        # Set up signal handlers
        self.interactive_manager.signal_manager.setup_signal_handlers()
        
        # Load RC file for interactive shells
        is_interactive = getattr(self, '_force_interactive', sys.stdin.isatty())
        if not self.state.is_script_mode and is_interactive and not self.state.norc:
            self._load_rc_file()
        
        # Load command history for interactive mode
        if not self.state.is_script_mode and is_interactive:
            self.interactive_manager.load_history()
    
    def run_command(self, command_string: str, add_to_history: bool = True) -> int:
        """Execute a command string and return its exit code.
        
        This is the main entry point for command execution. It handles the
        complete pipeline from parsing to execution.
        
        Args:
            command_string: The command string to execute
            add_to_history: Whether to add to command history
            
        Returns:
            Exit code of the command
        """
        if not command_string.strip():
            return 0
        
        # Add to history if requested
        if add_to_history and not self.state.is_script_mode:
            self.interactive_manager.history_manager.add_to_history(command_string)
        
        try:
            # Tokenize
            tokens = tokenize(command_string)
            
            # Debug tokens if requested
            if self.state.debug_tokens:
                from .utils.token_formatter import format_tokens
                print(f"Tokens: {format_tokens(tokens)}")
            
            # Expand aliases
            tokens = self.alias_manager.expand_aliases(tokens)
            
            # Transform tokens (handle special operators)
            tokens = transform_tokens(tokens)
            
            # Parse
            ast = parse(tokens)
            
            # Debug AST if requested
            if self.state.debug_ast:
                from .utils.ast_formatter import format_ast
                print(f"AST: {format_ast(ast)}")
            
            # Execute
            return self.executor_manager.execute(ast)
            
        except ParseError as e:
            print(f"psh: {e}", file=sys.stderr)
            self.state.last_exit_code = 2
            return 2
        except ExitShell as e:
            sys.exit(e.code)
        except KeyboardInterrupt:
            print("^C")
            self.state.last_exit_code = 130
            return 130
        except Exception as e:
            print(f"psh: {e}", file=sys.stderr)
            self.state.last_exit_code = 1
            return 1
    
    def run_script(self, script_path: str, args: List[str]) -> int:
        """Execute a script file.
        
        Args:
            script_path: Path to the script file
            args: Arguments to pass to the script
            
        Returns:
            Exit code of the script
        """
        return self.script_manager.run_script(script_path, args)
    
    def interactive_loop(self):
        """Run the interactive shell loop."""
        return self.interactive_manager.run_interactive_loop()
    
    def set_positional_params(self, params: List[str]):
        """Set positional parameters ($1, $2, etc.)."""
        self.state.positional_params = params
    
    def _load_rc_file(self):
        """Load the shell RC file."""
        rc_path = self.script_manager.rc_loader.get_rc_path(
            self.state.rcfile,
            self.state.norc
        )
        if rc_path:
            self.script_manager.rc_loader.load_rc_file(rc_path, self)
```

## Step 7: Update Component Dependencies

### Update all components to use managers instead of shell methods:
1. **Executor components** - Use expansion_manager instead of shell._expand_*
2. **Expansion components** - Use state directly instead of shell methods
3. **IO components** - Use executor for command execution
4. **Script components** - Use executor for script execution

### Example updates:
```python
# In executor/command.py
# Old: expanded = self.shell._expand_arguments(command)
# New: expanded = self.shell.expansion_manager.expand_arguments(command)

# In expansion/variable.py
# Old: value = self.shell._expand_variable(var_name)
# New: value = self.state.variables.get(var_name, '')
```

## Step 8: Final Cleanup

### Remove unused imports:
```python
# Remove from shell.py:
import subprocess
import glob
import readline
import signal
import termios
import tty
import tempfile
# etc.
```

### Update documentation:
1. Update method docstrings
2. Update CLAUDE.md with new architecture
3. Create architecture diagram
4. Update README with new structure

## Step 9: Comprehensive Testing

### Test all integration points:
```bash
# Run full test suite
python -m pytest tests/ -xvs

# Test interactive mode
python -m psh
# Test: history, tab completion, signals, multi-line

# Test script mode
python -m psh examples/fibonacci.sh
python -m psh -c "echo test"

# Test piping
echo "echo hello" | python -m psh

# Test all builtins
python -m psh -c "alias ll='ls -l'; ll"
python -m psh -c "function f() { echo $1; }; f test"
```

## Step 10: Performance Optimization

### Profile and optimize:
1. **Import optimization** - Use lazy imports where possible
2. **Manager initialization** - Initialize only needed managers
3. **Cache frequently used lookups** - Variable lookups, etc.

## Implementation Order

1. **Commit Phase 6** - Complete interactive refactoring
2. **Remove delegations** - Clean up redundant methods (1 hour)
3. **Move execution logic** - Complete executor extraction (3-4 hours)
4. **Extract utilities** - Move file tests and helpers (1 hour)
5. **Update dependencies** - Fix all component interactions (2 hours)
6. **Final cleanup** - Imports, docs, formatting (1 hour)
7. **Comprehensive testing** - Ensure everything works (2 hours)

## Validation Checklist

- [ ] Shell.py under 400 lines
- [ ] All tests passing
- [ ] Interactive mode fully functional
- [ ] Script execution working
- [ ] Piping/redirection working
- [ ] Job control functional
- [ ] RC file loading works
- [ ] All builtins operational
- [ ] Performance not degraded
- [ ] Documentation updated

## Expected Results

### Final Metrics
- **Shell.py**: ~350 lines (87% reduction from original)
- **Component sizes**: All under 500 lines
- **Test coverage**: Maintained or improved
- **Performance**: No regression

### Architecture Benefits
1. **Clear separation** - Each component has single responsibility
2. **Easy testing** - Components can be tested in isolation
3. **Easy extension** - New features as new components
4. **Better debugging** - Clear boundaries and data flow
5. **Educational value** - Each module teaches specific concepts

## Common Pitfalls to Avoid

1. **Circular dependencies** - Ensure clean dependency hierarchy
2. **State consistency** - All components must share same state
3. **Error handling** - Maintain consistent error handling
4. **Signal safety** - Ensure signal handlers remain safe
5. **Performance** - Avoid excessive indirection

## Next Steps After Phase 7

1. **Documentation**
   - Architecture guide
   - Component documentation
   - Developer handbook

2. **Optimization**
   - Performance profiling
   - Memory usage analysis
   - Startup time optimization

3. **Enhancement**
   - Plugin system design
   - Extension points
   - Configuration system

## Conclusion

Phase 7 completes the transformation of shell.py from a 2,712-line monolith into a clean ~350-line orchestrator. The shell now has a proper component-based architecture with clear separation of concerns, making it easier to understand, test, and extend.