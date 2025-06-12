"""Shell syntax formatter for reconstructing shell code from AST nodes."""

from ..ast_nodes import (
    TopLevel, CommandList, AndOrList, Pipeline, Command, SimpleCommand,
    CompoundCommand, Redirect, FunctionDef, CaseItem, BreakStatement, ContinueStatement,
    WhileLoop, ForLoop, CStyleForLoop, IfConditional, CaseConditional,
    SelectLoop, ArithmeticEvaluation
)


class ShellFormatter:
    """Formats AST nodes back into shell syntax."""
    
    @staticmethod
    def format(node, indent_level=0):
        """Format AST node as shell syntax."""
        indent = "    " * indent_level
        
        if isinstance(node, TopLevel):
            # Format top-level items
            return '\n'.join(ShellFormatter.format(item) for item in node.items)
        
        elif isinstance(node, FunctionDef):
            # Format function definition
            result = f"{node.name} () "
            result += ShellFormatter.format(node.body)
            return result
        
        elif isinstance(node, CommandList):
            # Format command list with proper semicolons
            parts = []
            for i, stmt in enumerate(node.statements):
                part = ShellFormatter.format(stmt, indent_level)
                # Add semicolon between statements if needed
                if i < len(node.statements) - 1:
                    if not part.rstrip().endswith(('&', ';')):
                        part = part.rstrip() + ';'
                parts.append(part)
            
            # If in a block context (with braces), format with newlines
            if indent_level > 0:
                return '\n'.join(f"{indent}{part}" for part in parts)
            else:
                return ' '.join(parts)
        
        elif isinstance(node, AndOrList):
            # Format pipelines with && and || operators
            result = ShellFormatter.format(node.pipelines[0], indent_level)
            for i, op in enumerate(node.operators):
                result += f" {op} "
                result += ShellFormatter.format(node.pipelines[i + 1], indent_level)
            return result
        
        elif isinstance(node, Pipeline):
            # Format pipeline with | between commands
            parts = []
            for cmd in node.commands:
                parts.append(ShellFormatter.format(cmd, indent_level))
            return ' | '.join(parts)
        
        elif isinstance(node, SimpleCommand):
            # Format simple command with arguments, preserving quotes
            parts = []
            for i, arg in enumerate(node.args):
                # Check if we need to add quotes back
                if hasattr(node, 'quote_types') and i < len(node.quote_types) and node.quote_types[i]:
                    # Add back the original quotes
                    quote_char = node.quote_types[i]
                    parts.append(f"{quote_char}{arg}{quote_char}")
                else:
                    # Check if arg needs quoting (contains spaces or special chars)
                    if ' ' in arg or '\t' in arg or '\n' in arg or ';' in arg or '&' in arg or '|' in arg:
                        # Use single quotes if arg contains double quotes, otherwise use double quotes
                        if '"' in arg and "'" not in arg:
                            parts.append(f"'{arg}'")
                        else:
                            parts.append(f'"{arg}"')
                    else:
                        parts.append(arg)
            
            result = ' '.join(parts)
            
            # Add redirections
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            # Add background marker
            if node.background:
                result += ' &'
            
            return result
        
        elif isinstance(node, WhileLoop):
            result = "while "
            result += ShellFormatter.format(node.condition, indent_level)
            result += "; do\n"
            result += ShellFormatter.format(node.body, indent_level + 1)
            result += f"\n{indent}done"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, ForLoop):
            result = f"for {node.variable} in"
            for item in node.items:
                result += f" {item}"
            result += "; do\n"
            result += ShellFormatter.format(node.body, indent_level + 1)
            result += f"\n{indent}done"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, CStyleForLoop):
            result = "for (("
            if node.init:
                result += node.init
            result += "; "
            if node.condition:
                result += node.condition
            result += "; "
            if node.update:
                result += node.update
            result += ")); do\n"
            result += ShellFormatter.format(node.body, indent_level + 1)
            result += f"\n{indent}done"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, IfConditional):
            result = "if "
            result += ShellFormatter.format(node.condition, indent_level)
            result += "; then\n"
            result += ShellFormatter.format(node.then_part, indent_level + 1)
            
            if node.else_part:
                result += f"\n{indent}else\n"
                result += ShellFormatter.format(node.else_part, indent_level + 1)
            
            result += f"\n{indent}fi"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, CaseConditional):
            result = f"case {node.expr} in\n"
            for item in node.items:
                result += ShellFormatter._format_case_item(item, indent_level + 1)
            result += f"{indent}esac"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, SelectLoop):
            result = f"select {node.variable} in"
            for item in node.items:
                result += f" {item}"
            result += "; do\n"
            result += ShellFormatter.format(node.body, indent_level + 1)
            result += f"\n{indent}done"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, ArithmeticEvaluation):
            result = f"(({node.expression}))"
            
            # Add redirections if present
            for redirect in node.redirects:
                result += ' ' + ShellFormatter._format_redirect(redirect)
            
            return result
        
        elif isinstance(node, BreakStatement):
            if node.levels and node.levels != 1:
                return f"break {node.levels}"
            return "break"
        
        elif isinstance(node, ContinueStatement):
            if node.levels and node.levels != 1:
                return f"continue {node.levels}"
            return "continue"
        
        else:
            # For compound commands when used as a body
            if hasattr(node, 'body') and isinstance(node.body, CommandList):
                result = "{ "
                result += ShellFormatter.format(node.body, indent_level)
                result += " }"
                return result
            
            # Fallback
            return f"# Unknown node type: {type(node).__name__}"
    
    @staticmethod
    def _format_redirect(redirect):
        """Format a single redirection."""
        result = ""
        
        # Add file descriptor if specified
        if redirect.fd is not None:
            result += str(redirect.fd)
        
        # Add redirection operator
        result += redirect.type
        
        # Add target
        if redirect.dup_fd is not None:
            result += str(redirect.dup_fd)
        elif redirect.heredoc_content is not None:
            # For here documents, just show the delimiter
            result += redirect.target
        else:
            result += redirect.target
        
        return result
    
    @staticmethod
    def _format_case_item(item, indent_level):
        """Format a case item."""
        indent = "    " * indent_level
        result = indent
        
        # Format patterns
        result += '|'.join(item.patterns)
        result += ")\n"
        
        # Format commands
        result += ShellFormatter.format(item.commands, indent_level + 1)
        
        # Add terminator
        result += f"\n{indent}{item.terminator}\n"
        
        return result
    
    @staticmethod
    def format_function_body(func):
        """Format a function body for display."""
        # Functions have a CommandList body
        if hasattr(func.body, 'statements'):
            # Format with braces
            result = "{ \n"
            for stmt in func.body.statements:
                result += "    " + ShellFormatter.format(stmt, 1) + "\n"
            result += "}"
            return result
        else:
            # Fallback for other body types
            return "{\n    " + ShellFormatter.format(func.body, 1) + "\n}"