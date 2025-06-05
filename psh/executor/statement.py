"""Statement list execution."""
import sys
from ..ast_nodes import (CommandList, AndOrList, Pipeline, ASTNode, TopLevel,
                         FunctionDef, IfStatement, WhileStatement, ForStatement,
                         CStyleForStatement, BreakStatement, ContinueStatement, 
                         CaseStatement, SelectStatement, EnhancedTestStatement, ArithmeticCommand)
from .base import ExecutorComponent
from ..builtins.function_support import FunctionReturn
from ..core.exceptions import LoopBreak, LoopContinue

class StatementExecutor(ExecutorComponent):
    """Executes statement lists and logical operators."""
    
    def execute(self, node: ASTNode) -> int:
        """Execute a statement node."""
        if isinstance(node, CommandList):
            return self.execute_command_list(node)
        elif isinstance(node, AndOrList):
            return self.execute_and_or_list(node)
        elif isinstance(node, TopLevel):
            return self.execute_toplevel(node)
        else:
            raise ValueError(f"Unknown statement node: {type(node)}")
    
    def execute_command_list(self, command_list: CommandList) -> int:
        """Execute a command list with full statement support."""
        exit_code = 0
        try:
            for item in command_list.statements:
                if isinstance(item, BreakStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, ContinueStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, IfStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_if(item)
                elif isinstance(item, WhileStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_while(item)
                elif isinstance(item, ForStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_for(item)
                elif isinstance(item, CStyleForStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_c_style_for(item)
                elif isinstance(item, CaseStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_case(item)
                elif isinstance(item, SelectStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_select(item)
                elif isinstance(item, EnhancedTestStatement):
                    exit_code = self.shell.executor_manager.control_flow_executor.execute_enhanced_test(item)
                elif isinstance(item, ArithmeticCommand):
                    exit_code = self.shell.executor_manager.arithmetic_executor.execute(item)
                elif isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        exit_code = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        exit_code = 1
                elif isinstance(item, AndOrList):
                    # Handle regular and_or_list
                    exit_code = self.execute_and_or_list(item)
                else:
                    print(f"psh: unknown statement type: {type(item).__name__}", file=sys.stderr)
                    exit_code = 1
                self.state.last_exit_code = exit_code
        except FunctionReturn:
            # Only catch FunctionReturn if we're in a function
            if self.state.function_stack:
                raise
            # Otherwise it's an error
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        except (LoopBreak, LoopContinue) as e:
            # Re-raise to be handled by enclosing loop
            raise
        return exit_code
    
    def execute_toplevel(self, toplevel: TopLevel) -> int:
        """Execute a top-level script/input containing functions and commands."""
        last_exit = 0
        
        try:
            for item in toplevel.items:
                if isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        last_exit = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        last_exit = 1
                elif isinstance(item, CommandList):
                    # Collect here documents if any
                    self.io_manager.collect_heredocs(item)
                    # Execute commands
                    last_exit = self.execute_command_list(item)
                    # last_exit_code already updated by execute_command_list
                elif isinstance(item, IfStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute if statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_if(item)
                elif isinstance(item, WhileStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute while statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_while(item)
                elif isinstance(item, ForStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute for statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_for(item)
                elif isinstance(item, CStyleForStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute C-style for statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_c_style_for(item)
                elif isinstance(item, CaseStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute case statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_case(item)
                elif isinstance(item, SelectStatement):
                    # Collect here documents
                    self.io_manager.collect_heredocs(item)
                    # Execute select statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_select(item)
                elif isinstance(item, BreakStatement):
                    # Execute break statement (this will raise LoopBreak)
                    last_exit = self.shell.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, ContinueStatement):
                    # Execute continue statement (this will raise LoopContinue)  
                    last_exit = self.shell.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, EnhancedTestStatement):
                    # Execute enhanced test statement
                    last_exit = self.shell.executor_manager.control_flow_executor.execute_enhanced_test(item)
                elif isinstance(item, ArithmeticCommand):
                    # Execute arithmetic command
                    last_exit = self.shell.executor_manager.arithmetic_executor.execute(item)
                    # Update last_exit_code immediately for use by subsequent commands
                    self.state.last_exit_code = last_exit
        except (LoopBreak, LoopContinue) as e:
            # Break/continue outside of loops is an error
            stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
            print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
            last_exit = 1
        
        self.state.last_exit_code = last_exit
        return last_exit
    
    def execute_and_or_list(self, and_or: AndOrList) -> int:
        """Execute an and/or list with && and || operators."""
        if not and_or.pipelines:
            return 0
        
        # Execute first pipeline
        status = self.shell.execute_pipeline(and_or.pipelines[0])
        self.state.last_exit_code = status
        
        # Process remaining pipelines with operators
        for i in range(len(and_or.operators)):
            operator = and_or.operators[i]
            next_pipeline = and_or.pipelines[i + 1]
            
            if operator == '&&':
                # Execute only if previous succeeded
                if status == 0:
                    status = self.shell.execute_pipeline(next_pipeline)
                    self.state.last_exit_code = status
            elif operator == '||':
                # Execute only if previous failed
                if status != 0:
                    status = self.shell.execute_pipeline(next_pipeline)
                    self.state.last_exit_code = status
        
        return status