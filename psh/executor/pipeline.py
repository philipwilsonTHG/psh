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
        return self._execute_pipeline(pipeline)
    
    def _execute_pipeline(self, pipeline: Pipeline) -> int:
        """Execute a multi-command pipeline."""
        # For now, delegate back to shell's execute_pipeline
        # This will be properly implemented when we have process management
        return self.shell.execute_pipeline(pipeline)