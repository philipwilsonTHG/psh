"""Pipeline execution."""
import os
import sys
import signal
from typing import List
from ..ast_nodes import (
    Pipeline, SimpleCommand, CompoundCommand,
    # Unified types only
    WhileLoop, ForLoop, CStyleForLoop, IfConditional,
    CaseConditional, SelectLoop, ArithmeticEvaluation,
    BreakStatement, ContinueStatement,
    ExecutionContext
)
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn
from ..job_control import JobState

class PipelineExecutor(ExecutorComponent):
    """Executes command pipelines."""
    
    def execute(self, pipeline: Pipeline) -> int:
        """Execute a pipeline and return exit status of last command."""
        if len(pipeline.commands) == 1:
            # Single command, no pipes
            command = pipeline.commands[0]
            
            # Handle break/continue specially
            if isinstance(command, (BreakStatement, ContinueStatement)):
                from ..core.exceptions import LoopBreak, LoopContinue
                if isinstance(command, BreakStatement):
                    raise LoopBreak(command.level)
                else:
                    raise LoopContinue(command.level)
            
            # Regular command execution
            try:
                if isinstance(command, SimpleCommand):
                    exit_status = self.shell.execute_command(command)
                elif isinstance(command, CompoundCommand):
                    # Execute compound command directly
                    exit_status = self._execute_compound_in_subshell(command)
                else:
                    exit_status = 1
                    
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
        
        # Sync exported variables to environment before forking
        self.state.scope_manager.sync_exports_to_environment(self.state.env)
        
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
            command = pipeline.commands[i]
            if isinstance(command, SimpleCommand):
                cmd_str = ' '.join(command.args) if command.args else ''
            else:
                cmd_str = f"({command.__class__.__name__})"
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
            if isinstance(command, SimpleCommand):
                cmd_str = ' '.join(command.args) if command.args else ''
            elif isinstance(command, CompoundCommand):
                # Use a generic representation for compound commands
                cmd_str = f"({command.__class__.__name__})"
            else:
                cmd_str = "(unknown)"
            
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
        if isinstance(command, SimpleCommand):
            # Delegate to command executor for simple commands
            return self.shell.executor_manager.command_executor.execute_in_child(command)
        elif isinstance(command, CompoundCommand):
            # Execute compound command in subshell
            return self._execute_compound_in_subshell(command)
        else:
            # Unknown command type
            return 1
    
    def _execute_compound_in_subshell(self, command: CompoundCommand) -> int:
        """Execute compound command in a subshell for pipeline compatibility."""
        try:
            # Set up as pipeline component (stdin/stdout already set up by _setup_child_process)
            
            # Apply redirections if any
            if command.redirects:
                saved_fds = self.shell.io_manager.apply_redirections(command.redirects)
            else:
                saved_fds = None
            
            try:
                # Route to appropriate executor based on command type
                # Handle unified types only
                if isinstance(command, WhileLoop):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_while_command(command)
                    else:
                        raise ValueError(f"WhileLoop with STATEMENT context in pipeline")
                elif isinstance(command, ForLoop):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_for_command(command)
                    else:
                        raise ValueError(f"ForLoop with STATEMENT context in pipeline")
                elif isinstance(command, CStyleForLoop):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_cstyle_for_command(command)
                    else:
                        raise ValueError(f"CStyleForLoop with STATEMENT context in pipeline")
                elif isinstance(command, IfConditional):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_if_command(command)
                    else:
                        raise ValueError(f"IfConditional with STATEMENT context in pipeline")
                elif isinstance(command, CaseConditional):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_case_command(command)
                    else:
                        raise ValueError(f"CaseConditional with STATEMENT context in pipeline")
                elif isinstance(command, SelectLoop):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_select_command(command)
                    else:
                        raise ValueError(f"SelectLoop with STATEMENT context in pipeline")
                elif isinstance(command, ArithmeticEvaluation):
                    if command.execution_context == ExecutionContext.PIPELINE:
                        return self._execute_arithmetic_command(command)
                    else:
                        raise ValueError(f"ArithmeticEvaluation with STATEMENT context in pipeline")
                elif isinstance(command, BreakStatement):
                    # Break in pipeline context
                    from ..core.exceptions import LoopBreak
                    raise LoopBreak(command.level)
                elif isinstance(command, ContinueStatement):
                    # Continue in pipeline context
                    from ..core.exceptions import LoopContinue
                    raise LoopContinue(command.level)
                else:
                    return 1
            finally:
                # Restore redirections
                if saved_fds:
                    self.shell.io_manager.restore_redirections(saved_fds)
                    
        except Exception:
            return 1
    
    def _execute_while_command(self, command) -> int:
        """Execute while loop in pipeline context."""
        from ..core.exceptions import LoopBreak, LoopContinue
        last_status = 0
        
        while True:
            try:
                # Check condition
                condition_status = self.shell.execute_command_list(command.condition)
                if condition_status != 0:
                    break
                
                # Execute body
                last_status = self.shell.execute_command_list(command.body)
                
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                continue
                
        return last_status
    
    def _execute_for_command(self, command) -> int:
        """Execute for loop in pipeline context."""
        from ..core.exceptions import LoopBreak, LoopContinue
        last_status = 0
        
        # Expand the items using the control flow executor
        expanded_items = []
        for item in command.items:
            # Use the control flow executor's expansion method
            expanded = self.shell.executor_manager.control_flow_executor._expand_for_item(item)
            expanded_items.extend(expanded)
        
        # Now iterate over expanded items
        for item in expanded_items:
            try:
                # Set loop variable
                self.state.set_variable(command.variable, item)
                
                # Execute body
                last_status = self.shell.execute_command_list(command.body)
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                continue
                
        return last_status
    
    def _execute_cstyle_for_command(self, command) -> int:
        """Execute C-style for loop in pipeline context."""
        # Execute directly using control flow executor
        return self.shell.executor_manager.control_flow_executor.execute_c_style_for(command)
    
    def _execute_if_command(self, command) -> int:
        """Execute if statement in pipeline context."""
        # Check main condition
        condition_status = self.shell.execute_command_list(command.condition)
        if condition_status == 0:
            return self.shell.execute_command_list(command.then_part)
        
        # Check elif conditions
        for elif_condition, elif_then in command.elif_parts:
            elif_status = self.shell.execute_command_list(elif_condition)
            if elif_status == 0:
                return self.shell.execute_command_list(elif_then)
        
        # Execute else part if present
        if command.else_part:
            return self.shell.execute_command_list(command.else_part)
        
        return 0
    
    def _execute_case_command(self, command) -> int:
        """Execute case statement in pipeline context."""
        # Execute directly using control flow executor
        return self.shell.executor_manager.control_flow_executor.execute_case(command)
    
    def _execute_select_command(self, command) -> int:
        """Execute select statement in pipeline context."""
        # Execute directly using control flow executor
        return self.shell.executor_manager.control_flow_executor.execute_select(command)
    
    def _execute_arithmetic_command(self, command) -> int:
        """Execute arithmetic command in pipeline context."""
        from ..executor.arithmetic_command import ArithmeticCommandExecutor
        executor = ArithmeticCommandExecutor(self.shell)
        return executor.execute(command)