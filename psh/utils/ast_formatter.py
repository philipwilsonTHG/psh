"""AST formatting utilities for debugging."""
from ..ast_nodes import (
    TopLevel, CommandList, AndOrList, Pipeline, Command, SimpleCommand,
    CompoundCommand, WhileCommand, ForCommand, CStyleForCommand, IfCommand,
    CaseCommand, SelectCommand, ArithmeticCompoundCommand, Redirect,
    FunctionDef, IfStatement, WhileStatement, ForStatement, CaseStatement,
    CaseItem, BreakStatement, ContinueStatement
)

class ASTFormatter:
    """Formats AST nodes for debug output."""
    
    @staticmethod
    def format(node, indent=0):
        """Format AST node for debugging output."""
        spaces = "  " * indent
        
        if isinstance(node, TopLevel):
            result = f"{spaces}TopLevel:\n"
            for item in node.items:
                result += ASTFormatter.format(item, indent + 1)
            return result
        
        elif isinstance(node, CommandList):
            result = f"{spaces}CommandList:\n"
            for stmt in node.statements:
                result += ASTFormatter.format(stmt, indent + 1)
            return result
        
        elif isinstance(node, AndOrList):
            result = f"{spaces}AndOrList:\n"
            for i, pipeline in enumerate(node.pipelines):
                if i < len(node.operators):
                    result += f"{spaces}  Operator: {node.operators[i]}\n"
                result += ASTFormatter.format(pipeline, indent + 1)
            return result
        
        elif isinstance(node, Pipeline):
            result = f"{spaces}Pipeline:\n"
            for cmd in node.commands:
                result += ASTFormatter.format(cmd, indent + 1)
            return result
        
        elif isinstance(node, SimpleCommand):
            result = f"{spaces}SimpleCommand: {' '.join(node.args)}"
            if node.background:
                result += " &"
            result += "\n"
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, WhileCommand):
            result = f"{spaces}WhileCommand:\n"
            result += f"{spaces}  Condition:\n"
            result += ASTFormatter.format(node.condition, indent + 2)
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, ForCommand):
            result = f"{spaces}ForCommand:\n"
            result += f"{spaces}  Variable: {node.variable}\n"
            result += f"{spaces}  Items: {node.items}\n"
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, CStyleForCommand):
            result = f"{spaces}CStyleForCommand:\n"
            result += f"{spaces}  Init: {node.init}\n"
            result += f"{spaces}  Condition: {node.condition}\n"
            result += f"{spaces}  Update: {node.update}\n"
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, IfCommand):
            result = f"{spaces}IfCommand:\n"
            result += f"{spaces}  Condition:\n"
            result += ASTFormatter.format(node.condition, indent + 2)
            result += f"{spaces}  Then:\n"
            result += ASTFormatter.format(node.then_part, indent + 2)
            if node.else_part:
                result += f"{spaces}  Else:\n"
                result += ASTFormatter.format(node.else_part, indent + 2)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, CaseCommand):
            result = f"{spaces}CaseCommand:\n"
            result += f"{spaces}  Expression: {node.expr}\n"
            for item in node.items:
                result += ASTFormatter.format(item, indent + 1)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, SelectCommand):
            result = f"{spaces}SelectCommand:\n"
            result += f"{spaces}  Variable: {node.variable}\n"
            result += f"{spaces}  Items: {node.items}\n"
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, ArithmeticCompoundCommand):
            result = f"{spaces}ArithmeticCompoundCommand:\n"
            result += f"{spaces}  Expression: {node.expression}\n"
            for redirect in node.redirects:
                result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, Command):
            # Fallback for any other Command types
            result = f"{spaces}{type(node).__name__}:\n"
            if hasattr(node, 'redirects'):
                for redirect in node.redirects:
                    result += ASTFormatter.format(redirect, indent + 1)
            return result
        
        elif isinstance(node, Redirect):
            result = f"{spaces}Redirect: "
            if node.fd is not None:
                result += f"{node.fd}"
            result += f"{node.type} {node.target}"
            if node.dup_fd is not None:
                result += f" (dup fd {node.dup_fd})"
            if node.heredoc_content:
                result += f" (heredoc: {len(node.heredoc_content)} chars)"
            result += "\n"
            return result
        
        elif isinstance(node, FunctionDef):
            result = f"{spaces}FunctionDef: {node.name}()\n"
            result += ASTFormatter.format(node.body, indent + 1)
            return result
        
        elif isinstance(node, IfStatement):
            result = f"{spaces}IfStatement:\n"
            result += f"{spaces}  Condition:\n"
            result += ASTFormatter.format(node.condition, indent + 2)
            result += f"{spaces}  Then:\n"
            result += ASTFormatter.format(node.then_part, indent + 2)
            
            # Format elif parts
            for i, (elif_cond, elif_then) in enumerate(node.elif_parts):
                result += f"{spaces}  Elif {i+1} Condition:\n"
                result += ASTFormatter.format(elif_cond, indent + 2)
                result += f"{spaces}  Elif {i+1} Then:\n"
                result += ASTFormatter.format(elif_then, indent + 2)
            
            if node.else_part:
                result += f"{spaces}  Else:\n"
                result += ASTFormatter.format(node.else_part, indent + 2)
            return result
        
        elif isinstance(node, WhileStatement):
            result = f"{spaces}WhileStatement:\n"
            result += f"{spaces}  Condition:\n"
            result += ASTFormatter.format(node.condition, indent + 2)
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            return result
        
        elif isinstance(node, ForStatement):
            result = f"{spaces}ForStatement:\n"
            result += f"{spaces}  Variable: {node.variable}\n"
            result += f"{spaces}  Iterable: {node.iterable}\n"
            result += f"{spaces}  Body:\n"
            result += ASTFormatter.format(node.body, indent + 2)
            return result
        
        elif isinstance(node, CaseStatement):
            result = f"{spaces}CaseStatement: {node.expr}\n"
            for item in node.items:
                result += ASTFormatter.format(item, indent + 1)
            return result
        
        elif isinstance(node, CaseItem):
            patterns = " | ".join(p.pattern for p in node.patterns)
            result = f"{spaces}CaseItem: {patterns}) terminator={node.terminator}\n"
            result += ASTFormatter.format(node.commands, indent + 1)
            return result
        
        elif isinstance(node, BreakStatement):
            return f"{spaces}BreakStatement(level={node.level})\n"
        
        elif isinstance(node, ContinueStatement):
            return f"{spaces}ContinueStatement(level={node.level})\n"
        
        else:
            return f"{spaces}{type(node).__name__}: {repr(node)}\n"