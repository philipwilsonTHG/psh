"""
Executor visitor that executes AST nodes using the visitor pattern.

This visitor provides a clean architecture for command execution while
maintaining compatibility with the existing execution engine.
"""

import os
import sys
import subprocess
import signal
from typing import List, Tuple, Optional, Dict, Any, Union
from contextlib import contextmanager

from .base import ASTVisitor
from ..ast_nodes import (
    # Core nodes
    ASTNode, TopLevel, StatementList, AndOrList, Pipeline,
    SimpleCommand, Redirect,
    
    # Control structures
    WhileLoop, ForLoop, CStyleForLoop, IfConditional, 
    CaseConditional, CaseItem, SelectLoop,
    BreakStatement, ContinueStatement,
    
    # Function nodes
    FunctionDef,
    
    # Arithmetic
    ArithmeticEvaluation,
    
    # Test commands
    EnhancedTestStatement,
    
    # Array operations
    ArrayInitialization, ArrayElementAssignment,
    
    # Other
    ProcessSubstitution
)
from ..core.exceptions import LoopBreak, LoopContinue, UnboundVariableError
from ..builtins.function_support import FunctionReturn
from ..job_control import JobState
import fnmatch


class PipelineContext:
    """Context for managing pipeline execution."""
    
    def __init__(self, job_manager):
        self.job_manager = job_manager
        self.pipes = []
        self.processes = []
        self.job = None
    
    def add_pipe(self):
        """Add a new pipe for the pipeline."""
        self.pipes.append(os.pipe())
        return len(self.pipes) - 1
    
    def get_stdin_fd(self, index: int) -> Optional[int]:
        """Get stdin file descriptor for command at index."""
        if index > 0 and index <= len(self.pipes):
            return self.pipes[index - 1][0]
        return None
    
    def get_stdout_fd(self, index: int) -> Optional[int]:
        """Get stdout file descriptor for command at index."""
        if index < len(self.pipes):
            return self.pipes[index][1]
        return None
    
    def close_pipes(self):
        """Close all pipes in parent process."""
        for read_fd, write_fd in self.pipes:
            try:
                os.close(read_fd)
                os.close(write_fd)
            except OSError:
                pass
    
    def add_process(self, pid: int):
        """Add a process to the pipeline."""
        self.processes.append(pid)


class ExecutorVisitor(ASTVisitor[int]):
    """
    Visitor that executes AST nodes and returns exit status.
    
    This visitor maintains compatibility with the existing execution
    engine while providing a cleaner architecture based on the visitor
    pattern.
    """
    
    def __init__(self, shell: 'Shell'):
        """
        Initialize executor with shell instance.
        
        Args:
            shell: The shell instance providing access to all components
        """
        super().__init__()  # Initialize method cache
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
        
        # Execution state
        self._in_pipeline = False
        self._in_subshell = False
        self._background_job = None
        self._current_function = None
        self._loop_depth = 0
        self._pipeline_context = None
    
    @contextmanager
    def _apply_redirections(self, redirects):
        """Context manager for applying and restoring redirections."""
        if not redirects:
            yield
            return
            
        saved_fds = self.io_manager.apply_redirections(redirects)
        try:
            yield
        finally:
            self.io_manager.restore_redirections(saved_fds)
    
    # Top-level execution
    
    def visit_TopLevel(self, node: TopLevel) -> int:
        """Execute top-level statements."""
        exit_status = 0
        
        for item in node.items:
            try:
                exit_status = self.visit(item)
                # Update $? after each top-level item
                self.state.last_exit_code = exit_status
            except LoopBreak:
                # Break at top level is an error
                print("psh: break: only meaningful in a loop", file=sys.stderr)
                exit_status = 1
                self.state.last_exit_code = exit_status
            except LoopContinue:
                # Continue at top level is an error
                print("psh: continue: only meaningful in a loop", file=sys.stderr)
                exit_status = 1
                self.state.last_exit_code = exit_status
            except SystemExit:
                # Let exit propagate
                raise
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print()  # New line after ^C
                exit_status = 130
                self.state.last_exit_code = exit_status
        
        return exit_status
    
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
        self.state.last_exit_code = exit_status
        
        # Process remaining pipelines based on operators
        for i, op in enumerate(node.operators):
            if op == '&&' and exit_status == 0:
                # Execute next pipeline only if previous succeeded
                exit_status = self.visit(node.pipelines[i + 1])
            elif op == '||' and exit_status != 0:
                # Execute next pipeline only if previous failed
                exit_status = self.visit(node.pipelines[i + 1])
            # Otherwise skip this pipeline
            
            self.state.last_exit_code = exit_status
        
        return exit_status
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        """Execute a pipeline of commands."""
        # Handle NOT operator
        if node.negated:
            exit_status = self._execute_pipeline(node)
            # Invert exit status for NOT
            return 0 if exit_status != 0 else 1
        else:
            return self._execute_pipeline(node)
    
    def _execute_pipeline(self, node: Pipeline) -> int:
        """Execute pipeline without NOT handling."""
        if len(node.commands) == 1:
            # Single command, no pipeline needed
            return self.visit(node.commands[0])
        
        # Multi-command pipeline
        pipeline_ctx = PipelineContext(self.job_manager)
        
        # Create pipes
        for i in range(len(node.commands) - 1):
            pipeline_ctx.add_pipe()
        
        # Check if pipeline runs in background (last command determines)
        is_background = node.commands[-1].background if node.commands else False
        
        # Build command string for job tracking
        command_string = self._pipeline_to_string(node)
        
        # Variables to track pgid
        pgid = None
        pids = []
        
        # Save pipeline state
        old_pipeline = self._in_pipeline
        old_context = self._pipeline_context
        self._in_pipeline = True
        self._pipeline_context = pipeline_ctx
        
        try:
            # Fork processes for each command
            for i, command in enumerate(node.commands):
                pid = os.fork()
                
                if pid == 0:
                    # Child process
                    try:
                        # Set flag to indicate we're in a forked child
                        self.state._in_forked_child = True
                        
                        # Set process group - first child becomes group leader
                        if pgid is None:
                            pgid = os.getpid()
                            os.setpgid(0, pgid)
                        else:
                            os.setpgid(0, pgid)
                        
                        # Reset signal handlers to default
                        signal.signal(signal.SIGINT, signal.SIG_DFL)
                        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                        
                        # Set up pipeline redirections
                        self._setup_pipeline_redirections(i, pipeline_ctx)
                        
                        # Execute command
                        exit_status = self.visit(command)
                        os._exit(exit_status)
                    except SystemExit as e:
                        # Handle explicit exit
                        os._exit(e.code if e.code is not None else 0)
                    except Exception as e:
                        print(f"psh: {e}", file=sys.stderr)
                        os._exit(1)
                else:
                    # Parent process
                    if pgid is None:
                        pgid = pid
                        os.setpgid(pid, pgid)
                    else:
                        try:
                            os.setpgid(pid, pgid)
                        except:
                            pass  # Race condition - child may have already done it
                    pids.append(pid)
                    pipeline_ctx.add_process(pid)
            
            # Create job entry for tracking
            job = self.job_manager.create_job(pgid, command_string)
            for i, pid in enumerate(pids):
                cmd_str = self._command_to_string(node.commands[i])
                job.add_process(pid, cmd_str)
            pipeline_ctx.job = job
            
            # Close pipes in parent
            pipeline_ctx.close_pipes()
            
            # Wait for pipeline completion
            if is_background:
                # Background pipeline
                self._background_job = job
                print(f"[{job.job_id}] {job.pgid}")
                return 0
            else:
                # Foreground pipeline - wait for completion
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                # Use job manager to wait (it handles SIGCHLD)
                exit_status = self.job_manager.wait_for_job(job)
                
                self.job_manager.set_foreground_job(None)
                
                # Remove completed job
                if job.state == JobState.DONE:
                    self.job_manager.remove_job(job.job_id)
                
                return exit_status
                
        finally:
            self._in_pipeline = old_pipeline
            self._pipeline_context = old_context
    
    def _setup_pipeline_redirections(self, index: int, pipeline_ctx: PipelineContext):
        """Set up stdin/stdout for command in pipeline."""
        # Redirect stdin from previous pipe
        stdin_fd = pipeline_ctx.get_stdin_fd(index)
        if stdin_fd is not None:
            os.dup2(stdin_fd, 0)
        
        # Redirect stdout to next pipe
        stdout_fd = pipeline_ctx.get_stdout_fd(index)
        if stdout_fd is not None:
            os.dup2(stdout_fd, 1)
        
        # Close all pipe file descriptors in child
        for read_fd, write_fd in pipeline_ctx.pipes:
            os.close(read_fd)
            os.close(write_fd)
    
    def _wait_for_pipeline(self, pipeline_ctx: PipelineContext) -> int:
        """Wait for all processes in pipeline to complete."""
        exit_statuses = []
        
        for pid in pipeline_ctx.processes:
            try:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    exit_statuses.append(os.WEXITSTATUS(status))
                elif os.WIFSIGNALED(status):
                    exit_statuses.append(128 + os.WTERMSIG(status))
                else:
                    exit_statuses.append(1)
            except OSError:
                exit_statuses.append(1)
        
        # Return exit status of last command (bash behavior)
        return exit_statuses[-1] if exit_statuses else 0
    
    def _pipeline_to_string(self, node: Pipeline) -> str:
        """Convert pipeline to string representation."""
        return " | ".join(self._command_to_string(cmd) for cmd in node.commands)
    
    def _command_to_string(self, cmd: ASTNode) -> str:
        """Convert command to string representation."""
        if isinstance(cmd, SimpleCommand):
            return " ".join(cmd.args)
        else:
            return f"<{type(cmd).__name__}>"
    
    # Simple command execution
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        """Execute a simple command (builtin or external)."""
        try:
            # Handle array assignments first
            if node.array_assignments:
                for assignment in node.array_assignments:
                    self._handle_array_assignment(assignment)
            
            # Perform expansions
            expanded_args = self._expand_arguments(node)
            
            if not expanded_args:
                return 0
            
            # Check for variable assignments
            assignments = self._extract_assignments(expanded_args)
            if assignments and len(expanded_args) == len(assignments):
                # Pure assignment (no command)
                for var, value in assignments:
                    self.state.set_variable(var, value)
                return 0
            
            # Apply assignments for this command
            saved_vars = {}
            for var, value in assignments:
                saved_vars[var] = self.state.get_variable(var)
                self.state.set_variable(var, value)
            
            try:
                # Remove assignments from args
                command_args = expanded_args[len(assignments):]
                
                # Apply redirections
                with self._apply_redirections(node.redirects):
                    # Execute command
                    if not command_args:
                        return 0
                    
                    cmd_name = command_args[0]
                    cmd_args = command_args[1:]
                    
                    # Check for empty command after expansion
                    if not cmd_name:
                        return 0
                    
                    # Execute based on command type
                    exit_status = self._execute_command(cmd_name, cmd_args, node.background)
                    
                    # Handle background jobs
                    if node.background and self._background_job:
                        print(f"[{self._background_job.job_id}] {self._background_job.pid}")
                        self._background_job = None
                    
                    return exit_status
                    
            finally:
                # Restore variables (unless exported)
                for var, old_value in saved_vars.items():
                    if not self._is_exported(var):
                        if old_value is None:
                            self.state.unset_variable(var)
                        else:
                            self.state.set_variable(var, old_value)
                
        except Exception as e:
            print(f"psh: {e}", file=sys.stderr)
            return 1
    
    def _execute_command(self, cmd_name: str, args: List[str], background: bool = False) -> int:
        """Execute a command by name."""
        # Check builtins first
        if self.builtin_registry.has(cmd_name):
            if background:
                # Builtins can't run in background
                print(f"psh: {cmd_name}: builtin commands cannot be run in background", 
                      file=sys.stderr)
                return 1
            return self._execute_builtin(cmd_name, args)
        
        # Check functions
        if self.function_manager.get_function(cmd_name):
            if background:
                # Functions can't run in background (in current implementation)
                print(f"psh: {cmd_name}: functions cannot be run in background", 
                      file=sys.stderr)
                return 1
            return self._execute_function(cmd_name, args)
        
        # Execute external command
        return self._execute_external([cmd_name] + args, background)
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        """Execute a builtin command."""
        builtin = self.builtin_registry.get(name)
        if not builtin:
            return 127  # Command not found
        
        try:
            # Use the builtin's execute method
            # The builtin will check state._in_forked_child to determine output method
            # Builtins expect the command name as the first argument
            return builtin.execute([name] + args, self.shell)
        except SystemExit as e:
            # Some builtins like 'exit' raise SystemExit
            raise
        except Exception as e:
            print(f"psh: {name}: {e}", file=sys.stderr)
            return 1
    
    def _execute_function(self, name: str, args: List[str]) -> int:
        """Execute a shell function."""
        func = self.function_manager.get_function(name)
        if not func:
            return 127  # Command not found
        
        # Save current state
        saved_params = self.state.positional_params.copy()
        saved_param_count = self.state.get_variable('#')
        saved_zero = self.state.get_variable('0')
        old_function = self._current_function
        
        try:
            # Push new variable scope for the function
            self.state.scope_manager.push_scope(name)
            self.state.function_stack.append(name)
            
            # Set function context
            self._current_function = name
            self.state.set_variable('0', name)
            self.shell.set_positional_params(args)
            
            # Execute function body
            return self.visit(func.body)
            
        except FunctionReturn as ret:
            return ret.code
        finally:
            # Pop function scope
            self.state.scope_manager.pop_scope()
            if self.state.function_stack and self.state.function_stack[-1] == name:
                self.state.function_stack.pop()
            
            # Restore state
            self.state.positional_params = saved_params
            self.state.set_variable('#', saved_param_count)
            self.state.set_variable('0', saved_zero)
            self._current_function = old_function
    
    def _execute_external(self, args: List[str], background: bool = False) -> int:
        """Execute an external command."""
        if self._in_pipeline:
            # In pipeline, use exec to replace current process
            try:
                os.execvp(args[0], args)
            except OSError as e:
                print(f"psh: {args[0]}: {e}", file=sys.stderr)
                os._exit(127)
        
        # Normal execution - fork a child process
        pid = os.fork()
        
        if pid == 0:
            # Child process
            try:
                # Set flag to indicate we're in a forked child
                self.state._in_forked_child = True
                
                # Create new process group
                os.setpgid(0, 0)
                
                # Reset signal handlers to default
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                signal.signal(signal.SIGTTIN, signal.SIG_DFL)
                
                # Execute the command
                os.execvp(args[0], args)
            except FileNotFoundError:
                # Write to stderr file descriptor
                error_msg = f"psh: {args[0]}: command not found\n"
                os.write(2, error_msg.encode('utf-8'))
                os._exit(127)
            except OSError as e:
                # Write to stderr file descriptor
                error_msg = f"psh: {args[0]}: {e}\n"
                os.write(2, error_msg.encode('utf-8'))
                os._exit(126)
        else:
            # Parent process
            # Set child's process group
            try:
                os.setpgid(pid, pid)
            except:
                pass  # Race condition - child may have already done it
            
            # Create job for tracking
            job = self.job_manager.create_job(pid, " ".join(args))
            job.add_process(pid, args[0])
            
            if background:
                # Background job
                job.foreground = False
                self._background_job = job
                self.state.last_bg_pid = pid
                print(f"[{job.job_id}] {pid}")
                return 0
            else:
                # Foreground job
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                # Use job manager to wait (it handles SIGCHLD)
                exit_status = self.job_manager.wait_for_job(job)
                
                # Clean up
                self.job_manager.set_foreground_job(None)
                if job.state == JobState.DONE:
                    self.job_manager.remove_job(job.job_id)
                
                return exit_status
    
    # Control structures
    
    def visit_IfConditional(self, node: IfConditional) -> int:
        """Execute if/then/else statement."""
        # Apply redirections to entire if statement
        with self._apply_redirections(node.redirects):
            # Evaluate main condition
            condition_status = self.visit(node.condition)
            
            if condition_status == 0:
                return self.visit(node.then_part)
            
            # Check elif conditions
            for elif_condition, elif_then in node.elif_parts:
                elif_status = self.visit(elif_condition)
                if elif_status == 0:
                    return self.visit(elif_then)
            
            # Execute else part if present
            if node.else_part:
                return self.visit(node.else_part)
            
            return 0
    
    def visit_WhileLoop(self, node: WhileLoop) -> int:
        """Execute while loop."""
        exit_status = 0
        self._loop_depth += 1
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
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
                        
            finally:
                self._loop_depth -= 1
            
        return exit_status
    
    def visit_ForLoop(self, node: ForLoop) -> int:
        """Execute for loop."""
        exit_status = 0
        self._loop_depth += 1
        
        # Expand items - create a temporary SimpleCommand for expansion
        expanded_items = []
        for item in node.items:
            # Expand variables and globs in the item
            if '$' in item:
                item = self.expansion_manager.expand_string_variables(item)
            
            # Handle glob expansion
            import glob
            matches = glob.glob(item)
            if matches:
                expanded_items.extend(matches)
            else:
                expanded_items.append(item)
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
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
                        
            finally:
                self._loop_depth -= 1
            
        return exit_status
    
    def visit_CaseConditional(self, node: CaseConditional) -> int:
        """Execute case statement."""
        # Expand the expression
        expr = node.expr
        if '$' in expr:
            expr = self.expansion_manager.expand_string_variables(expr)
        
        # Apply redirections
        with self._apply_redirections(node.redirects):
            # Try each case item
            for case_item in node.items:
                # Check if any pattern matches
                for pattern_obj in case_item.patterns:
                    # Expand pattern
                    pattern_str = pattern_obj.pattern
                    expanded_pattern = pattern_str
                    if '$' in pattern_str:
                        expanded_pattern = self.expansion_manager.expand_string_variables(pattern_str)
                    
                    if fnmatch.fnmatch(expr, expanded_pattern):
                        # Execute the commands for this case
                        exit_status = self.visit(case_item.commands)
                        
                        # Handle terminator
                        if case_item.terminator == ';;':
                            # Normal termination
                            return exit_status
                        elif case_item.terminator == ';&':
                            # Fall through to next case
                            break
                        elif case_item.terminator == ';;&':
                            # Continue testing patterns
                            continue
                        
                        return exit_status
            
            # No pattern matched
            return 0
    
    def visit_BreakStatement(self, node: BreakStatement) -> int:
        """Execute break statement."""
        if self._loop_depth == 0:
            print("psh: break: only meaningful in a loop", file=self.shell.stderr)
            return 1
        raise LoopBreak(node.level)
    
    def visit_ContinueStatement(self, node: ContinueStatement) -> int:
        """Execute continue statement."""
        if self._loop_depth == 0:
            print("psh: continue: only meaningful in a loop", file=self.shell.stderr)
            return 1
        raise LoopContinue(node.level)
    
    def visit_FunctionDef(self, node: FunctionDef) -> int:
        """Define a function."""
        self.function_manager.define_function(node.name, node.body)
        return 0
    
    # Helper methods
    
    def _expand_arguments(self, node: SimpleCommand) -> List[str]:
        """Expand all arguments in a command."""
        # Use expansion manager's expand_arguments method
        return self.expansion_manager.expand_arguments(node)
    
    def _extract_assignments(self, args: List[str]) -> List[Tuple[str, str]]:
        """Extract variable assignments from beginning of arguments."""
        assignments = []
        
        for arg in args:
            if '=' in arg and self._is_valid_assignment(arg):
                var, value = arg.split('=', 1)
                assignments.append((var, value))
            else:
                # Stop at first non-assignment
                break
        
        return assignments
    
    def _is_valid_assignment(self, arg: str) -> bool:
        """Check if argument is a valid variable assignment."""
        if '=' not in arg:
            return False
        
        var_name = arg.split('=', 1)[0]
        # Variable name must start with letter or underscore
        if not var_name or not (var_name[0].isalpha() or var_name[0] == '_'):
            return False
        
        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in var_name[1:])
    
    def _is_exported(self, var_name: str) -> bool:
        """Check if a variable is exported."""
        # This would check variable attributes when implemented
        return var_name in os.environ
    
    def _handle_array_assignment(self, assignment):
        """Handle array initialization or element assignment."""
        if isinstance(assignment, ArrayInitialization):
            # Initialize array with elements
            self.state.set_array(assignment.name, assignment.elements)
        elif isinstance(assignment, ArrayElementAssignment):
            # Set array element
            # Evaluate index
            index = self._evaluate_arithmetic(assignment.index)
            self.state.set_array_element(assignment.name, index, assignment.value)
    
    def _evaluate_arithmetic(self, expr: str) -> int:
        """Evaluate arithmetic expression."""
        # Use the shell's arithmetic evaluator
        from ..arithmetic import evaluate_arithmetic
        return evaluate_arithmetic(expr, self.shell)
    
    # Additional node type implementations
    
    def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> int:
        """Execute arithmetic command: ((expression))"""
        from ..arithmetic import evaluate_arithmetic
        
        try:
            # Apply redirections if any
            with self._apply_redirections(node.redirects):
                result = evaluate_arithmetic(node.expression, self.shell)
                # Bash behavior: exit 0 if expression is true (non-zero)
                # exit 1 if expression is false (zero)
                return 0 if result != 0 else 1
        except Exception as e:
            print(f"psh: ((: {e}", file=sys.stderr)
            return 1
    
    def visit_CStyleForLoop(self, node: CStyleForLoop) -> int:
        """Execute C-style for loop: for ((init; cond; update))"""
        from ..arithmetic import evaluate_arithmetic
        
        exit_status = 0
        self._loop_depth += 1
        
        # Evaluate init expression
        if node.init_expr:
            try:
                evaluate_arithmetic(node.init_expr, self.shell)
            except Exception as e:
                print(f"psh: ((: {e}", file=sys.stderr)
                self._loop_depth -= 1
                return 1
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            try:
                while True:
                    # Evaluate condition
                    if node.condition_expr:
                        try:
                            result = evaluate_arithmetic(node.condition_expr, self.shell)
                            if result == 0:  # Zero means false
                                break
                        except Exception as e:
                            print(f"psh: ((: {e}", file=sys.stderr)
                            exit_status = 1
                            break
                    
                    # Execute body
                    try:
                        exit_status = self.visit(node.body)
                    except LoopContinue as lc:
                        if lc.level > 1:
                            raise LoopContinue(lc.level - 1)
                    except LoopBreak as lb:
                        if lb.level > 1:
                            raise LoopBreak(lb.level - 1)
                        break
                    
                    # Evaluate update expression
                    if node.update_expr:
                        try:
                            evaluate_arithmetic(node.update_expr, self.shell)
                        except Exception as e:
                            print(f"psh: ((: {e}", file=sys.stderr)
                            exit_status = 1
                            break
                            
            finally:
                self._loop_depth -= 1
        
        return exit_status
    
    def visit_SelectLoop(self, node: SelectLoop) -> int:
        """Execute select loop."""
        # Select loops are complex due to their interactive nature
        # For now, we'll provide a basic implementation
        print("ExecutorVisitor: SelectLoop not fully implemented", file=sys.stderr)
        return 1
    
    def visit_EnhancedTestStatement(self, node: EnhancedTestStatement) -> int:
        """Execute enhanced test: [[ expression ]]"""
        # Delegate to shell's existing implementation
        return self.shell.execute_enhanced_test_statement(node)
    
    # Fallback for unimplemented nodes
    
    def generic_visit(self, node: ASTNode) -> int:
        """Fallback for unimplemented node types."""
        node_name = type(node).__name__
        
        # Try to handle some common unimplemented nodes
        if node_name == "CommandList":
            # CommandList is likely an alias for StatementList
            return self.visit_StatementList(node)
        
        print(f"ExecutorVisitor: Unimplemented node type: {node_name}", 
              file=sys.stderr)
        return 1