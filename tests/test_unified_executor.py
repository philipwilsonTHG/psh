"""Test executors with unified control structure types."""

import pytest
from psh.shell import Shell
from psh.ast_nodes import (
    WhileLoop, ForLoop, ExecutionContext, CommandList, StatementList,
    AndOrList, Pipeline, SimpleCommand
)


class TestUnifiedExecutor:
    """Test unified control structure execution."""
    
    def test_while_loop_statement_execution(self, shell):
        """Test executing WhileLoop with STATEMENT context."""
        
        # Create a while loop that prints numbers
        # while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done
        
        # Set up initial variable
        shell.state.set_variable('i', '0')
        
        # Create condition: [ $i -lt 3 ]
        condition = StatementList()
        test_pipeline = Pipeline()
        test_cmd = SimpleCommand(
            args=['[', '$i', '-lt', '3', ']'],
            arg_types=['WORD', 'VARIABLE', 'WORD', 'WORD', 'WORD']
        )
        test_pipeline.commands.append(test_cmd)
        and_or = AndOrList()
        and_or.pipelines.append(test_pipeline)
        condition.statements.append(and_or)
        
        # Create body: echo $i; i=$((i+1))
        body = StatementList()
        
        # echo $i
        echo_pipeline = Pipeline()
        echo_cmd = SimpleCommand(
            args=['echo', '$i'],
            arg_types=['WORD', 'VARIABLE']
        )
        echo_pipeline.commands.append(echo_cmd)
        echo_and_or = AndOrList()
        echo_and_or.pipelines.append(echo_pipeline)
        body.statements.append(echo_and_or)
        
        # i=$((i+1))
        assign_pipeline = Pipeline()
        assign_cmd = SimpleCommand(
            args=['i=$((i+1))'],
            arg_types=['VARIABLE_ASSIGNMENT']
        )
        assign_pipeline.commands.append(assign_cmd)
        assign_and_or = AndOrList()
        assign_and_or.pipelines.append(assign_pipeline)
        body.statements.append(assign_and_or)
        
        # Create unified while loop
        while_loop = WhileLoop(
            condition=condition,
            body=body,
            execution_context=ExecutionContext.STATEMENT
        )
        
        # Execute
        status = shell.executor_manager.control_flow_executor.execute(while_loop)
        assert status == 0
        assert shell.state.get_variable('i') == '3'
    
    def test_for_loop_statement_execution(self, shell):
        """Test executing ForLoop with STATEMENT context."""
        
        # for i in a b c; do echo $i; done
        
        # Create body: echo $i
        body = StatementList()
        echo_pipeline = Pipeline()
        echo_cmd = SimpleCommand(
            args=['echo', '$i'],
            arg_types=['WORD', 'VARIABLE']
        )
        echo_pipeline.commands.append(echo_cmd)
        echo_and_or = AndOrList()
        echo_and_or.pipelines.append(echo_pipeline)
        body.statements.append(echo_and_or)
        
        # Create unified for loop
        for_loop = ForLoop(
            variable='i',
            items=['a', 'b', 'c'],
            body=body,
            execution_context=ExecutionContext.STATEMENT
        )
        
        # Execute
        status = shell.executor_manager.control_flow_executor.execute(for_loop)
        assert status == 0
    
    def test_unified_type_pipeline_context_error(self, shell):
        """Test that PIPELINE context unified types raise error in ControlFlowExecutor."""
        
        # Create a WhileLoop with PIPELINE context
        condition = StatementList()
        body = StatementList()
        
        while_loop = WhileLoop(
            condition=condition,
            body=body,
            execution_context=ExecutionContext.PIPELINE
        )
        
        # Should raise error when trying to execute in ControlFlowExecutor
        with pytest.raises(ValueError, match="WhileLoop with PIPELINE context"):
            shell.executor_manager.control_flow_executor.execute(while_loop)
    
    def test_unified_type_statement_context_error(self, shell):
        """Test that STATEMENT context unified types raise error in PipelineExecutor."""
        
        # Create a WhileLoop with STATEMENT context
        condition = StatementList()
        body = StatementList()
        
        while_loop = WhileLoop(
            condition=condition,
            body=body,
            execution_context=ExecutionContext.STATEMENT
        )
        
        # The error should be raised when trying to execute in wrong context
        # But _execute_compound_in_subshell catches all exceptions and returns 1
        # So let's check the actual behavior
        result = shell.executor_manager.pipeline_executor._execute_compound_in_subshell(while_loop)
        # It should return 1 due to the ValueError
        assert result == 1