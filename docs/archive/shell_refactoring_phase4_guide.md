# Phase 4 Implementation Guide: Executor Components

## Overview
Phase 4 is the most complex phase of the shell.py refactoring, focusing on extracting command execution logic into dedicated executor components. This phase will significantly reduce the size of shell.py by moving execution logic to specialized classes.

## Challenges and Considerations

### 1. Complex Dependencies
- Execution methods are tightly coupled with shell state
- Job control integration throughout execution
- Signal handling during command execution
- Process group management

### 2. Execution Flow
- Command execution has multiple paths (builtin vs external)
- Pipeline execution requires careful process coordination
- Control structures have nested execution contexts
- Variable assignments affect execution environment

### 3. Error Handling
- Exit status propagation
- Exception handling for control flow (break/continue)
- Signal interruption handling

## Step 1: Create Base Executor Infrastructure

### Create `psh/executor/base.py` (already exists, enhance it):
```python
"""Base classes for executor components."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from ..ast_nodes import ASTNode
from ..core.state import ShellState
from ..core.exceptions import LoopBreak, LoopContinue

if TYPE_CHECKING:
    from ..shell import Shell


class ExecutorComponent(ABC):
    """Base class for all executor components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
    
    @abstractmethod
    def execute(self, node: ASTNode) -> int:
        """Execute the given AST node and return exit status."""
        pass
    
    def is_builtin(self, command: str) -> bool:
        """Check if a command is a builtin."""
        return command in self.builtin_registry.builtins
    
    def is_function(self, command: str) -> bool:
        """Check if a command is a function."""
        return command in self.function_manager.functions


class ExecutorManager:
    """Manages all executor components and routes execution."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize executor components
        from .command import CommandExecutor
        from .pipeline import PipelineExecutor
        from .control_flow import ControlFlowExecutor
        from .statement import StatementExecutor
        
        self.command_executor = CommandExecutor(shell)
        self.pipeline_executor = PipelineExecutor(shell)
        self.control_flow_executor = ControlFlowExecutor(shell)
        self.statement_executor = StatementExecutor(shell)
    
    def execute(self, node: ASTNode) -> int:
        """Route execution to appropriate executor based on node type."""
        # This will be implemented as we create the executors
        pass
```

## Step 2: Extract Command Execution

### Create `psh/executor/command.py`:
```python
"""Single command execution."""
import os
import sys
from typing import List, Optional
from ..ast_nodes import Command
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn

class CommandExecutor(ExecutorComponent):
    """Executes single commands (builtins, functions, or external)."""
    
    def execute(self, command: Command) -> int:
        """Execute a single command and return exit status."""
        # Handle empty command
        if not command.args:
            return 0
        
        # Expand arguments
        expanded_args = self.expansion_manager.expand_arguments(command)
        
        # Handle variable assignments
        if self._is_variable_assignment(expanded_args):
            return self._handle_variable_assignment(expanded_args)
        
        # Get command name
        cmd_name = expanded_args[0]
        
        # Check if it's a function
        if self.is_function(cmd_name):
            return self._execute_function(cmd_name, expanded_args[1:])
        
        # Check if it's a builtin
        if self.is_builtin(cmd_name):
            return self._execute_builtin(cmd_name, expanded_args, command)
        
        # Execute external command
        return self._execute_external(expanded_args, command)
    
    def _is_variable_assignment(self, args: List[str]) -> bool:
        """Check if command is a variable assignment."""
        if not args or '=' not in args[0] or args[0].startswith('='):
            return False
        
        # Check if all leading arguments are assignments
        for arg in args:
            if '=' not in arg:
                return False
        return True
    
    def _handle_variable_assignment(self, args: List[str]) -> int:
        """Handle variable assignment."""
        for arg in args:
            name, value = arg.split('=', 1)
            # Validate variable name
            if not name or not name[0].isalpha() and name[0] != '_':
                print(f"psh: {name}: not a valid identifier", file=sys.stderr)
                return 1
            if not all(c.isalnum() or c == '_' for c in name):
                print(f"psh: {name}: not a valid identifier", file=sys.stderr)
                return 1
            self.state.set_variable(name, value)
        return 0
    
    def _execute_function(self, name: str, args: List[str]) -> int:
        """Execute a shell function."""
        # Implementation will delegate to shell's execute_function
        # This needs careful handling of function stack
        pass
    
    def _execute_builtin(self, name: str, args: List[str], command: Command) -> int:
        """Execute a builtin command."""
        # Set up redirections for builtin
        stdin_backup, stdout_backup, stderr_backup = \
            self.io_manager.setup_builtin_redirections(command)
        
        try:
            # Get builtin
            builtin_class = self.builtin_registry.get_builtin(name)
            builtin = builtin_class(self.shell)
            
            # Execute builtin
            result = builtin.execute(args[1:])
            
            # Update exit code
            self.state.last_exit_code = result
            return result
            
        except FunctionReturn as e:
            # Handle return from function
            self.state.last_exit_code = e.code
            raise
        finally:
            # Restore redirections
            self.io_manager.restore_builtin_redirections(
                stdin_backup, stdout_backup, stderr_backup)
    
    def _execute_external(self, args: List[str], command: Command) -> int:
        """Execute an external command."""
        # Implementation will handle fork/exec
        # This is complex due to job control
        pass
```

## Step 3: Extract Pipeline Execution

### Create `psh/executor/pipeline.py`:
```python
"""Pipeline execution."""
import os
import sys
from typing import List
from ..ast_nodes import Pipeline
from .base import ExecutorComponent

class PipelineExecutor(ExecutorComponent):
    """Executes command pipelines."""
    
    def execute(self, pipeline: Pipeline) -> int:
        """Execute a pipeline and return exit status of last command."""
        if len(pipeline.commands) == 1:
            # Single command, no pipe needed
            return self.shell.execute_command(pipeline.commands[0])
        
        # Multiple commands in pipeline
        return self._execute_pipeline(pipeline.commands)
    
    def _execute_pipeline(self, commands: List) -> int:
        """Execute a multi-command pipeline."""
        # Save original stdin/stdout
        stdin_backup = os.dup(0)
        stdout_backup = os.dup(1)
        
        # Create pipes
        pipes = []
        for i in range(len(commands) - 1):
            pipes.append(os.pipe())
        
        pids = []
        
        try:
            for i, command in enumerate(commands):
                # Create pipe connections
                if i > 0:  # Not first command
                    # Read from previous pipe
                    os.dup2(pipes[i-1][0], 0)
                    os.close(pipes[i-1][0])
                    os.close(pipes[i-1][1])
                
                if i < len(commands) - 1:  # Not last command
                    # Write to next pipe
                    os.dup2(pipes[i][1], 1)
                    os.close(pipes[i][0])
                    os.close(pipes[i][1])
                
                # Fork and execute
                pid = self._fork_and_execute(command)
                pids.append(pid)
                
                # Restore stdin/stdout for parent
                os.dup2(stdin_backup, 0)
                os.dup2(stdout_backup, 1)
            
            # Close all remaining pipes
            for read_fd, write_fd in pipes:
                try:
                    os.close(read_fd)
                except:
                    pass
                try:
                    os.close(write_fd)
                except:
                    pass
            
            # Wait for all commands
            last_status = 0
            for pid in pids:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    last_status = os.WEXITSTATUS(status)
                else:
                    last_status = 1
            
            return last_status
            
        finally:
            # Restore original descriptors
            os.dup2(stdin_backup, 0)
            os.dup2(stdout_backup, 1)
            os.close(stdin_backup)
            os.close(stdout_backup)
    
    def _fork_and_execute(self, command) -> int:
        """Fork and execute a command in the child process."""
        # Implementation will handle process creation
        pass
```

## Step 4: Extract Control Flow Execution

### Create `psh/executor/control_flow.py`:
```python
"""Control flow statement execution."""
from ..ast_nodes import (IfStatement, WhileStatement, ForStatement, 
                         CaseStatement, BreakStatement, ContinueStatement)
from .base import ExecutorComponent
from ..core.exceptions import LoopBreak, LoopContinue

class ControlFlowExecutor(ExecutorComponent):
    """Executes control flow statements."""
    
    def execute(self, node) -> int:
        """Execute a control flow statement."""
        if isinstance(node, IfStatement):
            return self.execute_if(node)
        elif isinstance(node, WhileStatement):
            return self.execute_while(node)
        elif isinstance(node, ForStatement):
            return self.execute_for(node)
        elif isinstance(node, CaseStatement):
            return self.execute_case(node)
        elif isinstance(node, BreakStatement):
            raise LoopBreak(node.level)
        elif isinstance(node, ContinueStatement):
            raise LoopContinue(node.level)
        else:
            raise ValueError(f"Unknown control flow node: {type(node)}")
    
    def execute_if(self, node: IfStatement) -> int:
        """Execute if/then/else statement."""
        # Execute condition
        condition_status = self.shell.execute_command_list(node.condition)
        
        if condition_status == 0:
            # Condition true, execute then part
            return self.shell.execute_command_list(node.then_part)
        
        # Check elif parts
        for elif_condition, elif_then in node.elif_parts:
            elif_status = self.shell.execute_command_list(elif_condition)
            if elif_status == 0:
                return self.shell.execute_command_list(elif_then)
        
        # Execute else part if present
        if node.else_part:
            return self.shell.execute_command_list(node.else_part)
        
        return 0
    
    def execute_while(self, node: WhileStatement) -> int:
        """Execute while loop."""
        last_status = 0
        
        while True:
            try:
                # Execute condition
                condition_status = self.shell.execute_command_list(node.condition)
                
                if condition_status != 0:
                    # Condition false, exit loop
                    break
                
                # Execute body
                last_status = self.shell.execute_command_list(node.body)
                
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                continue
        
        return last_status
    
    def execute_for(self, node: ForStatement) -> int:
        """Execute for loop."""
        # Expand the word list
        expanded_items = []
        for item in node.items:
            # Handle each item based on its type
            expanded = self._expand_for_item(item)
            expanded_items.extend(expanded)
        
        last_status = 0
        
        for item in expanded_items:
            try:
                # Set loop variable
                self.state.set_variable(node.var, item)
                
                # Execute body
                last_status = self.shell.execute_command_list(node.body)
                
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                continue
        
        return last_status
    
    def execute_case(self, node: CaseStatement) -> int:
        """Execute case statement."""
        # Expand the expression
        expanded_expr = self._expand_case_expr(node.expr)
        
        # Try each case item
        for item in node.items:
            if self._match_case_pattern(expanded_expr, item.patterns):
                # Execute commands for this case
                status = self.shell.execute_statement_list(item.commands)
                
                # Handle terminator
                if item.terminator == ';;':
                    return status
                elif item.terminator == ';&':
                    # Fall through to next case
                    continue
                elif item.terminator == ';;&':
                    # Continue matching other patterns
                    continue
                
                return status
        
        return 0
    
    def _expand_for_item(self, item):
        """Expand a for loop item."""
        # Implementation will handle different item types
        pass
    
    def _expand_case_expr(self, expr):
        """Expand case expression."""
        # Implementation will handle expression expansion
        pass
    
    def _match_case_pattern(self, expr: str, patterns: List) -> bool:
        """Check if expression matches any of the patterns."""
        # Implementation will handle pattern matching
        pass
```

## Step 5: Extract Process Management

### Create `psh/executor/process.py`:
```python
"""Process management and execution."""
import os
import sys
import signal
from typing import List, Optional
from .base import ExecutorComponent

class ProcessManager(ExecutorComponent):
    """Manages process creation and execution."""
    
    def fork_and_execute_external(self, args: List[str], command) -> int:
        """Fork and execute an external command."""
        # Set up for job control
        is_interactive = sys.stdin.isatty()
        
        pid = os.fork()
        
        if pid == 0:  # Child process
            try:
                # Reset signal handlers
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                signal.signal(signal.SIGTTIN, signal.SIG_DFL)
                
                # Set up process group for job control
                if is_interactive:
                    # Put child in its own process group
                    os.setpgid(0, 0)
                    
                    # Give terminal to child if foreground
                    if not command.background:
                        pgid = os.getpgrp()
                        os.tcsetpgrp(0, pgid)
                
                # Apply redirections
                self.io_manager.setup_child_redirections(command)
                
                # Execute the command
                os.execvp(args[0], args)
                
            except FileNotFoundError:
                print(f"psh: {args[0]}: command not found", file=sys.stderr)
                os._exit(127)
            except PermissionError:
                print(f"psh: {args[0]}: permission denied", file=sys.stderr)
                os._exit(126)
            except Exception as e:
                print(f"psh: {args[0]}: {e}", file=sys.stderr)
                os._exit(1)
        
        else:  # Parent process
            return self._handle_parent_process(pid, command, args[0], is_interactive)
    
    def _handle_parent_process(self, pid: int, command, cmd_name: str, 
                               is_interactive: bool) -> int:
        """Handle parent process after fork."""
        # Implementation will handle job control and waiting
        pass
```

## Step 6: Create Statement List Executor

### Create `psh/executor/statement.py`:
```python
"""Statement list execution."""
from ..ast_nodes import CommandList, AndOrList, Pipeline
from .base import ExecutorComponent

class StatementExecutor(ExecutorComponent):
    """Executes statement lists and logical operators."""
    
    def execute_command_list(self, cmd_list: CommandList) -> int:
        """Execute a command list (statements separated by ;)."""
        last_status = 0
        
        for statement in cmd_list.statements:
            last_status = self.execute_and_or_list(statement)
            
        return last_status
    
    def execute_and_or_list(self, and_or: AndOrList) -> int:
        """Execute an and/or list with && and || operators."""
        if not and_or.pipelines:
            return 0
        
        # Execute first pipeline
        status = self.shell.execute_pipeline(and_or.pipelines[0])
        
        # Process remaining pipelines with operators
        for i in range(len(and_or.operators)):
            operator = and_or.operators[i]
            next_pipeline = and_or.pipelines[i + 1]
            
            if operator == '&&':
                # Execute only if previous succeeded
                if status == 0:
                    status = self.shell.execute_pipeline(next_pipeline)
            elif operator == '||':
                # Execute only if previous failed
                if status != 0:
                    status = self.shell.execute_pipeline(next_pipeline)
        
        return status
```

## Step 7: Update Shell Class

### Modify shell.py to use ExecutorManager:
```python
# Add import
from .executor.base import ExecutorManager

# In __init__:
self.executor_manager = ExecutorManager(self)

# Update execution methods to delegate:
def execute_command(self, command: Command) -> int:
    """Execute a single command."""
    return self.executor_manager.command_executor.execute(command)

def execute_pipeline(self, pipeline: Pipeline) -> int:
    """Execute a pipeline."""
    return self.executor_manager.pipeline_executor.execute(pipeline)

def execute_if_statement(self, node: IfStatement) -> int:
    """Execute if statement."""
    return self.executor_manager.control_flow_executor.execute_if(node)

# etc. for other execution methods
```

## Implementation Order

1. **Start with CommandExecutor**
   - Begin with variable assignment handling
   - Then builtin execution
   - Leave external execution as stub initially

2. **Implement StatementExecutor**
   - This is relatively simple
   - Good for testing the architecture

3. **Implement ControlFlowExecutor**
   - Start with if statements
   - Then while loops
   - For loops are more complex
   - Case statements last

4. **Implement PipelineExecutor**
   - Single command pipelines first
   - Then multi-command pipelines

5. **Implement ProcessManager**
   - This is the most complex
   - Involves job control integration
   - Signal handling

## Testing Strategy

### Unit Tests for Each Executor
```python
# tests/test_command_executor.py
def test_variable_assignment():
    shell = create_test_shell()
    executor = CommandExecutor(shell)
    # Test variable assignment logic

def test_builtin_execution():
    shell = create_test_shell()
    executor = CommandExecutor(shell)
    # Test builtin execution
```

### Integration Tests
- Run existing tests after each step
- Should maintain 100% pass rate
- Add new tests for executor components

### Incremental Migration
1. Create executor with minimal functionality
2. Update shell.py to use it
3. Run tests
4. Move more functionality
5. Repeat

## Common Pitfalls to Avoid

1. **State Management**
   - Don't duplicate state between shell and executors
   - Always use shell.state for consistency

2. **Signal Handling**
   - Be careful with signal handlers in child processes
   - Reset to defaults before exec

3. **Job Control**
   - Maintain process group consistency
   - Handle terminal control properly

4. **Error Handling**
   - Preserve exit status semantics
   - Handle exceptions correctly

5. **Resource Cleanup**
   - Close file descriptors properly
   - Wait for child processes

## Validation Checklist

- [ ] All 585 tests still pass
- [ ] Variable assignments work correctly
- [ ] Builtins execute with proper redirections
- [ ] External commands run correctly
- [ ] Pipelines work with proper data flow
- [ ] Control structures maintain proper flow
- [ ] Job control still functions
- [ ] Signal handling works correctly
- [ ] No resource leaks
- [ ] Performance not degraded

## Next Steps After Phase 4

Once Phase 4 is complete:
1. Phase 5: Script handling extraction
2. Phase 6: Interactive features extraction
3. Phase 7: Final integration and cleanup

The goal is to reduce shell.py to under 500 lines while maintaining all functionality.