"""Statement list execution."""
from ..ast_nodes import CommandList, AndOrList, Pipeline, ASTNode
from .base import ExecutorComponent

class StatementExecutor(ExecutorComponent):
    """Executes statement lists and logical operators."""
    
    def execute(self, node: ASTNode) -> int:
        """Execute a statement node."""
        if isinstance(node, CommandList):
            return self.execute_command_list(node)
        elif isinstance(node, AndOrList):
            return self.execute_and_or_list(node)
        else:
            raise ValueError(f"Unknown statement node: {type(node)}")
    
    def execute_command_list(self, cmd_list: CommandList) -> int:
        """Execute a command list (statements separated by ;)."""
        last_status = 0
        
        for statement in cmd_list.statements:
            last_status = self.execute_and_or_list(statement)
            
        return last_status
    
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