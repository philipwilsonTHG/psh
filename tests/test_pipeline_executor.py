"""
Tests for the PipelineExecutor module.
"""

import pytest
from psh.shell import Shell
from psh.executor import PipelineExecutor, ExecutionContext
from psh.ast_nodes import Pipeline, SimpleCommand


class TestPipelineExecutor:
    """Test the PipelineExecutor functionality."""
    
    @pytest.fixture
    def shell(self):
        """Create a shell instance for testing."""
        return Shell(norc=True)
    
    @pytest.fixture
    def executor(self, shell):
        """Create a pipeline executor."""
        return PipelineExecutor(shell)
    
    @pytest.fixture
    def context(self):
        """Create an execution context."""
        return ExecutionContext()
    
    def test_single_command_pipeline(self, executor, context, shell):
        """Test pipeline with single command (no actual pipe needed)."""
        # Create a single command pipeline
        cmd = SimpleCommand(args=['echo', 'hello'])
        pipeline = Pipeline(commands=[cmd])
        
        # Import ExecutorVisitor for visitor parameter
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute the pipeline
        exit_status = executor.execute(pipeline, context, visitor)
        
        assert exit_status == 0
    
    def test_two_command_pipeline(self, executor, context, shell):
        """Test pipeline with two commands."""
        # Create a two-stage pipeline: echo hello | grep hello
        cmd1 = SimpleCommand(args=['echo', 'hello'])
        cmd2 = SimpleCommand(args=['grep', 'hello'])
        pipeline = Pipeline(commands=[cmd1, cmd2])
        
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute the pipeline
        exit_status = executor.execute(pipeline, context, visitor)
        
        assert exit_status == 0
    
    def test_pipeline_negation(self, executor, context, shell):
        """Test pipeline with NOT operator."""
        # Create a pipeline that fails: false
        cmd = SimpleCommand(args=['false'])
        pipeline = Pipeline(commands=[cmd], negated=True)
        
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute the negated pipeline
        exit_status = executor.execute(pipeline, context, visitor)
        
        # Should return 0 because false returns 1 and it's negated
        assert exit_status == 0
    
    def test_three_stage_pipeline(self, executor, context, shell):
        """Test pipeline with three commands."""
        # Create a three-stage pipeline: echo "line1\nline2" | grep line | wc -l
        cmd1 = SimpleCommand(args=['echo', 'line1\nline2'])
        cmd2 = SimpleCommand(args=['grep', 'line'])
        cmd3 = SimpleCommand(args=['wc', '-l'])
        pipeline = Pipeline(commands=[cmd1, cmd2, cmd3])
        
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute the pipeline
        exit_status = executor.execute(pipeline, context, visitor)
        
        assert exit_status == 0
    
    def test_pipeline_failure(self, executor, context, shell):
        """Test pipeline with command that fails."""
        # Create a pipeline with failing command
        cmd1 = SimpleCommand(args=['echo', 'test'])
        cmd2 = SimpleCommand(args=['grep', 'notfound'])
        pipeline = Pipeline(commands=[cmd1, cmd2])
        
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute the pipeline
        exit_status = executor.execute(pipeline, context, visitor)
        
        # grep returns 1 when no match found
        assert exit_status == 1
    
    def test_pipefail_option(self, executor, context, shell):
        """Test pipefail option behavior."""
        # Enable pipefail
        shell.state.options['pipefail'] = True
        
        # Create pipeline where first command fails: false | echo "test"
        cmd1 = SimpleCommand(args=['false'])
        cmd2 = SimpleCommand(args=['echo', 'test'])
        pipeline = Pipeline(commands=[cmd1, cmd2])
        
        from psh.executor import ExecutorVisitor
        visitor = ExecutorVisitor(shell)
        
        # Execute with pipefail
        exit_status = executor.execute(pipeline, context, visitor)
        
        # With pipefail, should return 1 (from false)
        assert exit_status == 1