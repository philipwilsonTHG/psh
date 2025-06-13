"""
Metrics visitor for collecting code metrics from shell scripts.

This visitor analyzes AST nodes to gather statistics about script complexity,
command usage, and structure.
"""

from typing import Dict, Any, Set
from .base import ASTVisitor
from ..ast_nodes import (
    SimpleCommand, Pipeline, FunctionDef, WhileLoop, ForLoop, CStyleForLoop,
    IfConditional, CaseConditional, SelectLoop, StatementList, TopLevel,
    AndOrList
)


class MetricsVisitor(ASTVisitor[None]):
    """Collect metrics about shell scripts."""
    
    def __init__(self):
        """Initialize metrics collection."""
        super().__init__()
        self.metrics = {
            'total_commands': 0,
            'external_commands': 0,
            'builtin_commands': 0,
            'pipelines': 0,
            'functions': 0,
            'loops': 0,
            'conditionals': 0,
            'max_pipeline_length': 0,
            'max_nesting_depth': 0,
            'total_lines': 0,
            'variable_assignments': 0,
            'array_operations': 0,
            'command_substitutions': 0,
            'arithmetic_operations': 0,
        }
        self._current_depth = 0
        self._known_builtins = {
            'echo', 'cd', 'pwd', 'export', 'unset', 'exit', 'return',
            'true', 'false', 'test', '[', 'break', 'continue', 'eval',
            'source', '.', 'alias', 'unalias', 'set', 'declare', 'typeset',
            'local', 'readonly', 'shift', 'getopts', 'trap', 'wait',
            'jobs', 'fg', 'bg', 'kill', 'suspend', 'builtin', 'command',
            'type', 'hash', 'help', 'history', 'fc', 'read', 'printf'
        }
        self._function_names: Set[str] = set()
    
    def get_summary(self) -> str:
        """Get a formatted summary of collected metrics."""
        return f"""Script Metrics Summary:
═══════════════════════════════════════
Commands:
  Total Commands:        {self.metrics['total_commands']:>6}
  Built-in Commands:     {self.metrics['builtin_commands']:>6}
  External Commands:     {self.metrics['external_commands']:>6}
  
Structure:
  Functions Defined:     {self.metrics['functions']:>6}
  Pipelines:            {self.metrics['pipelines']:>6}
  Loops:                {self.metrics['loops']:>6}
  Conditionals:         {self.metrics['conditionals']:>6}
  
Complexity:
  Max Pipeline Length:   {self.metrics['max_pipeline_length']:>6}
  Max Nesting Depth:     {self.metrics['max_nesting_depth']:>6}
  
Advanced Features:
  Variable Assignments:  {self.metrics['variable_assignments']:>6}
  Array Operations:      {self.metrics['array_operations']:>6}
  Command Substitutions: {self.metrics['command_substitutions']:>6}
  Arithmetic Operations: {self.metrics['arithmetic_operations']:>6}"""
    
    def visit_TopLevel(self, node: TopLevel) -> None:
        """Visit top-level script structure."""
        for item in node.items:
            self.visit(item)
    
    def visit_StatementList(self, node: StatementList) -> None:
        """Visit a list of statements."""
        for statement in node.statements:
            self.visit(statement)
    
    def visit_AndOrList(self, node: AndOrList) -> None:
        """Visit pipelines connected by && or ||."""
        for pipeline in node.pipelines:
            self.visit(pipeline)
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> None:
        """Analyze a simple command."""
        self.metrics['total_commands'] += 1
        
        # Count variable assignments
        if node.array_assignments:
            self.metrics['array_operations'] += len(node.array_assignments)
        
        # Check for pure variable assignment
        if node.args and '=' in node.args[0] and not any(arg.startswith('-') for arg in node.args):
            # Likely a variable assignment
            self.metrics['variable_assignments'] += 1
            return
        
        # Categorize command
        if node.args:
            cmd = node.args[0]
            if cmd in self._known_builtins:
                self.metrics['builtin_commands'] += 1
            elif cmd in self._function_names:
                # Function call
                pass
            else:
                self.metrics['external_commands'] += 1
            
            # Check for command substitution in arguments
            for arg in node.args:
                if '$(' in arg or '`' in arg:
                    self.metrics['command_substitutions'] += 1
                if '$((' in arg:
                    self.metrics['arithmetic_operations'] += 1
    
    def visit_Pipeline(self, node: Pipeline) -> None:
        """Analyze a pipeline."""
        num_commands = len(node.commands)
        
        if num_commands > 1:
            self.metrics['pipelines'] += 1
            self.metrics['max_pipeline_length'] = max(
                self.metrics['max_pipeline_length'], 
                num_commands
            )
        
        # Visit each command in the pipeline
        for command in node.commands:
            self.visit(command)
    
    def visit_FunctionDef(self, node: FunctionDef) -> None:
        """Analyze a function definition."""
        self.metrics['functions'] += 1
        self._function_names.add(node.name)
        self._with_depth(lambda: self.visit(node.body))
    
    def visit_WhileLoop(self, node: WhileLoop) -> None:
        """Analyze a while loop."""
        self.metrics['loops'] += 1
        self._with_depth(lambda: (
            self.visit(node.condition),
            self.visit(node.body)
        ))
    
    def visit_ForLoop(self, node: ForLoop) -> None:
        """Analyze a for loop."""
        self.metrics['loops'] += 1
        # Check items for command substitution
        for item in node.items:
            if '$(' in item or '`' in item:
                self.metrics['command_substitutions'] += 1
        self._with_depth(lambda: self.visit(node.body))
    
    def visit_CStyleForLoop(self, node: CStyleForLoop) -> None:
        """Analyze a C-style for loop."""
        self.metrics['loops'] += 1
        self.metrics['arithmetic_operations'] += 1  # C-style loops use arithmetic
        self._with_depth(lambda: self.visit(node.body))
    
    def visit_IfConditional(self, node: IfConditional) -> None:
        """Analyze an if statement."""
        self.metrics['conditionals'] += 1
        self._with_depth(lambda: (
            self.visit(node.condition),
            self.visit(node.then_part),
            [self.visit(elif_cond) for elif_cond, _ in node.elif_parts],
            [self.visit(elif_then) for _, elif_then in node.elif_parts],
            self.visit(node.else_part) if node.else_part else None
        ))
    
    def visit_CaseConditional(self, node: CaseConditional) -> None:
        """Analyze a case statement."""
        self.metrics['conditionals'] += 1
        self._with_depth(lambda: [
            self.visit(item.commands) for item in node.items
        ])
    
    def visit_SelectLoop(self, node: SelectLoop) -> None:
        """Analyze a select loop."""
        self.metrics['loops'] += 1
        self.metrics['conditionals'] += 1  # Select is both loop and conditional
        self._with_depth(lambda: self.visit(node.body))
    
    def visit_ArithmeticEvaluation(self, node) -> None:
        """Analyze arithmetic evaluation."""
        self.metrics['arithmetic_operations'] += 1
    
    def visit_EnhancedTestStatement(self, node) -> None:
        """Analyze enhanced test [[...]]."""
        self.metrics['conditionals'] += 1
    
    def _with_depth(self, func):
        """Execute function while tracking nesting depth."""
        self._current_depth += 1
        self.metrics['max_nesting_depth'] = max(
            self.metrics['max_nesting_depth'],
            self._current_depth
        )
        try:
            result = func()
            # Handle various return types
            if isinstance(result, (list, tuple)):
                for item in result:
                    if item is not None:
                        pass  # Already processed in func
            return result
        finally:
            self._current_depth -= 1
    
    def generic_visit(self, node) -> None:
        """Handle unimplemented node types."""
        # For unimplemented nodes, try to visit children if it's a compound structure
        node_name = type(node).__name__
        
        # Known compound structures that might contain statements
        if hasattr(node, 'body') and hasattr(node.body, '__iter__'):
            for item in node.body:
                self.visit(item)
        elif hasattr(node, 'commands') and hasattr(node.commands, '__iter__'):
            for item in node.commands:
                self.visit(item)