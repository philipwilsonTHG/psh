"""Pipeline execution."""
import os
import sys
import signal
from typing import List
from ..ast_nodes import Pipeline
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn
from ..job_control import JobState

class PipelineExecutor(ExecutorComponent):
    """Executes command pipelines."""
    
    def execute(self, pipeline: Pipeline) -> int:
        """Execute a pipeline and return exit status of last command."""
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            try:
                exit_status = self.shell.execute_command(pipeline.commands[0])
                # Apply negation if needed
                if pipeline.negated:
                    exit_status = 0 if exit_status != 0 else 1
                return exit_status
            except FunctionReturn:
                # Propagate up
                raise
        
        # Multiple commands in pipeline
        return self._execute_pipeline(pipeline)
    
    def _execute_pipeline(self, pipeline: Pipeline) -> int:
        """Execute a multi-command pipeline."""
        # Build command string for job tracking
        command_string = self._build_pipeline_string(pipeline)
        
        # Execute pipeline using fork and pipe
        num_commands = len(pipeline.commands)
        pipes = []
        pids = []
        pgid = None
        job = None
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        # Create pipes for inter-process communication
        for i in range(num_commands - 1):
            pipe_read, pipe_write = os.pipe()
            pipes.append((pipe_read, pipe_write))
        
        # Fork and execute each command
        for i, command in enumerate(pipeline.commands):
            pid = os.fork()
            
            if pid == 0:  # Child process
                # Set flag to indicate we're in a forked child
                self.state._in_forked_child = True
                pgid = self._setup_child_process(pgid, i, num_commands, pipes)
                exit_code = self._execute_in_child(command)
                os._exit(exit_code)
            
            else:  # Parent process
                if pgid is None:
                    pgid = pid
                    os.setpgid(pid, pgid)
                else:
                    try:
                        os.setpgid(pid, pgid)
                    except:
                        pass  # Race condition - child may have already done it
                pids.append(pid)
        
        # Create job entry for tracking
        job = self.job_manager.create_job(pgid, command_string)
        for i, pid in enumerate(pids):
            cmd_str = ' '.join(pipeline.commands[i].args) if pipeline.commands[i].args else ''
            job.add_process(pid, cmd_str)
        
        # Give terminal control to the pipeline
        is_background = pipeline.commands[-1].background
        
        if not is_background:
            # Foreground job
            self.state.foreground_pgid = pgid
            job.foreground = True
            self.job_manager.set_foreground_job(job)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, pgid)
                except:
                    pass
        else:
            # Background job
            job.foreground = False
            print(f"[{job.job_id}] {job.pgid}")
        
        # Parent: Close all pipes
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        # Wait for all children and get exit status
        if not is_background:
            # Foreground job - wait for it
            # Check if we need to collect all exit statuses for pipefail
            if self.state.options.get('pipefail', False) and len(pipeline.commands) > 1:
                # Collect all exit statuses
                exit_statuses = self.job_manager.wait_for_job(job, collect_all_statuses=True)
                
                # Use OptionHandler to determine final exit code
                from ..core.options import OptionHandler
                last_status = OptionHandler.get_pipeline_exit_code(self.state, exit_statuses)
            else:
                # Normal behavior - just get last command's exit status
                last_status = self.job_manager.wait_for_job(job)
            
            # Restore terminal control
            self.state.foreground_pgid = None
            self.job_manager.set_foreground_job(None)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, original_pgid)
                except:
                    pass
            
            # Remove completed job
            if job.state == JobState.DONE:
                self.job_manager.remove_job(job.job_id)
        else:
            # Background job - don't wait
            last_status = 0
            self.state.last_bg_pid = pids[-1] if pids else None
        
        # Apply negation if needed
        if pipeline.negated:
            last_status = 0 if last_status != 0 else 1
        
        return last_status
    
    def _build_pipeline_string(self, pipeline: Pipeline) -> str:
        """Build a string representation of the pipeline for job display."""
        parts = []
        for command in pipeline.commands:
            cmd_str = ' '.join(command.args) if command.args else ''
            if command.background:
                cmd_str += ' &'
            parts.append(cmd_str)
        return ' | '.join(parts)
    
    def _setup_child_process(self, pgid, command_index, num_commands, pipes):
        """Set up a child process in a pipeline"""
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
        
        # Set up pipes
        if command_index > 0:  # Not first command - read from previous pipe
            os.dup2(pipes[command_index-1][0], 0)  # stdin = pipe_read
            
        if command_index < num_commands - 1:  # Not last command - write to next pipe
            os.dup2(pipes[command_index][1], 1)  # stdout = pipe_write
        
        # Close all pipe file descriptors
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        return pgid
    
    def _execute_in_child(self, command):
        """Execute a command in a child process (after fork)"""
        # Delegate to command executor
        return self.shell.executor_manager.command_executor.execute_in_child(command)