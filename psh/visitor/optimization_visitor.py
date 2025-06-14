"""
AST optimization visitor for PSH.

This visitor implements various AST optimizations to improve execution performance.
It identifies and transforms common patterns that can be executed more efficiently.
"""

from typing import List, Optional
from .base import ASTTransformer
from ..ast_nodes import (
    ASTNode, Pipeline, SimpleCommand, AndOrList, StatementList,
    IfConditional, WhileLoop, ForLoop, CaseConditional,
    ArithmeticEvaluation, TopLevel
)


class OptimizationVisitor(ASTTransformer):
    """
    Optimize AST before execution.
    
    This visitor performs various optimizations:
    - Remove unnecessary cat commands in pipelines
    - Constant folding for arithmetic expressions
    - Dead code elimination
    - Simplify redundant constructs
    """
    
    def __init__(self):
        """Initialize the optimization visitor."""
        super().__init__()
        self.optimizations_applied = 0
    
    def visit_Pipeline(self, node: Pipeline) -> Pipeline:
        """Optimize pipeline commands."""
        # First, recursively optimize all commands in the pipeline
        optimized_commands = []
        for cmd in node.commands:
            optimized_commands.append(self.visit(cmd))
        
        # Optimization: Recursively remove unnecessary cats
        changed = True
        while changed:
            changed = False
            new_commands = []
            
            for i, cmd in enumerate(optimized_commands):
                # Skip leading cat
                if i == 0 and self._is_simple_cat(cmd) and len(optimized_commands) > 1:
                    self.optimizations_applied += 1
                    changed = True
                    continue
                    
                # Skip trailing cat
                if i == len(optimized_commands) - 1 and self._is_simple_cat(cmd) and len(optimized_commands) > 1:
                    self.optimizations_applied += 1
                    changed = True
                    continue
                    
                # Skip middle cats (cat between two other commands)
                if (i > 0 and i < len(optimized_commands) - 1 and 
                    self._is_simple_cat(cmd) and 
                    not self._is_simple_cat(optimized_commands[i-1]) and
                    not self._is_simple_cat(optimized_commands[i+1])):
                    # This cat is unnecessary in the middle
                    self.optimizations_applied += 1
                    changed = True
                    continue
                    
                new_commands.append(cmd)
            
            optimized_commands = new_commands
            
            # If only one command left, we're done
            if len(optimized_commands) <= 1:
                break
        
        # Return optimized pipeline
        return Pipeline(optimized_commands, node.negated)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> SimpleCommand:
        """Optimize simple commands."""
        # Optimization: Pre-expand literal strings that don't need runtime expansion
        optimized_args = []
        optimized_types = []
        optimized_quotes = []
        
        for i, (arg, arg_type, quote_type) in enumerate(zip(node.args, node.arg_types, node.quote_types)):
            # If it's a simple string with no special characters, we can optimize
            if arg_type == 'WORD' and not any(c in arg for c in ['$', '*', '?', '[', '~']):
                # This is a literal that doesn't need expansion
                optimized_args.append(arg)
                optimized_types.append('LITERAL')  # Mark as pre-expanded
                optimized_quotes.append(quote_type)
            else:
                optimized_args.append(arg)
                optimized_types.append(arg_type)
                optimized_quotes.append(quote_type)
        
        # Recursively optimize redirects
        optimized_redirects = [self.visit(r) for r in node.redirects]
        
        return SimpleCommand(
            args=optimized_args,
            arg_types=optimized_types,
            quote_types=optimized_quotes,
            redirects=optimized_redirects,
            background=node.background,
            array_assignments=node.array_assignments
        )
    
    def visit_IfConditional(self, node: IfConditional) -> ASTNode:
        """Optimize if statements."""
        # Check for constant conditions
        if self._is_constant_true(node.condition):
            # If condition is always true, replace with then_part
            self.optimizations_applied += 1
            return self.visit(node.then_part)
        elif self._is_constant_false(node.condition):
            # If condition is always false, check elif/else
            self.optimizations_applied += 1
            if node.elif_parts:
                # Convert first elif to if
                first_elif_cond, first_elif_then = node.elif_parts[0]
                new_if = IfConditional(
                    condition=first_elif_cond,
                    then_part=first_elif_then,
                    elif_parts=node.elif_parts[1:],
                    else_part=node.else_part,
                    redirects=node.redirects
                )
                return self.visit(new_if)
            elif node.else_part:
                return self.visit(node.else_part)
            else:
                # No else part, entire if can be removed
                return StatementList([])
        
        # Recursively optimize all parts
        return IfConditional(
            condition=self.visit(node.condition),
            then_part=self.visit(node.then_part),
            elif_parts=[(self.visit(c), self.visit(t)) for c, t in node.elif_parts],
            else_part=self.visit(node.else_part) if node.else_part else None,
            redirects=node.redirects
        )
    
    def visit_WhileLoop(self, node: WhileLoop) -> ASTNode:
        """Optimize while loops."""
        # Check for constant false condition
        if self._is_constant_false(node.condition):
            # While false loop never executes
            self.optimizations_applied += 1
            return StatementList([])
        
        # Recursively optimize
        return WhileLoop(
            condition=self.visit(node.condition),
            body=self.visit(node.body),
            redirects=node.redirects
        )
    
    def visit_ArithmeticEvaluation(self, node: ArithmeticEvaluation) -> ArithmeticEvaluation:
        """Optimize arithmetic expressions."""
        # For now, just return as-is
        # Future: implement constant folding for arithmetic
        return node
    
    def visit_StatementList(self, node: StatementList) -> StatementList:
        """Optimize statement lists."""
        # Remove empty statements and optimize each statement
        optimized_statements = []
        
        for stmt in node.statements:
            optimized = self.visit(stmt)
            # Skip empty statement lists
            if isinstance(optimized, StatementList) and not optimized.statements:
                continue
            optimized_statements.append(optimized)
        
        return StatementList(optimized_statements)
    
    def visit_TopLevel(self, node: TopLevel) -> TopLevel:
        """Optimize top-level items."""
        optimized_items = []
        
        for item in node.items:
            optimized = self.visit(item)
            # Skip empty items
            if isinstance(optimized, StatementList) and not optimized.statements:
                continue
            optimized_items.append(optimized)
        
        return TopLevel(optimized_items)
    
    def visit_AndOrList(self, node: AndOrList) -> AndOrList:
        """Optimize and/or lists."""
        optimized_pipelines = []
        
        for pipeline in node.pipelines:
            optimized = self.visit(pipeline)
            optimized_pipelines.append(optimized)
        
        return AndOrList(optimized_pipelines, node.operators)
    
    # Helper methods
    
    def _is_simple_cat(self, cmd: ASTNode) -> bool:
        """Check if a command is a simple 'cat' with no arguments."""
        if not isinstance(cmd, SimpleCommand):
            return False
        if not cmd.args:
            return False
        # Check if it's just 'cat' with no additional arguments
        return cmd.args[0] == 'cat' and len(cmd.args) == 1 and not cmd.redirects
    
    def _is_constant_true(self, condition: ASTNode) -> bool:
        """Check if a condition is always true."""
        if isinstance(condition, StatementList) and len(condition.statements) == 1:
            stmt = condition.statements[0]
            if isinstance(stmt, AndOrList) and len(stmt.pipelines) == 1:
                pipeline = stmt.pipelines[0]
                if len(pipeline.commands) == 1:
                    cmd = pipeline.commands[0]
                    if isinstance(cmd, SimpleCommand) and cmd.args == ['true']:
                        return True
        return False
    
    def _is_constant_false(self, condition: ASTNode) -> bool:
        """Check if a condition is always false."""
        if isinstance(condition, StatementList) and len(condition.statements) == 1:
            stmt = condition.statements[0]
            if isinstance(stmt, AndOrList) and len(stmt.pipelines) == 1:
                pipeline = stmt.pipelines[0]
                if len(pipeline.commands) == 1:
                    cmd = pipeline.commands[0]
                    if isinstance(cmd, SimpleCommand) and cmd.args == ['false']:
                        return True
        return False
    
    def get_optimization_stats(self) -> dict:
        """Get statistics about optimizations applied."""
        return {
            'optimizations_applied': self.optimizations_applied
        }