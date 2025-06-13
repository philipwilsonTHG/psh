# ExecutorVisitor Detailed Design

## Overview

This document provides a detailed design for the ExecutorVisitor, which will use the visitor pattern to execute PSH AST nodes. This design maintains compatibility with existing execution behavior while providing better architecture.

## Core Architecture

### Class Hierarchy

```
ASTVisitor[int]
    └── ExecutorVisitor
            ├── Uses: ExpansionManager
            ├── Uses: IOManager
            ├── Uses: JobManager
            ├── Uses: BuiltinRegistry
            └── Uses: ShellState
```

### Key Design Decisions

1. **Return Type**: All visit methods return `int` (exit status)
2. **State Management**: Use ShellState for all mutable state
3. **Manager Integration**: Reuse existing manager classes
4. **Exception Handling**: Use existing exception hierarchy
5. **Context Objects**: Use context managers for cleanup

## Implementation Details

### 1. Base ExecutorVisitor Class

```python
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from ..visitor.base import ASTVisitor
from ..core.state import ShellState
from ..expansion.manager import ExpansionManager
from ..io_redirect.manager import IOManager
from ..job_control import JobManager
from ..builtins import registry as builtin_registry

class ExecutorVisitor(ASTVisitor[int]):
    """
    Visitor that executes AST nodes and returns exit status.
    
    This visitor maintains compatibility with the existing execution
    engine while providing a cleaner architecture.
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize with shell instance for access to all components."""
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = builtin_registry
        
        # Execution state
        self._in_pipeline = False
        self._background_job = None
        self._current_function = None
```

### 2. Simple Command Execution

```python
def visit_SimpleCommand(self, node: SimpleCommand) -> int:
    """Execute a simple command (builtin or external)."""
    try:
        # Perform expansions
        expanded_args, expanded_types = self._expand_command(node)
        
        if not expanded_args:
            return 0
        
        # Check for variable assignments
        if self._is_pure_assignment(expanded_args):
            return self._handle_assignments(expanded_args)
        
        # Apply redirections
        with self.io_manager.apply_redirections(node.redirects):
            # Execute command
            cmd_name = expanded_args[0]
            
            # Check builtins first
            if cmd_name in self.builtin_registry:
                return self._execute_builtin(cmd_name, expanded_args[1:])
            
            # Check functions
            if self.shell.function_manager.get_function(cmd_name):
                return self._execute_function(cmd_name, expanded_args[1:])
            
            # Execute external command
            return self._execute_external(expanded_args, node.background)
            
    except Exception as e:
        self.state.last_exit_code = 1
        print(f"psh: {e}", file=sys.stderr)
        return 1
```

### 3. Pipeline Execution

```python
def visit_Pipeline(self, node: Pipeline) -> int:
    """Execute a pipeline of commands."""
    if len(node.commands) == 1:
        # Single command, no pipeline needed
        return self.visit(node.commands[0])
    
    # Save pipeline state
    was_in_pipeline = self._in_pipeline
    self._in_pipeline = True
    
    try:
        # Create pipeline job
        job = self.job_manager.create_job(" | ".join(
            self._command_to_string(cmd) for cmd in node.commands
        ))
        
        # Set up pipes
        pipes = []
        for i in range(len(node.commands) - 1):
            pipes.append(os.pipe())
        
        # Execute commands in pipeline
        processes = []
        for i, command in enumerate(node.commands):
            # Determine pipes for this command
            stdin_fd = pipes[i-1][0] if i > 0 else None
            stdout_fd = pipes[i][1] if i < len(pipes) else None
            
            # Fork and execute
            pid = os.fork()
            if pid == 0:
                # Child process
                self._setup_pipeline_redirections(stdin_fd, stdout_fd, pipes)
                exit_status = self.visit(command)
                sys.exit(exit_status)
            else:
                # Parent process
                processes.append(pid)
                self.job_manager.add_process_to_job(job.job_id, pid)
        
        # Close pipes in parent
        for read_fd, write_fd in pipes:
            os.close(read_fd)
            os.close(write_fd)
        
        # Wait for pipeline completion
        if node.background:
            self._background_job = job
            return 0
        else:
            return self._wait_for_pipeline(processes, job)
            
    finally:
        self._in_pipeline = was_in_pipeline
```

### 4. Control Structure Execution

#### If Statement
```python
def visit_IfConditional(self, node: IfConditional) -> int:
    """Execute if/then/else statement."""
    # Evaluate condition
    condition_status = self.visit(node.condition)
    
    if condition_status == 0:
        # Condition true, execute then branch
        return self.visit(node.then_stmt)
    elif node.else_stmt:
        # Condition false, execute else branch
        return self.visit(node.else_stmt)
    else:
        # No else branch
        return 0
```

#### While Loop
```python
def visit_WhileLoop(self, node: WhileLoop) -> int:
    """Execute while loop."""
    exit_status = 0
    
    # Apply redirections for entire loop
    with self.io_manager.apply_redirections(node.redirects or []):
        try:
            while True:
                # Evaluate condition
                condition_status = self.visit(node.condition)
                if condition_status != 0:
                    break
                
                # Execute body
                try:
                    exit_status = self.visit(node.body)
                except LoopContinue as lc:
                    if lc.level > 1:
                        raise LoopContinue(lc.level - 1)
                    continue
                except LoopBreak as lb:
                    if lb.level > 1:
                        raise LoopBreak(lb.level - 1)
                    break
                    
        except LoopBreak:
            pass
            
    return exit_status
```

#### For Loop
```python
def visit_ForLoop(self, node: ForLoop) -> int:
    """Execute for loop."""
    exit_status = 0
    
    # Expand items
    expanded_items = []
    for item in node.items:
        expanded = self.expansion_manager.expand_word(item)
        if isinstance(expanded, list):
            expanded_items.extend(expanded)
        else:
            expanded_items.append(expanded)
    
    # Apply redirections for entire loop
    with self.io_manager.apply_redirections(node.redirects or []):
        try:
            for item in expanded_items:
                # Set loop variable
                self.state.set_variable(node.variable, item)
                
                # Execute body
                try:
                    exit_status = self.visit(node.body)
                except LoopContinue as lc:
                    if lc.level > 1:
                        raise LoopContinue(lc.level - 1)
                    continue
                except LoopBreak as lb:
                    if lb.level > 1:
                        raise LoopBreak(lb.level - 1)
                    break
                    
        except LoopBreak:
            pass
            
    return exit_status
```

### 5. Function Execution

```python
def visit_FunctionDef(self, node: FunctionDef) -> int:
    """Define a function (doesn't execute it)."""
    self.shell.function_manager.define_function(node.name, node.body)
    return 0

def _execute_function(self, name: str, args: List[str]) -> int:
    """Execute a function with arguments."""
    func_body = self.shell.function_manager.get_function(name)
    if not func_body:
        return 127  # Command not found
    
    # Save current positional parameters
    saved_params = self.state.positional_params.copy()
    saved_param_count = self.state.get_variable('#')
    
    # Save function context
    old_function = self._current_function
    self._current_function = name
    
    try:
        # Set new positional parameters
        self.state.set_positional_params(args)
        
        # Execute function body
        return self.visit(func_body)
        
    except FunctionReturn as ret:
        return ret.code
    finally:
        # Restore state
        self.state.positional_params = saved_params
        self.state.set_variable('#', saved_param_count)
        self._current_function = old_function
```

### 6. Statement Lists and Operators

```python
def visit_StatementList(self, node: StatementList) -> int:
    """Execute a list of statements."""
    exit_status = 0
    
    for statement in node.statements:
        exit_status = self.visit(statement)
        # Update $? after each statement
        self.state.last_exit_code = exit_status
    
    return exit_status

def visit_AndOrList(self, node: AndOrList) -> int:
    """Execute pipelines with && and || operators."""
    if not node.pipelines:
        return 0
    
    # Execute first pipeline
    exit_status = self.visit(node.pipelines[0])
    
    # Process remaining pipelines based on operators
    for i, op in enumerate(node.operators):
        if op == '&&' and exit_status == 0:
            # Execute next pipeline only if previous succeeded
            exit_status = self.visit(node.pipelines[i + 1])
        elif op == '||' and exit_status != 0:
            # Execute next pipeline only if previous failed
            exit_status = self.visit(node.pipelines[i + 1])
        # Otherwise skip this pipeline
    
    return exit_status
```

### 7. Helper Methods

```python
def _expand_command(self, node: SimpleCommand) -> Tuple[List[str], List[str]]:
    """Expand all arguments in a command."""
    expanded_args = []
    expanded_types = []
    
    for arg, arg_type in zip(node.args, node.arg_types):
        result = self.expansion_manager.expand_word(arg, arg_type)
        if isinstance(result, list):
            expanded_args.extend(result)
            expanded_types.extend([arg_type] * len(result))
        else:
            expanded_args.append(result)
            expanded_types.append(arg_type)
    
    return expanded_args, expanded_types

def _execute_builtin(self, name: str, args: List[str]) -> int:
    """Execute a builtin command."""
    builtin = self.builtin_registry.get_builtin(name)
    if not builtin:
        return 127
    
    try:
        return builtin.execute(args, self.shell)
    except Exception as e:
        print(f"psh: {name}: {e}", file=sys.stderr)
        return 1

def _execute_external(self, args: List[str], background: bool = False) -> int:
    """Execute an external command."""
    if self._in_pipeline:
        # In pipeline, don't use subprocess
        os.execvp(args[0], args)
        # If we get here, exec failed
        print(f"psh: {args[0]}: command not found", file=sys.stderr)
        sys.exit(127)
    
    # Normal execution
    try:
        if background:
            process = subprocess.Popen(args)
            job = self.job_manager.create_job(" ".join(args))
            self.job_manager.add_process_to_job(job.job_id, process.pid)
            self._background_job = job
            return 0
        else:
            result = subprocess.run(args)
            return result.returncode
    except FileNotFoundError:
        print(f"psh: {args[0]}: command not found", file=sys.stderr)
        return 127
```

## Testing Strategy

### 1. Unit Tests
- Test each visit method independently
- Mock dependencies (managers, state)
- Verify correct delegation

### 2. Integration Tests
- Test complete command execution
- Compare with existing executor
- Verify state changes

### 3. Regression Tests
- Run entire test suite with ExecutorVisitor
- Compare outputs and exit codes
- Performance benchmarks

### 4. Migration Tests
- Parallel execution with flag
- A/B testing framework
- Gradual rollout

## Performance Considerations

1. **Method Dispatch**: Virtual method calls have overhead
   - Solution: Profile and optimize hot paths
   
2. **Object Creation**: Visitor might create more objects
   - Solution: Object pooling for frequently used types
   
3. **Recursion Depth**: Deep ASTs might hit limits
   - Solution: Consider iterative approach for deep trees

## Benefits

1. **Clear Structure**: Each node type has dedicated handler
2. **Testability**: Easy to mock and test individual methods
3. **Extensibility**: New node types just need new visit method
4. **Debugging**: Clear execution trace through visit calls
5. **Maintainability**: Related code is grouped together

## Conclusion

The ExecutorVisitor design provides a clean, maintainable approach to command execution while preserving all existing functionality. The gradual migration path ensures safety and allows for thorough testing.