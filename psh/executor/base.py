"""Base classes for executor components."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from ..ast_nodes import ASTNode
from ..core.state import ShellState
from ..core.exceptions import LoopBreak, LoopContinue

if TYPE_CHECKING:
    from ..shell import Shell


class ExecutorComponent(ABC):
    """Base class for all executor components."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        self.expansion_manager = shell.expansion_manager
        self.io_manager = shell.io_manager
        self.job_manager = shell.job_manager
        self.builtin_registry = shell.builtin_registry
        self.function_manager = shell.function_manager
    
    @abstractmethod
    def execute(self, node: ASTNode) -> int:
        """Execute the given AST node and return exit status."""
        pass
    
    def is_builtin(self, command: str) -> bool:
        """Check if a command is a builtin."""
        return self.builtin_registry.has(command)
    
    def is_function(self, command: str) -> bool:
        """Check if a command is a function."""
        return command in self.function_manager.functions


class ExecutorManager:
    """Manages all executor components and routes execution."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize executor components
        from .command import CommandExecutor
        from .pipeline import PipelineExecutor
        from .control_flow import ControlFlowExecutor
        from .statement import StatementExecutor
        from .arithmetic_command import ArithmeticCommandExecutor
        
        self.command_executor = CommandExecutor(shell)
        self.pipeline_executor = PipelineExecutor(shell)
        self.control_flow_executor = ControlFlowExecutor(shell)
        self.statement_executor = StatementExecutor(shell)
        self.arithmetic_executor = ArithmeticCommandExecutor(shell)
    
    def execute(self, node: ASTNode) -> int:
        """Route execution to appropriate executor based on node type."""
        from ..ast_nodes import (
            SimpleCommand, Pipeline, AndOrList, CommandList, TopLevel, StatementList,
            WhileLoop, ForLoop, CStyleForLoop, IfConditional, CaseConditional, 
            SelectLoop, ArithmeticEvaluation, EnhancedTestStatement, FunctionDef,
            BreakStatement, ContinueStatement
        )
        
        # Route to appropriate executor based on node type
        if isinstance(node, SimpleCommand):
            return self.command_executor.execute(node)
        elif isinstance(node, Pipeline):
            return self.pipeline_executor.execute(node)
        elif isinstance(node, (AndOrList, CommandList, TopLevel, StatementList)):
            return self.statement_executor.execute(node)
        elif isinstance(node, (WhileLoop, ForLoop, CStyleForLoop, IfConditional, 
                              CaseConditional, SelectLoop, BreakStatement, 
                              ContinueStatement, EnhancedTestStatement)):
            return self.control_flow_executor.execute(node)
        elif isinstance(node, ArithmeticEvaluation):
            return self.arithmetic_executor.execute(node)
        elif isinstance(node, FunctionDef):
            # Register the function and return 0
            try:
                self.shell.function_manager.define_function(node.name, node.body)
                return 0
            except ValueError as e:
                import sys
                print(f"psh: {e}", file=sys.stderr)
                return 1
        else:
            import sys
            print(f"psh: unknown node type: {type(node).__name__}", file=sys.stderr)
            return 1