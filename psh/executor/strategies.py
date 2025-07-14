"""
Execution strategies for different command types.

This module implements the Strategy pattern for command execution,
providing different strategies for builtins, functions, and external commands.
"""

import os
import sys
import signal
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..shell import Shell
    from ..ast_nodes import SimpleCommand, Redirect
    from .context import ExecutionContext
    from ..job_control import Job


class ExecutionStrategy(ABC):
    """Abstract base class for command execution strategies."""
    
    @abstractmethod
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """Check if this strategy can execute the given command."""
        pass
    
    @abstractmethod
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context: 'ExecutionContext',
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute the command and return exit status."""
        pass


class BuiltinExecutionStrategy(ExecutionStrategy):
    """Strategy for executing builtin commands."""
    
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """Check if command is a builtin."""
        return shell.builtin_registry.has(cmd_name)
    
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context: 'ExecutionContext',
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute a builtin command."""
        if background:
            # Run builtin in background by forking a subshell (bash compatibility)
            return self._execute_builtin_in_background(cmd_name, args, shell, context, redirects)
        
        builtin = shell.builtin_registry.get(cmd_name)
        if not builtin:
            return 127  # Command not found
        
        # DEBUG: Log builtin execution
        if shell.state.options.get('debug-exec'):
            print(f"DEBUG BuiltinStrategy: executing builtin '{cmd_name}' with args {args}", 
                  file=sys.stderr)
            print(f"DEBUG BuiltinStrategy: in_pipeline={context.in_pipeline}, "
                  f"in_forked_child={context.in_forked_child}", file=sys.stderr)
        
        try:
            # Use the builtin's execute method
            # The builtin will check context.in_forked_child to determine output method
            # Builtins expect the command name as the first argument
            return builtin.execute([cmd_name] + args, shell)
        except SystemExit as e:
            # Some builtins like 'exit' raise SystemExit
            raise
        except Exception as e:
            # Import FunctionReturn here to avoid circular imports
            from ..builtins.function_support import FunctionReturn
            if isinstance(e, FunctionReturn):
                # FunctionReturn must propagate to be caught by function execution
                raise
            print(f"psh: {cmd_name}: {e}", file=sys.stderr)
            return 1
    
    def _execute_builtin_in_background(self, cmd_name: str, args: List[str], 
                                     shell: 'Shell', context: 'ExecutionContext',
                                     redirects: Optional[List['Redirect']] = None) -> int:
        """Execute a builtin command in background by forking a subshell."""
        import os
        import sys
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        # Fork a child process to run the builtin
        pid = os.fork()
        
        if pid == 0:
            # Child process - run the builtin in a subshell
            try:
                # Set flag to indicate we're in a forked child
                shell.state._in_forked_child = True
                
                # Create new process group
                os.setpgid(0, 0)
                
                # Reset signal handlers for child
                import signal
                signal.signal(signal.SIGINT, signal.SIG_DFL)
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                signal.signal(signal.SIGTTIN, signal.SIG_DFL)
                
                # Apply redirections if any
                if redirects:
                    from ..ast_nodes import SimpleCommand
                    temp_command = SimpleCommand(args=[cmd_name] + args, redirects=redirects)
                    shell.io_manager.setup_child_redirections(temp_command)
                
                # Execute the builtin
                builtin = shell.builtin_registry.get(cmd_name)
                if builtin:
                    exit_code = builtin.execute([cmd_name] + args, shell)
                    os._exit(exit_code)
                else:
                    os._exit(127)
                    
            except Exception as e:
                print(f"psh: {cmd_name}: {e}", file=sys.stderr)
                os._exit(1)
        else:
            # Parent process - set up job control
            try:
                # Set child's process group
                os.setpgid(pid, pid)
            except OSError:
                pass  # Child may have already set it
            
            # Create job and register it
            job = shell.job_manager.create_job(pid, f"{cmd_name} {' '.join(args)}")
            job.add_process(pid, cmd_name)
            job.foreground = False
            shell.state.last_bg_pid = pid
            
            # Print job assignment notification (only in interactive mode)
            if not shell.state.is_script_mode:
                print(f"[{job.job_id}] {pid}")
            
            return 0


class FunctionExecutionStrategy(ExecutionStrategy):
    """Strategy for executing shell functions."""
    
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """Check if command is a defined function."""
        return shell.function_manager.get_function(cmd_name) is not None
    
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context: 'ExecutionContext',
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute a shell function."""
        if background:
            # Functions can't run in background (in current implementation)
            print(f"psh: {cmd_name}: functions cannot be run in background", 
                  file=sys.stderr)
            return 1
        
        # Import here to avoid circular imports
        from .function import FunctionOperationExecutor
        
        # Create a function executor to handle the call
        # Pass the current context to preserve loop depth and other state
        function_executor = FunctionOperationExecutor(shell)
        
        # We need a visitor for function execution, but we need to preserve the context
        # The issue is that we need the visitor that called this strategy
        # For now, create a new visitor but use the passed context
        from .core import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        # Override the context to preserve loop depth
        visitor.context = context
        
        return function_executor.execute_function_call(
            cmd_name, args, context, visitor, redirects
        )


class AliasExecutionStrategy(ExecutionStrategy):
    """Strategy for executing shell aliases."""
    
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """Check if command is an alias."""
        # Check for bypass mechanisms first
        if cmd_name.startswith('\\'):
            return False  # Backslash escapes bypass aliases
        result = shell.alias_manager.has_alias(cmd_name)
        return result
    
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context: 'ExecutionContext',
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute an alias by expanding and re-executing."""
        alias_definition = shell.alias_manager.get_alias(cmd_name)
        if not alias_definition:
            return 127  # Should not happen if can_execute returned True
        
        # Prevent infinite recursion
        if cmd_name in shell.alias_manager.expanding:
            # Already expanding this alias, treat as external command
            return self._execute_as_external(cmd_name, args, shell, context, redirects, background)
        
        # Mark this alias as being expanded
        shell.alias_manager.expanding.add(cmd_name)
        
        try:
            # Create new command string by expanding the alias
            # If alias has trailing space, next word can also be expanded
            if alias_definition.endswith(' '):
                # Handle trailing space for chained alias expansion
                expanded_command = alias_definition + ' '.join(args)
            else:
                expanded_command = alias_definition + (' ' + ' '.join(args) if args else '')
            
            # Re-tokenize and parse the expanded command
            from ..lexer import tokenize
            from ..parser import Parser
            
            tokens = tokenize(expanded_command)
            parser = Parser(tokens, source_text=expanded_command)
            ast = parser.parse()
            
            # Execute the expanded command through the visitor
            # Import here to avoid circular imports
            from .core import ExecutorVisitor
            visitor = ExecutorVisitor(shell)
            # Preserve the current context
            visitor.context = context
            
            return visitor.visit(ast)
        
        finally:
            # Remove from expanding set
            shell.alias_manager.expanding.discard(cmd_name)
    
    def _execute_as_external(self, cmd_name: str, args: List[str], 
                            shell: 'Shell', context: 'ExecutionContext',
                            redirects: Optional[List['Redirect']] = None,
                            background: bool = False) -> int:
        """Execute as external command when alias recursion is detected."""
        external_strategy = ExternalExecutionStrategy()
        return external_strategy.execute(cmd_name, args, shell, context, redirects, background)


class ExternalExecutionStrategy(ExecutionStrategy):
    """Strategy for executing external commands."""
    
    def can_execute(self, cmd_name: str, shell: 'Shell') -> bool:
        """External commands are the fallback - always return True."""
        return True
    
    def execute(self, cmd_name: str, args: List[str], 
                shell: 'Shell', context: 'ExecutionContext',
                redirects: Optional[List['Redirect']] = None,
                background: bool = False) -> int:
        """Execute an external command."""
        full_args = [cmd_name] + args
        
        if context.in_pipeline:
            # In pipeline, use exec to replace current process
            try:
                # Set up redirections if any
                if redirects:
                    # Create a dummy command object for the io_manager
                    from ..ast_nodes import SimpleCommand
                    temp_command = SimpleCommand(args=full_args, redirects=redirects)
                    shell.io_manager.setup_child_redirections(temp_command)
                
                # Ensure we're in the correct process group before exec
                # This is important for commands that might fork after exec
                current_pgid = os.getpgrp()
                current_pid = os.getpid()
                
                if shell.state.options.get('debug-exec'):
                    print(f"DEBUG ExternalStrategy: Before exec - PID={current_pid}, PGID={current_pgid}", 
                          file=sys.stderr)
                
                # Always explicitly set the process group to ensure it's inherited
                # This helps when execvpe creates a new process
                os.setpgid(0, current_pgid)
                
                os.execvpe(full_args[0], full_args, shell.env)
            except OSError as e:
                print(f"psh: {full_args[0]}: {e}", file=sys.stderr)
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
                shell.state._in_forked_child = True
                
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
                    temp_command = SimpleCommand(args=full_args, redirects=redirects)
                    shell.io_manager.setup_child_redirections(temp_command)
                
                # Execute the command with proper environment
                if shell.state.options.get('debug-exec'):
                    print(f"DEBUG ExternalStrategy: execvpe {full_args[0]} with PATH={shell.env.get('PATH', 'NOT_SET')[:50]}...", 
                          file=sys.stderr)
                os.execvpe(full_args[0], full_args, shell.env)
            except FileNotFoundError:
                # Write to stderr file descriptor
                error_msg = f"psh: {full_args[0]}: command not found\n"
                os.write(2, error_msg.encode('utf-8'))
                os._exit(127)
            except OSError as e:
                # Write to stderr file descriptor
                error_msg = f"psh: {full_args[0]}: {e}\n"
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
            job = shell.job_manager.create_job(pid, " ".join(str(arg) for arg in full_args))
            job.add_process(pid, str(full_args[0]))
            
            if background:
                # Background job
                job.foreground = False
                # Note: context.background_job should be set by caller
                shell.state.last_bg_pid = pid
                # Print job assignment notification (only in interactive mode)
                if not shell.state.is_script_mode:
                    print(f"[{job.job_id}] {pid}")
                return 0
            else:
                # Foreground job - give it terminal control
                job.foreground = True
                shell.job_manager.set_foreground_job(job)
                
                if original_pgid is not None:
                    shell.state.foreground_pgid = pid
                    try:
                        os.tcsetpgrp(0, pid)
                    except:
                        pass
                
                # Use job manager to wait (it handles SIGCHLD)
                exit_status = shell.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    shell.state.foreground_pgid = None
                    shell.job_manager.set_foreground_job(None)
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
                # Clean up
                from ..job_control import JobState
                if job.state == JobState.DONE:
                    shell.job_manager.remove_job(job.job_id)
                
                return exit_status