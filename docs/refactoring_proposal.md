# Shell.py Refactoring Proposal

## Overview

This document outlines a comprehensive refactoring plan for `psh/shell.py`, which has grown to 2230+ lines and contains multiple responsibilities that should be separated for better maintainability, testability, and educational clarity.

## Current Architecture Analysis

### Strengths
- Clear three-phase architecture: tokenize → parse → execute
- Well-separated tokenizer and parser modules
- Educational clarity maintained in core concepts

### Problems with shell.py
- **Multiple concerns mixed together**: execution, I/O, job control, built-ins, environment management
- **Large file size**: 2230+ lines in a single file
- **Hard to maintain and extend**: New features require navigating through unrelated code
- **Built-ins scattered**: Built-in commands mixed with execution logic
- **Testing complexity**: Difficult to unit test individual components

## Proposed Refactoring Plan

### 1. Extract Built-in Commands (`psh/builtins.py`)

**Purpose**: Centralize all built-in command implementations

**Content**: Move all `_builtin_*` methods to a dedicated module

```python
class BuiltinCommands:
    def __init__(self, shell):
        self.shell = shell
    
    def exit(self, args):
        """Exit the shell with optional exit code."""
        # Move _builtin_exit logic here
        
    def cd(self, args):
        """Change directory."""
        # Move _builtin_cd logic here
        
    def echo(self, args):
        """Echo arguments to stdout."""
        # Move _builtin_echo logic here
        
    # ... all other built-ins (export, pwd, env, unset, source, history, 
    # set, version, alias, unalias, declare, return, jobs, fg, bg, test, 
    # true, false)
    
    def get_builtin_map(self):
        """Return dictionary mapping builtin names to methods."""
        return {
            'exit': self.exit,
            'cd': self.cd,
            'echo': self.echo,
            # ... complete mapping
        }
```

**Benefits**:
- All built-ins in one place for easy maintenance
- Can easily add new built-ins
- Cleaner separation from execution logic

### 2. Extract Process Execution (`psh/execution.py`)

**Purpose**: Handle external command and pipeline execution

**Content**: Move process/pipeline execution logic

```python
class ProcessExecutor:
    def __init__(self, shell):
        self.shell = shell
    
    def execute_external(self, args, command):
        """Execute an external command with proper redirection and process handling."""
        # Move _execute_external logic here
        
    def execute_pipeline(self, pipeline):
        """Execute a pipeline of commands."""
        # Move execute_pipeline logic here
        
    def _setup_child_process(self, pgid, command_index, num_commands, pipes):
        """Set up a child process in a pipeline."""
        # Move _setup_child_process logic here
        
    def _wait_for_pipeline(self, pids):
        """Wait for all processes in pipeline and return exit status of last."""
        # Move _wait_for_pipeline logic here
        
    def _build_pipeline_string(self, pipeline):
        """Build a string representation of the pipeline for job display."""
        # Move _build_pipeline_string logic here
        
    def _execute_in_child(self, command):
        """Execute a command in a child process (after fork)."""
        # Move _execute_in_child logic here
```

**Benefits**:
- Isolates complex process management code
- Easier to test pipeline execution
- Cleaner job control integration

### 3. Extract Variable/Environment Management (`psh/environment.py`)

**Purpose**: Handle all variable expansion and environment operations

**Content**: Move variable expansion and environment handling

```python
class Environment:
    def __init__(self, shell):
        self.shell = shell
    
    def expand_variable(self, var_expr):
        """Expand a variable expression starting with $."""
        # Move _expand_variable logic here
        
    def expand_string_variables(self, text):
        """Expand variables in a string (for here strings)."""
        # Move _expand_string_variables logic here
        
    def expand_tilde(self, path):
        """Expand tilde in paths like ~ and ~user."""
        # Move _expand_tilde logic here
        
    def expand_arguments(self, command):
        """Expand variables, command substitutions, tildes, and globs in command arguments."""
        # Move _expand_arguments logic here
        
    def execute_command_substitution(self, cmd_sub):
        """Execute command substitution and return output."""
        # Move _execute_command_substitution logic here
        
    def handle_variable_assignment(self, args):
        """Handle variable assignment if present."""
        # Move _handle_variable_assignment logic here
```

**Benefits**:
- Centralizes all variable handling logic
- Easier to extend with new expansion features
- Cleaner separation of concerns

### 4. Extract I/O and Redirection (`psh/redirections.py`)

**Purpose**: Manage all I/O redirection operations

**Content**: Move redirection setup and management

```python
class RedirectionManager:
    def __init__(self, shell):
        self.shell = shell
    
    def setup_builtin_redirections(self, command):
        """Set up redirections for built-in commands."""
        # Move _setup_builtin_redirections logic here
        
    def restore_builtin_redirections(self, stdin_backup, stdout_backup, stderr_backup):
        """Restore original stdin/stdout/stderr after built-in execution."""
        # Move _restore_builtin_redirections logic here
        
    def setup_child_redirections(self, command):
        """Set up redirections in child process (after fork) using dup2."""
        # Move _setup_child_redirections logic here
        
    def collect_heredocs(self, command_list):
        """Collect here document content for all commands."""
        # Move _collect_heredocs logic here
```

**Benefits**:
- Isolates complex I/O handling
- Easier to add new redirection types
- Cleaner error handling for I/O operations

### 5. Extract Script Execution (`psh/script_runner.py`)

**Purpose**: Handle script file execution and validation

**Content**: Move script file handling

```python
class ScriptRunner:
    def __init__(self, shell):
        self.shell = shell
    
    def run_script(self, script_path, script_args=None):
        """Execute a script file with optional arguments."""
        # Move run_script logic here
        
    def validate_script_file(self, script_path):
        """Validate script file and return appropriate exit code."""
        # Move _validate_script_file logic here
        
    def is_binary_file(self, file_path):
        """Check if file is binary by looking for null bytes and other indicators."""
        # Move _is_binary_file logic here
        
    def execute_with_shebang(self, script_path, script_args):
        """Execute script using its shebang interpreter."""
        # Move _execute_with_shebang logic here
        
    def parse_shebang(self, script_path):
        """Parse shebang line from script file."""
        # Move _parse_shebang logic here
        
    def should_execute_with_shebang(self, script_path):
        """Determine if script should be executed with its shebang interpreter."""
        # Move _should_execute_with_shebang logic here
        
    def find_source_file(self, filename):
        """Find a source file, searching PATH if needed."""
        # Move _find_source_file logic here
```

**Benefits**:
- Isolates script execution complexity
- Easier to add new script features
- Cleaner separation from interactive shell logic

### 6. Refactored Shell Class Structure

**Purpose**: Core orchestration and control structures only

```python
class Shell:
    def __init__(self, args=None, script_name=None):
        # Core shell state
        self.env = os.environ.copy()
        self.variables = {}
        self.positional_params = args if args else []
        self.script_name = script_name or "psh"
        self.is_script_mode = script_name is not None and script_name != "psh"
        
        # Component initialization
        self.builtins = BuiltinCommands(self)
        self.executor = ProcessExecutor(self)
        self.environment = Environment(self)
        self.redirections = RedirectionManager(self)
        self.script_runner = ScriptRunner(self)
        
        # Existing managers
        self.alias_manager = AliasManager()
        self.function_manager = FunctionManager()
        self.job_manager = JobManager()
        
        # Other core state...
        self.last_exit_code = 0
        self.history = []
        # ... etc
    
    # Keep only core execution orchestration methods
    def execute_command(self, command):
        """Execute a single command - orchestrates other components."""
        
    def execute_toplevel(self, toplevel):
        """Execute a top-level script/input containing functions and commands."""
        
    def execute_if_statement(self, if_stmt):
        """Execute an if/then/else/fi conditional statement."""
        
    def execute_while_statement(self, while_stmt):
        """Execute a while/do/done loop statement."""
        
    def execute_for_statement(self, for_stmt):
        """Execute a for/in/do/done loop statement."""
        
    def execute_case_statement(self, case_stmt):
        """Execute a case/esac statement."""
        
    # Keep high-level orchestration methods
    def run_command(self, command_string, add_to_history=True):
        """Execute a command string using the unified input system."""
        
    def interactive_loop(self):
        """Main interactive shell loop."""
```

## Implementation Strategy

### Phase 1: Extract Built-ins (Lowest Risk)
1. Create `psh/builtins.py`
2. Move all `_builtin_*` methods
3. Update shell.py to use new BuiltinCommands class
4. Run tests to ensure no regressions

### Phase 2: Extract Process Execution
1. Create `psh/execution.py`
2. Move process/pipeline execution methods
3. Update shell.py to use ProcessExecutor
4. Test pipeline functionality

### Phase 3: Extract Environment Management
1. Create `psh/environment.py`
2. Move variable expansion methods
3. Update shell.py to use Environment class
4. Test variable expansion and command substitution

### Phase 4: Extract I/O Redirection
1. Create `psh/redirections.py`
2. Move redirection setup methods
3. Update shell.py to use RedirectionManager
4. Test all redirection types

### Phase 5: Extract Script Execution
1. Create `psh/script_runner.py`
2. Move script execution methods
3. Update shell.py to use ScriptRunner
4. Test script execution and shebang handling

### Phase 6: Final Shell Refactoring
1. Clean up shell.py to focus on orchestration
2. Ensure all tests pass
3. Update documentation

## Expected Results

### Before Refactoring
- `shell.py`: 2230+ lines
- Mixed responsibilities
- Hard to test individual components
- Difficult to add new features

### After Refactoring
- `shell.py`: ~800-1000 lines (core orchestration only)
- `builtins.py`: ~400-500 lines
- `execution.py`: ~300-400 lines
- `environment.py`: ~200-300 lines
- `redirections.py`: ~150-200 lines
- `script_runner.py`: ~200-250 lines

## Benefits of This Refactoring

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Smaller, focused files are easier to understand and modify
3. **Testability**: Can unit test each component independently with mock objects
4. **Extensibility**: Easy to add new built-ins, redirection types, or execution features
5. **Educational Value**: Clearer architecture demonstrates good software design principles
6. **Debugging**: Easier to isolate and fix issues in specific areas
7. **Code Reuse**: Components can potentially be reused in other shell implementations

## Risks and Mitigations

### Risks
- Circular dependencies between components
- Increased complexity of component interactions
- Potential performance overhead from additional method calls

### Mitigations
- Careful design of component interfaces
- Use dependency injection pattern (components receive shell instance)
- Comprehensive testing at each phase
- Performance testing to ensure no significant slowdown

## Testing Strategy

1. **Unit Tests**: Create focused unit tests for each extracted component
2. **Integration Tests**: Ensure components work together correctly
3. **Regression Tests**: Run full test suite after each phase
4. **Performance Tests**: Verify no significant performance degradation

This refactoring will significantly improve the maintainability and extensibility of the psh codebase while preserving its educational value and functionality.