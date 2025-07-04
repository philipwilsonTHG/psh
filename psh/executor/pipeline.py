"""
Pipeline execution support for the PSH executor.

This module provides the PipelineContext class and PipelineExecutor for
handling pipeline execution with proper process management and job control.
"""

import os
import sys
import signal
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..shell import Shell
    from ..job_control import JobManager, Job, JobState
    from ..ast_nodes import Pipeline, ASTNode, SimpleCommand
    from .context import ExecutionContext
    from ..visitor.base import ASTVisitor


class PipelineContext:
    """Context for managing pipeline execution state."""
    
    def __init__(self, job_manager: 'JobManager'):
        self.job_manager = job_manager
        self.pipes: List[Tuple[int, int]] = []
        self.processes: List[int] = []
        self.job: Optional['Job'] = None
    
    def add_pipe(self) -> int:
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


class PipelineExecutor:
    """
    Handles execution of pipelines.
    
    This class encapsulates all logic for executing Pipeline nodes,
    including process forking, pipe management, job control, and
    terminal control.
    """
    
    def __init__(self, shell: 'Shell'):
        """Initialize the pipeline executor with a shell instance."""
        self.shell = shell
        self.state = shell.state
        self.job_manager = shell.job_manager
    
    def execute(self, node: 'Pipeline', context: 'ExecutionContext', 
                visitor: 'ASTVisitor[int]') -> int:
        """
        Execute a pipeline and return exit status.
        
        Args:
            node: The Pipeline AST node to execute
            context: The current execution context
            visitor: The visitor to use for executing individual commands
            
        Returns:
            Exit status code
        """
        # Handle NOT operator
        if node.negated:
            exit_status = self._execute_pipeline(node, context, visitor)
            # Invert exit status for NOT
            return 0 if exit_status != 0 else 1
        else:
            return self._execute_pipeline(node, context, visitor)
    
    def _execute_pipeline(self, node: 'Pipeline', context: 'ExecutionContext',
                         visitor: 'ASTVisitor[int]') -> int:
        """Execute pipeline without NOT handling."""
        if len(node.commands) == 1:
            # Single command, no pipeline needed
            return visitor.visit(node.commands[0])
        
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
        
        # Create new context for pipeline execution
        pipeline_context = context.pipeline_context_enter()
        pipeline_context = pipeline_context.with_pipeline_context(pipeline_ctx)
        
        # Save original terminal process group for restoration
        try:
            original_pgid = os.tcgetpgrp(0)
            if self.state.options.get('debug-exec'):
                print(f"DEBUG Pipeline: Original terminal PGID: {original_pgid}", file=sys.stderr)
        except Exception as e:
            if self.state.options.get('debug-exec'):
                print(f"DEBUG Pipeline: Cannot get original PGID: {e}", file=sys.stderr)
            original_pgid = None
        
        try:
            # Fork processes for each command
            for i, command in enumerate(node.commands):
                is_last_command = (i == len(node.commands) - 1)
                pid = os.fork()
                
                if pid == 0:
                    # Child process
                    try:
                        # Create forked context
                        child_context = pipeline_context.fork_context()
                        
                        # Set flag to indicate we're in a forked child
                        self.state._in_forked_child = True
                        
                        # Set process group - this must be done before resetting signal handlers
                        # to avoid SIGTTOU when child tries to write to terminal
                        if i == 0:
                            # First child becomes process group leader
                            os.setpgid(0, 0)
                            # Also ensure we set signal disposition to ignore SIGTTOU temporarily
                            # until parent transfers terminal control
                            signal.signal(signal.SIGTTOU, signal.SIG_IGN)
                        else:
                            # Other children must join the process group of the first child
                            # We need to wait for the parent to set our process group
                            # Check if we're already in a process group (parent may have set it)
                            import time
                            for attempt in range(50):  # Try for up to 50ms
                                try:
                                    current_pgid = os.getpgrp()
                                    # If we're not in our own process group, we've been moved
                                    if current_pgid != os.getpid():
                                        if self.state.options.get('debug-exec'):
                                            print(f"DEBUG Pipeline: Child {os.getpid()} joined pgid {current_pgid} after {attempt} attempts", file=sys.stderr)
                                        break
                                except OSError:
                                    pass
                                time.sleep(0.001)  # Wait 1ms
                            else:
                                # If we get here, we timed out
                                if self.state.options.get('debug-exec'):
                                    final_pgid = os.getpgrp()
                                    print(f"DEBUG Pipeline: Child {os.getpid()} timed out, pgid is {final_pgid}", file=sys.stderr)
                            # Ignore SIGTTOU until parent sets up terminal control
                            signal.signal(signal.SIGTTOU, signal.SIG_IGN)
                        
                        # Reset most signal handlers to default (but keep SIGTTOU ignored)
                        signal.signal(signal.SIGINT, signal.SIG_DFL)
                        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                        # Keep SIGTTOU ignored - it was set above
                        signal.signal(signal.SIGTTIN, signal.SIG_DFL)
                        
                        # Set up pipeline redirections
                        self._setup_pipeline_redirections(i, pipeline_ctx)
                        
                        # For the last command in foreground pipeline, ensure terminal access
                        if is_last_command and not is_background:
                            # Restore terminal signal handling for interactive commands
                            signal.signal(signal.SIGTTOU, signal.SIG_DFL)
                            signal.signal(signal.SIGTTIN, signal.SIG_DFL)
                        
                        # Execute command with pipeline context
                        # Note: visitor is a special parameter because we need the
                        # ExecutorVisitor instance to execute commands
                        # IMPORTANT: Update visitor's context to use the child_context
                        original_context = visitor.context
                        visitor.context = child_context
                        exit_status = visitor.visit(command)
                        os._exit(exit_status)
                    except SystemExit as e:
                        # Handle explicit exit
                        os._exit(e.code if e.code is not None else 0)
                    except Exception as e:
                        print(f"psh: {e}", file=sys.stderr)
                        os._exit(1)
                else:
                    # Parent process
                    if i == 0:
                        # First child becomes the process group leader
                        pgid = pid
                        # Try to set the first child's process group from parent side too
                        try:
                            os.setpgid(pid, pid)
                        except OSError:
                            pass  # Child may have already set it
                    else:
                        # Set process group for subsequent children to join the pipeline
                        try:
                            os.setpgid(pid, pgid)
                            if self.state.options.get('debug-exec'):
                                print(f"DEBUG Pipeline: Parent set child {pid} to pgid {pgid}", file=sys.stderr)
                        except OSError as e:
                            if self.state.options.get('debug-exec'):
                                print(f"DEBUG Pipeline: Parent failed to set pgid for {pid}: {e}", file=sys.stderr)
                            pass  # Race condition - child may have set it already
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
            
            # Transfer terminal control immediately for foreground pipelines
            # This prevents SIGTTOU in children before wait method is called
            if not is_background and original_pgid is not None:
                try:
                    if self.state.options.get('debug-exec'):
                        print(f"DEBUG Pipeline: Transferring terminal control from {original_pgid} to {pgid}", file=sys.stderr)
                    os.tcsetpgrp(0, pgid)
                    if self.state.options.get('debug-exec'):
                        print(f"DEBUG Pipeline: Terminal control transferred successfully", file=sys.stderr)
                except Exception as e:
                    if self.state.options.get('debug-exec'):
                        print(f"DEBUG Pipeline: Failed to transfer terminal control: {e}", file=sys.stderr)
                    pass  # Ignore errors - may not have terminal control
            
            # Wait for pipeline completion
            if is_background:
                # Background pipeline
                print(f"[{job.job_id}] {job.pgid}")
                return 0
            else:
                # Foreground pipeline - wait for completion
                return self._wait_for_foreground_pipeline(job, node, original_pgid)
                
        except Exception as e:
            # Clean up pipes on error
            pipeline_ctx.close_pipes()
            # Restore terminal control on error
            if not is_background and original_pgid is not None:
                try:
                    os.tcsetpgrp(0, original_pgid)
                except:
                    pass
            raise
    
    def _wait_for_foreground_pipeline(self, job: 'Job', node: 'Pipeline', original_pgid: Optional[int] = None) -> int:
        """Wait for a foreground pipeline to complete."""
        job.foreground = True
        self.job_manager.set_foreground_job(job)
        
        # Ensure we have the original pgid for restoration
        if original_pgid is None:
            try:
                original_pgid = os.tcgetpgrp(0)
            except:
                original_pgid = None
        
        # Terminal control should already be transferred by caller
        # No need to transfer again here
        
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
            self.state.foreground_pgid = None
            try:
                os.tcsetpgrp(0, original_pgid)
            except:
                pass
        
        self.job_manager.set_foreground_job(None)
        
        # Remove completed job
        from ..job_control import JobState
        if job.state == JobState.DONE:
            self.job_manager.remove_job(job.job_id)
        
        return exit_status
    
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
    
    def _pipeline_to_string(self, node: 'Pipeline') -> str:
        """Convert pipeline to string representation."""
        return " | ".join(self._command_to_string(cmd) for cmd in node.commands)
    
    def _command_to_string(self, cmd: 'ASTNode') -> str:
        """Convert command to string representation."""
        from ..ast_nodes import SimpleCommand
        if isinstance(cmd, SimpleCommand):
            # Convert args to strings (in case they're RichToken objects)
            str_args = [str(arg) for arg in cmd.args]
            return " ".join(str_args)
        else:
            return f"<{type(cmd).__name__}>"