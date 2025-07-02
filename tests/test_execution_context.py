"""
Tests for the ExecutionContext class.
"""

import pytest
from psh.executor.context import ExecutionContext


class TestExecutionContext:
    """Test the ExecutionContext functionality."""
    
    def test_default_context(self):
        """Test default context values."""
        ctx = ExecutionContext()
        assert ctx.in_pipeline is False
        assert ctx.in_subshell is False
        assert ctx.in_forked_child is False
        assert ctx.loop_depth == 0
        assert ctx.current_function is None
        assert ctx.pipeline_context is None
        assert ctx.background_job is None
        assert ctx.suppress_function_lookup is False
        assert ctx.exec_mode is False
    
    def test_fork_context(self):
        """Test forking a context for child process."""
        ctx = ExecutionContext(
            in_pipeline=True,
            loop_depth=2,
            current_function="test_func"
        )
        
        forked = ctx.fork_context()
        assert forked.in_pipeline is True  # Inherited
        assert forked.in_subshell is True
        assert forked.in_forked_child is True
        assert forked.loop_depth == 2  # Inherited
        assert forked.current_function == "test_func"  # Inherited
        assert forked.pipeline_context is None  # Not inherited
        assert forked.background_job is None  # Not inherited
    
    def test_subshell_context(self):
        """Test creating a subshell context."""
        ctx = ExecutionContext(
            in_pipeline=True,
            loop_depth=1,
            current_function="func"
        )
        
        subshell = ctx.subshell_context()
        assert subshell.in_pipeline is False  # Reset
        assert subshell.in_subshell is True
        assert subshell.loop_depth == 1  # Inherited
        assert subshell.current_function == "func"  # Inherited
    
    def test_pipeline_context_enter(self):
        """Test entering a pipeline."""
        ctx = ExecutionContext()
        pipeline_ctx = ctx.pipeline_context_enter()
        
        assert pipeline_ctx.in_pipeline is True
        assert pipeline_ctx.in_subshell is False
        assert pipeline_ctx.loop_depth == 0
    
    def test_loop_context_enter(self):
        """Test entering a loop."""
        ctx = ExecutionContext(loop_depth=1)
        loop_ctx = ctx.loop_context_enter()
        
        assert loop_ctx.loop_depth == 2
        assert loop_ctx.in_loop() is True
    
    def test_function_context_enter(self):
        """Test entering a function."""
        ctx = ExecutionContext()
        func_ctx = ctx.function_context_enter("my_func")
        
        assert func_ctx.current_function == "my_func"
        assert func_ctx.in_function() is True
    
    def test_in_loop_helper(self):
        """Test in_loop helper method."""
        ctx = ExecutionContext()
        assert ctx.in_loop() is False
        
        ctx.loop_depth = 1
        assert ctx.in_loop() is True
    
    def test_in_function_helper(self):
        """Test in_function helper method."""
        ctx = ExecutionContext()
        assert ctx.in_function() is False
        
        ctx.current_function = "test"
        assert ctx.in_function() is True
    
    def test_should_use_print(self):
        """Test should_use_print helper method."""
        ctx = ExecutionContext()
        assert ctx.should_use_print() is True  # Not in forked child
        
        ctx.in_forked_child = True
        assert ctx.should_use_print() is False  # In forked child
    
    def test_immutability_of_context_methods(self):
        """Test that context methods return new instances."""
        ctx = ExecutionContext()
        
        # Each method should return a new instance
        fork = ctx.fork_context()
        assert fork is not ctx
        
        loop = ctx.loop_context_enter()
        assert loop is not ctx
        assert ctx.loop_depth == 0  # Original unchanged
        
        func = ctx.function_context_enter("test")
        assert func is not ctx
        assert ctx.current_function is None  # Original unchanged