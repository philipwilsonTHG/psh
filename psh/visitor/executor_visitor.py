"""
Executor visitor that demonstrates execution using the visitor pattern.

This is a proof-of-concept showing how the executor could be refactored to use
the visitor pattern. It's not a complete implementation but shows the design.
"""

from typing import List, Dict, Any, Optional
import os
import sys
from .base import ASTVisitor
from ..ast_nodes import (
    ASTNode, SimpleCommand, Pipeline, AndOrList, StatementList,
    TopLevel, FunctionDef, BreakStatement, ContinueStatement,
    WhileLoop, ForLoop, IfConditional
)
from ..core.exceptions import LoopBreak, LoopContinue


class ExecutorVisitor(ASTVisitor[int]):
    """
    Visitor that executes AST nodes.
    
    This is a simplified demonstration of how execution could work with
    the visitor pattern. A full implementation would need to handle:
    - All node types
    - Process forking and job control
    - I/O redirection
    - Signal handling
    - Variable expansion
    - And much more
    """
    
    def __init__(self, shell_state):
        """
        Initialize the executor.
        
        Args:
            shell_state: The shell state object containing variables, functions, etc.
        """
        self.shell_state = shell_state
        self.builtin_registry = {}  # Would be injected
        self.function_registry = {}  # Would be injected
    
    # Top-level execution
    
    def visit_TopLevel(self, node: TopLevel) -> int:
        """Execute top-level script."""
        last_status = 0
        
        for item in node.items:
            try:
                last_status = self.visit(item)
                self.shell_state.last_exit_code = last_status
            except LoopBreak:
                # Break at top level is an error
                print("break: only meaningful in a loop", file=sys.stderr)
                last_status = 1
            except LoopContinue:
                # Continue at top level is an error
                print("continue: only meaningful in a loop", file=sys.stderr)
                last_status = 1
        
        return last_status
    
    def visit_StatementList(self, node: StatementList) -> int:
        """Execute a list of statements."""
        last_status = 0
        
        for stmt in node.statements:
            last_status = self.visit(stmt)
            self.shell_state.last_exit_code = last_status
        
        return last_status
    
    # Command execution
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        """Execute a simple command."""
        # This is a simplified version - real implementation would:
        # 1. Handle array assignments
        # 2. Expand arguments
        # 3. Apply redirections
        # 4. Handle builtins vs external commands
        # 5. Fork for external commands
        # 6. Handle job control
        
        if not node.args:
            return 0
        
        cmd_name = node.args[0]
        
        # Check for builtin
        if cmd_name in self.builtin_registry:
            return self._execute_builtin(cmd_name, node.args)
        
        # Check for function
        if cmd_name in self.function_registry:
            return self._execute_function(cmd_name, node.args)
        
        # External command (simplified)
        return self._execute_external(node.args)
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        """Execute a pipeline."""
        if len(node.commands) == 1:
            # Single command
            status = self.visit(node.commands[0])
            if node.negated:
                status = 0 if status != 0 else 1
            return status
        
        # Multi-command pipeline
        # Real implementation would:
        # 1. Create pipes
        # 2. Fork processes
        # 3. Connect stdin/stdout
        # 4. Wait for completion
        # 5. Return appropriate exit status
        
        # For now, just execute sequentially
        last_status = 0
        for cmd in node.commands:
            last_status = self.visit(cmd)
        
        if node.negated:
            last_status = 0 if last_status != 0 else 1
        
        return last_status
    
    def visit_AndOrList(self, node: AndOrList) -> int:
        """Execute an and/or list with short-circuit evaluation."""
        if not node.pipelines:
            return 0
        
        # Execute first pipeline
        status = self.visit(node.pipelines[0])
        
        # Process remaining pipelines based on operators
        for i, op in enumerate(node.operators):
            if i + 1 >= len(node.pipelines):
                break
            
            if op == '&&':
                # Execute next only if previous succeeded
                if status == 0:
                    status = self.visit(node.pipelines[i + 1])
                else:
                    # Short-circuit - skip remaining
                    break
            elif op == '||':
                # Execute next only if previous failed
                if status != 0:
                    status = self.visit(node.pipelines[i + 1])
                else:
                    # Short-circuit - skip remaining
                    break
        
        return status
    
    # Control structures
    
    def visit_WhileLoop(self, node: WhileLoop) -> int:
        """Execute a while loop."""
        last_status = 0
        
        while True:
            try:
                # Evaluate condition
                condition_status = self.visit(node.condition)
                if condition_status != 0:
                    break
                
                # Execute body
                last_status = self.visit(node.body)
                
            except LoopBreak as e:
                if e.level > 1:
                    # Re-raise with decremented level
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    # Re-raise with decremented level
                    raise LoopContinue(e.level - 1)
                continue
        
        return last_status
    
    def visit_ForLoop(self, node: ForLoop) -> int:
        """Execute a for loop."""
        last_status = 0
        
        # In real implementation, items would be expanded
        expanded_items = node.items
        
        for item in expanded_items:
            try:
                # Set loop variable
                self.shell_state.set_variable(node.variable, item)
                
                # Execute body
                last_status = self.visit(node.body)
                
            except LoopBreak as e:
                if e.level > 1:
                    raise LoopBreak(e.level - 1)
                break
            except LoopContinue as e:
                if e.level > 1:
                    raise LoopContinue(e.level - 1)
                continue
        
        return last_status
    
    def visit_IfConditional(self, node: IfConditional) -> int:
        """Execute an if statement."""
        # Evaluate main condition
        condition_status = self.visit(node.condition)
        
        if condition_status == 0:
            return self.visit(node.then_part)
        
        # Check elif conditions
        for elif_condition, elif_then in node.elif_parts:
            elif_status = self.visit(elif_condition)
            if elif_status == 0:
                return self.visit(elif_then)
        
        # Execute else part if present
        if node.else_part:
            return self.visit(node.else_part)
        
        return 0
    
    # Control flow
    
    def visit_BreakStatement(self, node: BreakStatement) -> int:
        """Execute a break statement."""
        raise LoopBreak(node.level)
    
    def visit_ContinueStatement(self, node: ContinueStatement) -> int:
        """Execute a continue statement."""
        raise LoopContinue(node.level)
    
    # Functions
    
    def visit_FunctionDef(self, node: FunctionDef) -> int:
        """Register a function definition."""
        self.function_registry[node.name] = node.body
        return 0
    
    # Helper methods
    
    def _execute_builtin(self, name: str, args: List[str]) -> int:
        """Execute a builtin command."""
        # Simplified - would delegate to builtin registry
        if name == 'echo':
            print(' '.join(args[1:]))
            return 0
        elif name == 'exit':
            exit_code = 0
            if len(args) > 1:
                try:
                    exit_code = int(args[1])
                except ValueError:
                    exit_code = 2
            sys.exit(exit_code)
        return 1
    
    def _execute_function(self, name: str, args: List[str]) -> int:
        """Execute a shell function."""
        # Simplified - would:
        # 1. Save positional parameters
        # 2. Set new positional parameters
        # 3. Push variable scope
        # 4. Execute function body
        # 5. Pop scope and restore parameters
        
        if name in self.function_registry:
            body = self.function_registry[name]
            return self.visit(body)
        return 1
    
    def _execute_external(self, args: List[str]) -> int:
        """Execute an external command."""
        # Simplified - real implementation would fork and exec
        try:
            # This is just for demonstration
            import subprocess
            result = subprocess.run(args, capture_output=False)
            return result.returncode
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1
    
    def generic_visit(self, node: ASTNode) -> int:
        """Default execution for unknown nodes."""
        print(f"Executor: unhandled node type {node.__class__.__name__}", file=sys.stderr)
        return 1