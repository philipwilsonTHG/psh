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
    ProcessSubstitution, SubshellGroup
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
                print("break: only meaningful in a `for' or `while' loop", file=sys.stderr)
                exit_status = 1
                self.state.last_exit_code = exit_status
            except LoopContinue:
                # Continue at top level is an error
                print("continue: only meaningful in a `for' or `while' loop", file=sys.stderr)
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
            try:
                exit_status = self.visit(statement)
                # Update $? after each statement
                self.state.last_exit_code = exit_status
            except FunctionReturn:
                # Function return should propagate up
                raise
            except (LoopBreak, LoopContinue):
                # Re-raise if we're in a loop, otherwise it's an error
                if self._loop_depth > 0:
                    raise
                # Not in a loop - this was already reported by visit_BreakStatement/visit_ContinueStatement
                exit_status = 1
                self.state.last_exit_code = exit_status
                # Don't continue executing statements after break/continue error
                break
        
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
                
                # Give terminal control to the pipeline
                try:
                    original_pgid = os.tcgetpgrp(0)
                    os.tcsetpgrp(0, pgid)
                except:
                    original_pgid = None
                
                # Use job manager to wait (it handles SIGCHLD)
                if self.state.options.get('pipefail') and len(node.commands) > 1:
                    # Get all exit statuses for pipefail
                    all_statuses = self.job_manager.wait_for_job(job, collect_all_statuses=True)
                    if isinstance(all_statuses, list):
                        # Return rightmost non-zero exit status, or 0 if all succeeded
                        exit_status = 0
                        for status in reversed(all_statuses):
                            if status != 0:
                                exit_status = status
                                break
                    else:
                        exit_status = all_statuses
                else:
                    # Normal behavior: return exit status of last command
                    exit_status = self.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
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
            # Convert args to strings (in case they're RichToken objects)
            str_args = [str(arg) for arg in cmd.args]
            return " ".join(str_args)
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
                # Handle xtrace for assignments
                if self.state.options.get('xtrace'):
                    ps4 = self.state.get_variable('PS4', '+ ')
                    for var, value in assignments:
                        trace_line = ps4 + f"{var}={value}\n"
                        self.state.stderr.write(trace_line)
                        self.state.stderr.flush()
                
                # Save the current exit code before expansions
                saved_exit_code = self.state.last_exit_code
                
                for var, value in assignments:
                    # Apply all expansions to assignment values
                    value = self._expand_assignment_value(value)
                    self.state.set_variable(var, value)
                
                # If any command substitution happened during expansion, it will have set last_exit_code
                # Return the current exit code (which will be from command substitution if any)
                # Otherwise return the saved exit code
                return self.state.last_exit_code
            
            # Apply assignments for this command
            saved_vars = {}
            for var, value in assignments:
                saved_vars[var] = self.state.get_variable(var)
                # Apply all expansions to assignment values
                value = self._expand_assignment_value(value)
                self.state.set_variable(var, value)
            
            try:
                # Remove assignments from args
                command_args = expanded_args[len(assignments):]
                
                # Special handling for exec builtin
                if command_args and command_args[0] == 'exec':
                    return self._handle_exec_builtin(node, command_args, assignments)
                
                # Check if this is a builtin that needs special redirection handling
                if command_args and self.builtin_registry.has(command_args[0]) and not self._in_pipeline:
                    # DEBUG: Log builtin redirection setup
                    if self.state.options.get('debug-exec'):
                        print(f"DEBUG ExecutorVisitor: Setting up builtin redirections for '{command_args[0]}'", file=sys.stderr)
                        print(f"DEBUG ExecutorVisitor: Redirections: {[r.type for r in node.redirects]}", file=sys.stderr)
                    
                    # Builtins need special redirection handling
                    stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup = \
                        self.io_manager.setup_builtin_redirections(node)
                    try:
                        # Update shell streams for builtins that might use them
                        self.shell.stdout = sys.stdout
                        self.shell.stderr = sys.stderr
                        self.shell.stdin = sys.stdin
                        
                        # Execute command
                        if not command_args:
                            return 0
                        
                        cmd_name = command_args[0]
                        cmd_args = command_args[1:]
                        
                        # Check for empty command after expansion
                        if not cmd_name:
                            return 0
                        
                        # Handle xtrace option
                        if self.state.options.get('xtrace'):
                            # Get PS4 prompt (default "+ ")
                            ps4 = self.state.get_variable('PS4', '+ ')
                            # Print command to stderr
                            trace_line = ps4 + ' '.join([cmd_name] + cmd_args) + '\n'
                            self.state.stderr.write(trace_line)
                            self.state.stderr.flush()
                        
                        # Execute builtin
                        exit_status = self._execute_builtin(cmd_name, cmd_args)
                        
                        return exit_status
                    finally:
                        self.io_manager.restore_builtin_redirections(
                            stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup
                        )
                        # Reset shell stream references to current sys streams
                        # This avoids holding onto closed/captured streams
                        # However, preserve StringIO objects for test frameworks
                        import io
                        if not isinstance(self.shell.stdout, io.StringIO):
                            self.shell.stdout = sys.stdout
                        if not isinstance(self.shell.stderr, io.StringIO):
                            self.shell.stderr = sys.stderr
                        if not isinstance(self.shell.stdin, io.StringIO):
                            self.shell.stdin = sys.stdin
                else:
                    # Apply normal redirections for external commands or builtins in pipelines
                    with self._apply_redirections(node.redirects):
                        # Execute command
                        if not command_args:
                            return 0
                        
                        cmd_name = command_args[0]
                        cmd_args = command_args[1:]
                        
                        # Check for empty command after expansion
                        if not cmd_name:
                            return 0
                        
                        # Handle xtrace option
                        if self.state.options.get('xtrace'):
                            # Get PS4 prompt (default "+ ")
                            ps4 = self.state.get_variable('PS4', '+ ')
                            # Print command to stderr
                            trace_line = ps4 + ' '.join([cmd_name] + cmd_args) + '\n'
                            self.state.stderr.write(trace_line)
                            self.state.stderr.flush()
                        
                        # Execute based on command type
                        exit_status = self._execute_command(cmd_name, cmd_args, node.background, node.redirects)
                        
                        # Clear background job reference
                        if node.background and self._background_job:
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
                
        except FunctionReturn:
            # Function return must propagate
            raise
        except (LoopBreak, LoopContinue):
            # Loop control must propagate
            raise
        except SystemExit:
            # Exit must propagate
            raise
        except Exception as e:
            print(f"psh: {e}", file=sys.stderr)
            return 1
    
    def _execute_command(self, cmd_name: str, args: List[str], background: bool = False, redirects: List[Redirect] = None) -> int:
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
        return self._execute_external([cmd_name] + args, background, redirects)
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        """Execute a builtin command."""
        builtin = self.builtin_registry.get(name)
        if not builtin:
            return 127  # Command not found
        
        # DEBUG: Log builtin execution
        if self.state.options.get('debug-exec'):
            print(f"DEBUG ExecutorVisitor: executing builtin '{name}' with args {args}", file=sys.stderr)
            print(f"DEBUG ExecutorVisitor: _in_pipeline={self._in_pipeline}, _in_forked_child={self.state._in_forked_child}", file=sys.stderr)
        
        try:
            # Use the builtin's execute method
            # The builtin will check state._in_forked_child to determine output method
            # Builtins expect the command name as the first argument
            return builtin.execute([name] + args, self.shell)
        except SystemExit as e:
            # Some builtins like 'exit' raise SystemExit
            raise
        except FunctionReturn as e:
            # FunctionReturn must propagate to be caught by function execution
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
        
        # Save terminal attributes if in interactive mode
        saved_attrs = None
        if hasattr(sys, 'stdin') and sys.stdin.isatty():
            try:
                import termios
                saved_attrs = termios.tcgetattr(0)
            except:
                saved_attrs = None
        
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
            return ret.exit_code
        except (LoopBreak, LoopContinue) as e:
            # If we're called from within a loop, propagate the exception
            if self._loop_depth > 0:
                raise
            # Otherwise, it's an error
            stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
            print(f"{stmt_name}: only meaningful in a `for' or `while' loop", 
                  file=sys.stderr)
            return 1
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
            
            # Restore terminal attributes if they were saved
            if saved_attrs is not None:
                try:
                    import termios
                    termios.tcsetattr(0, termios.TCSANOW, saved_attrs)
                except:
                    pass
    
    def _execute_external(self, args: List[str], background: bool = False, redirects: List[Redirect] = None) -> int:
        """Execute an external command."""
        if self._in_pipeline:
            # In pipeline, use exec to replace current process
            try:
                # Set up redirections if any
                if redirects:
                    # Create a dummy command object for the io_manager
                    from ..ast_nodes import SimpleCommand
                    temp_command = SimpleCommand(args=args, redirects=redirects)
                    self.io_manager.setup_child_redirections(temp_command)
                
                os.execvp(args[0], args)
            except OSError as e:
                print(f"psh: {args[0]}: {e}", file=sys.stderr)
                os._exit(127)
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
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
                
                # Set up redirections if any
                if redirects:
                    # Create a dummy command object for the io_manager
                    from ..ast_nodes import SimpleCommand
                    temp_command = SimpleCommand(args=args, redirects=redirects)
                    self.io_manager.setup_child_redirections(temp_command)
                
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
            job = self.job_manager.create_job(pid, " ".join(str(arg) for arg in args))
            job.add_process(pid, str(args[0]))
            
            if background:
                # Background job
                job.foreground = False
                self._background_job = job
                self.state.last_bg_pid = pid
                print(f"[{job.job_id}] {pid}")
                return 0
            else:
                # Foreground job - give it terminal control
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                if original_pgid is not None:
                    self.state.foreground_pgid = pid
                    try:
                        os.tcsetpgrp(0, pid)
                    except:
                        pass
                
                # Use job manager to wait (it handles SIGCHLD)
                exit_status = self.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    self.state.foreground_pgid = None
                    self.job_manager.set_foreground_job(None)
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
                # Clean up
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
        
        # Expand items - handle all types of expansion, respecting quote types
        expanded_items = []
        quote_types = getattr(node, 'item_quote_types', [None] * len(node.items))
        
        for i, item in enumerate(node.items):
            quote_type = quote_types[i] if i < len(quote_types) else None
            
            # Check if this is an array expansion
            if '$' in item and self.expansion_manager.variable_expander.is_array_expansion(item):
                # Expand array to list of items
                array_items = self.expansion_manager.variable_expander.expand_array_to_list(item)
                expanded_items.extend(array_items)
            else:
                # Perform full expansion on the item
                # Determine the type of the item (check arithmetic first since it starts with $()
                if item.startswith('$((') and item.endswith('))'):
                    # Arithmetic expansion
                    result = self.expansion_manager.execute_arithmetic_expansion(item)
                    # Arithmetic expansion always produces a single value
                    expanded_items.append(str(result))
                elif item.startswith('$(') and item.endswith(')'):
                    # Command substitution
                    output = self.expansion_manager.execute_command_substitution(item)
                    # For quoted command substitution, don't word split
                    if quote_type == '"':
                        expanded_items.append(output if output else "")
                    else:
                        # Split on whitespace for word splitting
                        if output:
                            words = output.split()
                            expanded_items.extend(words)
                elif item.startswith('`') and item.endswith('`'):
                    # Backtick command substitution
                    output = self.expansion_manager.execute_command_substitution(item)
                    # For quoted command substitution, don't word split
                    if quote_type == '"':
                        expanded_items.append(output if output else "")
                    else:
                        # Split on whitespace for word splitting
                        if output:
                            words = output.split()
                            expanded_items.extend(words)
                elif '$' in item:
                    # Variable expansion
                    expanded = self.expansion_manager.expand_string_variables(item)
                    
                    if quote_type == '"':
                        # Double-quoted: no word splitting, no glob expansion
                        expanded_items.append(expanded if expanded else "")
                    elif quote_type == "'":
                        # Single-quoted: no expansion at all (but shouldn't happen here since we have $)
                        expanded_items.append(item)
                    else:
                        # Unquoted: word splitting and glob expansion
                        import re
                        # Get IFS for field splitting
                        ifs = self.state.get_variable('IFS', ' \t\n')
                        if ifs:
                            # Create regex pattern from IFS characters
                            ifs_pattern = '[' + re.escape(ifs) + ']+'
                            words = re.split(ifs_pattern, expanded.strip()) if expanded.strip() else []
                        else:
                            # No IFS means no field splitting
                            words = [expanded] if expanded else []
                        
                        # Handle glob expansion on each word
                        import glob
                        for word in words:
                            if word:  # Skip empty words
                                matches = glob.glob(word)
                                if matches:
                                    expanded_items.extend(matches)
                                else:
                                    expanded_items.append(word)
                else:
                    # No expansion needed
                    if quote_type:
                        # Quoted literal
                        expanded_items.append(item)
                    else:
                        # Unquoted literal - check for glob expansion
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
            print("break: only meaningful in a `for' or `while' loop", file=self.shell.stderr)
            # Raise exception even outside loop so StatementList stops executing
            raise LoopBreak(node.level)
        raise LoopBreak(node.level)
    
    def visit_ContinueStatement(self, node: ContinueStatement) -> int:
        """Execute continue statement."""
        if self._loop_depth == 0:
            print("continue: only meaningful in a `for' or `while' loop", file=self.shell.stderr)
            # Raise exception even outside loop so StatementList stops executing
            raise LoopContinue(node.level)
        raise LoopContinue(node.level)
    
    def visit_SubshellGroup(self, node: SubshellGroup) -> int:
        """Execute subshell group (...) in isolated environment."""
        return self._execute_in_subshell(node.statements, node.redirects, node.background)
    
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
        # This is now handled by visit_ArrayInitialization and visit_ArrayElementAssignment
        if isinstance(assignment, ArrayInitialization):
            return self.visit_ArrayInitialization(assignment)
        elif isinstance(assignment, ArrayElementAssignment):
            return self.visit_ArrayElementAssignment(assignment)
        return 0
    
    def _evaluate_arithmetic(self, expr: str) -> int:
        """Evaluate arithmetic expression."""
        # Use the shell's arithmetic evaluator
        from ..arithmetic import evaluate_arithmetic
        return evaluate_arithmetic(expr, self.shell)
    
    def _expand_assignment_value(self, value: str) -> str:
        """Expand a value used in variable assignment."""
        # Handle all expansions in order, without word splitting
        
        # 1. Tilde expansion (only at start)
        if value.startswith('~'):
            value = self.expansion_manager.expand_tilde(value)
        
        # 2. Variable expansion (including ${var} forms)
        if '$' in value:
            # We need to handle command substitution separately from variable expansion
            # to preserve the exact semantics
            result = []
            i = 0
            while i < len(value):
                if i < len(value) - 1 and value[i:i+2] == '$(':
                    # Find matching )
                    paren_count = 1
                    j = i + 2
                    while j < len(value) and paren_count > 0:
                        if value[j] == '(':
                            paren_count += 1
                        elif value[j] == ')':
                            paren_count -= 1
                        j += 1
                    if paren_count == 0:
                        # Found complete command substitution
                        cmd_sub = value[i:j]
                        output = self.expansion_manager.execute_command_substitution(cmd_sub)
                        result.append(output)
                        i = j
                        continue
                elif value[i] == '`':
                    # Find matching backtick
                    j = i + 1
                    while j < len(value) and value[j] != '`':
                        j += 1
                    if j < len(value):
                        # Found complete backtick command substitution
                        cmd_sub = value[i:j+1]
                        output = self.expansion_manager.execute_command_substitution(cmd_sub)
                        result.append(output)
                        i = j + 1
                        continue
                elif i < len(value) - 2 and value[i:i+3] == '$((': 
                    # Arithmetic expansion
                    # Find matching ))
                    paren_count = 2
                    j = i + 3
                    while j < len(value) and paren_count > 0:
                        if value[j] == '(':
                            paren_count += 1
                        elif value[j] == ')':
                            paren_count -= 1
                        j += 1
                    if paren_count == 0:
                        # Found complete arithmetic expression
                        arith_expr = value[i:j]
                        result.append(str(self.expansion_manager.execute_arithmetic_expansion(arith_expr)))
                        i = j
                        continue
                
                result.append(value[i])
                i += 1
            
            value = ''.join(result)
            
            # Now expand remaining variables
            value = self.expansion_manager.expand_string_variables(value)
        
        return value
    
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
        """Execute select loop for interactive menu selection."""
        exit_status = 0
        self._loop_depth += 1
        
        # Expand items
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
        
        # Empty list - exit immediately
        if not expanded_items:
            self._loop_depth -= 1
            return 0
        
        # Apply redirections for entire loop
        with self._apply_redirections(node.redirects):
            try:
                # Get PS3 prompt (default "#? " if not set)
                ps3 = self.state.get_variable("PS3", "#? ")
                
                while True:
                    # Display menu to stderr
                    self._display_select_menu(expanded_items)
                    
                    # Show prompt and read input
                    try:
                        sys.stderr.write(ps3)
                        sys.stderr.flush()
                        
                        # Read input line
                        if hasattr(self.shell, 'stdin') and self.shell.stdin:
                            # Use shell's stdin if available (set by I/O redirection)
                            reply = self.shell.stdin.readline()
                        else:
                            # Use sys.stdin as fallback
                            if sys.stdin is None or sys.stdin.closed:
                                raise EOFError
                            try:
                                reply = sys.stdin.readline()
                            except (OSError, ValueError):
                                # Handle case where stdin is not available in test environment
                                raise EOFError
                        
                        if not reply:  # EOF
                            raise EOFError
                        reply = reply.rstrip('\n')
                    except (EOFError, KeyboardInterrupt):
                        # Ctrl+D or Ctrl+C exits the loop
                        sys.stderr.write("\n")
                        break
                    
                    # Set REPLY variable
                    self.state.set_variable("REPLY", reply)
                    
                    # Process selection
                    if reply.strip().isdigit():
                        choice = int(reply.strip())
                        if 1 <= choice <= len(expanded_items):
                            # Valid selection
                            selected = expanded_items[choice - 1]
                            self.state.set_variable(node.variable, selected)
                        else:
                            # Out of range
                            self.state.set_variable(node.variable, "")
                    else:
                        # Non-numeric input
                        self.state.set_variable(node.variable, "")
                    
                    # Execute loop body
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
            except KeyboardInterrupt:
                sys.stderr.write("\n")
                exit_status = 130
            finally:
                self._loop_depth -= 1
        
        return exit_status
    
    def _display_select_menu(self, items: List[str]) -> None:
        """Display the select menu to stderr."""
        # Calculate layout
        num_items = len(items)
        if num_items <= 9:
            # Single column for small lists
            for i, item in enumerate(items, 1):
                sys.stderr.write(f"{i}) {item}\n")
        else:
            # Multi-column for larger lists
            columns = 2 if num_items <= 20 else 3
            rows = (num_items + columns - 1) // columns
            
            # Calculate column widths
            col_width = max(len(f"{i}) {items[i-1]}") for i in range(1, num_items + 1)) + 3
            
            for row in range(rows):
                for col in range(columns):
                    idx = row + col * rows
                    if idx < num_items:
                        entry = f"{idx + 1}) {items[idx]}"
                        sys.stderr.write(entry.ljust(col_width))
                sys.stderr.write("\n")
    
    def visit_EnhancedTestStatement(self, node: EnhancedTestStatement) -> int:
        """Execute enhanced test: [[ expression ]]"""
        # Delegate to shell's existing implementation
        return self.shell.execute_enhanced_test_statement(node)
    
    # Array operations
    
    def visit_ArrayInitialization(self, node: ArrayInitialization) -> int:
        """Execute array initialization: arr=(a b c)"""
        # Handle append mode
        from ..core.variables import IndexedArray, VarAttributes
        
        if node.is_append:
            # Get existing array or create new one
            var_obj = self.state.scope_manager.get_variable_object(node.name)
            if var_obj and isinstance(var_obj.value, IndexedArray):
                array = var_obj.value
                # Find next index for appending
                start_index = max(array._elements.keys()) + 1 if array._elements else 0
            else:
                array = IndexedArray()
                start_index = 0
        else:
            # Create new array
            array = IndexedArray()
            start_index = 0
        
        # Expand and add elements
        next_sequential_index = start_index
        
        for i, element in enumerate(node.elements):
            element_type = node.element_types[i] if i < len(node.element_types) else 'WORD'
            
            # Check if this is an explicit index assignment: [index]=value
            if element_type in ('COMPOSITE', 'COMPOSITE_QUOTED') and self._is_explicit_array_assignment(element):
                # Parse explicit index assignment (this will handle expansion internally)
                index, value = self._parse_explicit_array_assignment(element)
                if index is not None:
                    # Evaluate arithmetic in index (bash always evaluates indices as arithmetic)
                    try:
                        from ..arithmetic import evaluate_arithmetic
                        evaluated_index = evaluate_arithmetic(str(index), self.shell)
                        array.set(evaluated_index, value)
                        # Update next sequential index to be after this explicit index
                        next_sequential_index = max(next_sequential_index, evaluated_index + 1)
                    except (ValueError, Exception):
                        # If index evaluation fails, treat as regular sequential element
                        next_sequential_index = self._add_expanded_element_to_array(
                            array, element, next_sequential_index, split_words=False)
                else:
                    # Failed to parse as explicit assignment, treat as regular element
                    next_sequential_index = self._add_expanded_element_to_array(
                        array, element, next_sequential_index, split_words=False)
            elif element_type in ('WORD', 'COMPOSITE'):
                # Split unquoted words/composites on whitespace for sequential assignment with glob expansion
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=True)
            elif element_type in ('COMMAND_SUB', 'ARITH_EXPANSION', 'VARIABLE'):
                # Command substitution, arithmetic expansion, and variables should be word-split in arrays
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=True)
            else:
                # Keep as single element for sequential assignment (STRING, etc.)
                # Quoted strings should not be glob expanded or word split
                next_sequential_index = self._add_expanded_element_to_array(
                    array, element, next_sequential_index, split_words=False)
        
        # Set array in shell state
        self.state.scope_manager.set_variable(node.name, array, attributes=VarAttributes.ARRAY)
        return 0
    
    def visit_ArrayElementAssignment(self, node: ArrayElementAssignment) -> int:
        """Execute array element assignment: arr[i]=value"""
        # Handle index - can be string or list of tokens
        if isinstance(node.index, list):
            # Expand each token if it's a variable
            expanded_parts = []
            for token in node.index:
                if hasattr(token, 'type') and str(token.type) == 'TokenType.VARIABLE':
                    # This is a variable token, expand it
                    var_name = token.value
                    expanded_parts.append(self.state.get_variable(var_name, ''))
                else:
                    # Regular token, use its value
                    expanded_parts.append(token.value if hasattr(token, 'value') else str(token))
            index_str = ''.join(expanded_parts)
        else:
            index_str = node.index
        
        # Expand any remaining variables in the index (e.g., ${var})
        expanded_index = self.expansion_manager.expand_string_variables(index_str)
        
        # Get the variable to check if it's an associative array
        from ..core.variables import IndexedArray, AssociativeArray, VarAttributes
        var_obj = self.state.scope_manager.get_variable_object(node.name)
        
        # Determine index type based on array type
        if var_obj and isinstance(var_obj.value, AssociativeArray):
            # For associative arrays, index is always a string
            index = expanded_index
        else:
            # For indexed arrays, evaluate arithmetic if needed
            try:
                if any(op in expanded_index for op in ['+', '-', '*', '/', '%', '(', ')']):
                    from ..arithmetic import evaluate_arithmetic
                    index = evaluate_arithmetic(expanded_index, self.shell)
                else:
                    index = int(expanded_index)
            except (ValueError, Exception):
                print(f"psh: {node.name}[{index_str}]: bad array subscript", file=sys.stderr)
                return 1
        
        # Expand value
        expanded_value = self.expansion_manager.expand_string_variables(node.value)
        
        # Get or create array
        if var_obj and (isinstance(var_obj.value, IndexedArray) or isinstance(var_obj.value, AssociativeArray)):
            array = var_obj.value
        else:
            # Create new indexed array by default
            array = IndexedArray()
            self.state.scope_manager.set_variable(node.name, array, attributes=VarAttributes.ARRAY)
        
        # Handle append mode
        if node.is_append:
            # Get current value and append
            current = array.get(index)
            if current is not None:
                expanded_value = current + expanded_value
        
        # Set element
        array.set(index, expanded_value)
        return 0
    
    # Exec builtin implementation
    
    def _handle_exec_builtin(self, node: SimpleCommand, command_args: List[str], assignments: List[tuple]) -> int:
        """Handle exec builtin with access to redirections."""
        exec_args = command_args[1:]  # Remove 'exec' itself
        
        # Handle xtrace option
        if self.state.options.get('xtrace'):
            ps4 = self.state.get_variable('PS4', '+ ')
            trace_line = ps4 + ' '.join(command_args) + '\n'
            self.state.stderr.write(trace_line)
            self.state.stderr.flush()
        
        # Apply environment variable assignments permanently for exec
        for var, value in assignments:
            expanded_value = self._expand_assignment_value(value)
            self.state.set_variable(var, expanded_value)
            # Also set in environment for exec
            os.environ[var] = expanded_value
        
        try:
            if exec_args:
                # Mode 1: exec with command - replace the shell process
                return self._exec_with_command(node, exec_args)
            else:
                # Mode 2: exec without command - apply redirections permanently
                return self._exec_without_command(node)
                
        except OSError as e:
            if e.errno == 2:  # No such file or directory
                print(f"exec: {exec_args[0]}: command not found", file=sys.stderr)
                return 127
            elif e.errno == 13:  # Permission denied  
                print(f"exec: {exec_args[0]}: Permission denied", file=sys.stderr)
                return 126
            else:
                print(f"exec: {exec_args[0]}: {e}", file=sys.stderr)
                return 126
        except Exception as e:
            print(f"exec: {e}", file=sys.stderr)
            return 1
    
    def _exec_with_command(self, node: SimpleCommand, args: List[str]) -> int:
        """Handle exec with command - replace the shell process."""
        cmd_name = args[0]
        cmd_args = args
        
        # Apply redirections before exec
        if node.redirects:
            try:
                # Apply redirections permanently (don't restore them)
                self.io_manager.apply_permanent_redirections(node.redirects)
            except Exception as e:
                print(f"exec: {e}", file=sys.stderr)
                return 1
        
        # exec bypasses builtins and functions - look for external command in PATH
        command_path = self._find_command_in_path(cmd_name)
        if not command_path:
            print(f"exec: {cmd_name}: command not found", file=sys.stderr)
            return 127
        
        # Check if command is executable
        if not os.access(command_path, os.X_OK):
            print(f"exec: {cmd_name}: Permission denied", file=sys.stderr)
            return 126
        
        # Reset signal handlers to default
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGQUIT, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        
        # Replace the current process with the command
        try:
            os.execv(command_path, cmd_args)
        except OSError as e:
            # This should not return, but if it does, there was an error
            print(f"exec: {cmd_name}: {e}", file=sys.stderr)
            return 126
    
    def _exec_without_command(self, node: SimpleCommand) -> int:
        """Handle exec without command - apply redirections permanently."""
        if not node.redirects:
            # No redirections, just return success
            return 0
        
        try:
            # Apply redirections permanently (don't restore them)
            self.io_manager.apply_permanent_redirections(node.redirects)
            return 0
        except Exception as e:
            print(f"exec: {e}", file=sys.stderr)
            return 1
    
    def _find_command_in_path(self, cmd_name: str) -> str:
        """Find command in PATH, return full path or None."""
        # If command contains '/', it's a path
        if '/' in cmd_name:
            if os.path.isfile(cmd_name):
                return cmd_name
            return None
        
        # Search in PATH
        path_env = os.environ.get('PATH', '')
        for path_dir in path_env.split(':'):
            if not path_dir:
                continue
            full_path = os.path.join(path_dir, cmd_name)
            if os.path.isfile(full_path):
                return full_path
        
        return None
    
    # Array assignment helper methods
    
    def _add_expanded_element_to_array(self, array, element: str, start_index: int, split_words: bool = True) -> int:
        """
        Add expanded element to array with glob expansion.
        
        Args:
            array: The array to add elements to
            element: The element to expand and add
            start_index: Starting index for sequential assignment
            split_words: Whether to split on whitespace after expansion
            
        Returns:
            Next available index after adding elements
        """
        # Expand variables first  
        expanded = self.expansion_manager.expand_string_variables(element)
        
        if split_words:
            # Split on whitespace for WORD and command substitution elements
            words = expanded.split()
        else:
            # Keep as single element for STRING and composite elements
            words = [expanded] if expanded else ['']
        
        # Handle glob expansion on each word (like for loops do)
        import glob
        next_index = start_index
        for word in words:
            matches = glob.glob(word)
            if matches:
                # Glob pattern matched files - add all matches
                for match in sorted(matches):
                    array.set(next_index, match)
                    next_index += 1
            else:
                # No matches, add literal word
                array.set(next_index, word)
                next_index += 1
        
        return next_index
    
    def _is_explicit_array_assignment(self, element: str) -> bool:
        """Check if element has explicit array assignment syntax: [index]=value"""
        import re
        # Match [anything]=anything pattern
        return bool(re.match(r'^\[[^\]]*\]=', element))
    
    def _parse_explicit_array_assignment(self, element: str) -> tuple:
        """
        Parse explicit array assignment: [index]=value
        
        Returns:
            tuple: (index, value) or (None, None) if parsing fails
        """
        import re
        match = re.match(r'^\[([^\]]*)\]=(.*)$', element)
        if match:
            index_str = match.group(1)
            value = match.group(2)
            
            # Expand any variables in the index
            expanded_index = self.expansion_manager.expand_string_variables(index_str)
            expanded_value = self.expansion_manager.expand_string_variables(value)
            
            return expanded_index, expanded_value
        
        return None, None
    
    def _execute_in_subshell(self, statements: 'CommandList', redirects: List['Redirect'], background: bool) -> int:
        """Execute statements in an isolated subshell environment."""
        if background:
            # Handle background subshell - for now, treat as foreground
            # TODO: Implement proper background job management for subshells
            pass
        
        # Execute in foreground subshell with proper isolation
        return self._execute_foreground_subshell(statements, redirects)
    
    def _execute_foreground_subshell(self, statements: 'CommandList', redirects: List['Redirect']) -> int:
        """Execute subshell in foreground with proper isolation."""
        pid = os.fork()
        
        if pid == 0:
            # Child process - create isolated shell
            try:
                # Create new process group for the subshell
                os.setpgid(0, 0)
                
                # Import Shell here to avoid circular import
                from ..shell import Shell
                
                # Create new shell instance with copied environment
                subshell = Shell(
                    debug_ast=self.shell.state.debug_ast,
                    debug_tokens=self.shell.state.debug_tokens,
                    parent_shell=self.shell,  # Copy variables/functions
                    norc=True
                )
                subshell.state._in_forked_child = True
                
                # Inherit I/O streams from parent shell for test compatibility
                subshell.stdout = self.shell.stdout
                subshell.stderr = self.shell.stderr
                subshell.stdin = self.shell.stdin
                
                # Apply redirections if any
                saved_fds = None
                if redirects:
                    saved_fds = subshell.io_manager.apply_redirections(redirects)
                
                # Execute statements in isolated environment  
                exit_code = subshell.execute_command_list(statements)
                os._exit(exit_code)
                
            except SystemExit as e:
                # Handle explicit exit calls
                os._exit(e.code if e.code is not None else 0)
            except Exception as e:
                print(f"psh: subshell error: {e}", file=sys.stderr)
                os._exit(1)
        else:
            # Parent process - use job manager to wait for child
            try:
                # Set the child's process group 
                os.setpgid(pid, pid)
            except OSError:
                # Race condition - child may have already done it
                pass
            
            # Create job for tracking the subshell
            job = self.job_manager.create_job(pid, "<subshell>")
            job.add_process(pid, "subshell")
            job.foreground = True
            
            # Use job manager to wait (handles SIGCHLD properly)
            exit_status = self.job_manager.wait_for_job(job)
            
            # Clean up job
            if job.state.name == 'DONE':
                self.job_manager.remove_job(job.job_id)
            
            return exit_status
    
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