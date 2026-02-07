"""
Execution context management for the PSH executor.

This module provides the ExecutionContext class that encapsulates all
execution state, replacing scattered instance variables with a structured
approach.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..job_control import Job
    from .pipeline import PipelineContext


@dataclass
class ExecutionContext:
    """
    Encapsulates execution state for cleaner parameter passing.
    
    This context object replaces the scattered state variables that were
    previously stored as instance variables in ExecutorVisitor, providing
    a cleaner and more maintainable approach to state management.
    """

    # Execution environment flags
    in_pipeline: bool = False
    in_subshell: bool = False
    in_forked_child: bool = False

    # Control flow state
    loop_depth: int = 0
    current_function: Optional[str] = None

    # Job and pipeline management
    pipeline_context: Optional['PipelineContext'] = None
    background_job: Optional['Job'] = None

    # Additional state for specific operations
    suppress_function_lookup: bool = False
    exec_mode: bool = False

    def fork_context(self) -> 'ExecutionContext':
        """
        Create a context for a forked child process.
        
        This creates a new context that inherits certain state but marks
        itself as being in a forked child, which affects how certain
        operations (like builtin output) are handled.
        """
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=True,
            in_forked_child=True,
            loop_depth=self.loop_depth,
            current_function=self.current_function,
            pipeline_context=None,  # Don't inherit pipeline context
            background_job=None,    # Don't inherit background job
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def subshell_context(self) -> 'ExecutionContext':
        """
        Create a context for subshell execution.
        
        Subshells inherit most state but are marked as being in a subshell,
        which affects variable scoping and other behaviors.
        """
        return ExecutionContext(
            in_pipeline=False,      # Subshells start fresh pipeline state
            in_subshell=True,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth,
            current_function=self.current_function,
            pipeline_context=None,
            background_job=None,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def pipeline_context_enter(self) -> 'ExecutionContext':
        """
        Create a context for entering a pipeline.
        
        Returns a new context with in_pipeline set to True.
        """
        return ExecutionContext(
            in_pipeline=True,
            in_subshell=self.in_subshell,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth,
            current_function=self.current_function,
            pipeline_context=self.pipeline_context,
            background_job=self.background_job,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def loop_context_enter(self) -> 'ExecutionContext':
        """
        Create a context for entering a loop.
        
        Returns a new context with incremented loop depth.
        """
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=self.in_subshell,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth + 1,
            current_function=self.current_function,
            pipeline_context=self.pipeline_context,
            background_job=self.background_job,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def function_context_enter(self, function_name: str) -> 'ExecutionContext':
        """
        Create a context for entering a function.
        
        Returns a new context with the current function set.
        """
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=self.in_subshell,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth,
            current_function=function_name,
            pipeline_context=self.pipeline_context,
            background_job=self.background_job,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def with_pipeline_context(self, pipeline_ctx: 'PipelineContext') -> 'ExecutionContext':
        """
        Create a context with a specific pipeline context.
        
        Used when setting up pipeline execution.
        """
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=self.in_subshell,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth,
            current_function=self.current_function,
            pipeline_context=pipeline_ctx,
            background_job=self.background_job,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def with_background_job(self, job: 'Job') -> 'ExecutionContext':
        """
        Create a context with a background job reference.
        
        Used when executing background commands.
        """
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=self.in_subshell,
            in_forked_child=self.in_forked_child,
            loop_depth=self.loop_depth,
            current_function=self.current_function,
            pipeline_context=self.pipeline_context,
            background_job=job,
            suppress_function_lookup=self.suppress_function_lookup,
            exec_mode=self.exec_mode
        )

    def in_loop(self) -> bool:
        """Check if we're currently inside a loop."""
        return self.loop_depth > 0

    def in_function(self) -> bool:
        """Check if we're currently inside a function."""
        return self.current_function is not None

    def should_use_print(self) -> bool:
        """
        Determine if builtins should use print() or write to file descriptors.
        
        In forked children (pipelines, subshells), builtins should write
        directly to file descriptors to ensure output goes through pipes
        correctly.
        """
        return not self.in_forked_child
