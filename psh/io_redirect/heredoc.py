"""Here document implementation."""
import tempfile
from typing import Optional, TYPE_CHECKING
from ..ast_nodes import CommandList, AndOrList, WhileLoop, ForLoop, CStyleForLoop, IfConditional, CaseConditional, SelectLoop

if TYPE_CHECKING:
    from ..shell import Shell


class HeredocHandler:
    """Handles here document collection and processing."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
    
    def collect_heredocs(self, node):
        """Collect here document content for all commands in a node."""
        if isinstance(node, CommandList):
            # Process all statements in the command list
            for item in node.statements:
                self.collect_heredocs(item)
                
        elif isinstance(node, AndOrList):
            # Process pipelines in and_or_list
            for pipeline in node.pipelines:
                for command in pipeline.commands:
                    for redirect in command.redirects:
                        if redirect.type in ('<<', '<<-'):
                            # Collect here document content
                            self._read_heredoc_content(redirect)
                            
        elif isinstance(node, IfConditional):
            # Recursively collect for if statement parts
            self.collect_heredocs(node.condition)
            self.collect_heredocs(node.then_part)
            # Collect from elif parts
            for elif_condition, elif_then in node.elif_parts:
                self.collect_heredocs(elif_condition)
                self.collect_heredocs(elif_then)
            if node.else_part:
                self.collect_heredocs(node.else_part)
                
        elif isinstance(node, WhileLoop):
            # Recursively collect for while statement parts
            self.collect_heredocs(node.condition)
            self.collect_heredocs(node.body)
            
        elif isinstance(node, ForLoop):
            # Recursively collect for for statement body
            self.collect_heredocs(node.body)
            
        elif isinstance(node, CaseConditional):
            # Recursively collect for case statement items
            for item in node.items:
                # item.commands is a StatementList, not a list
                if item.commands:
                    self.collect_heredocs(item.commands)
    
    def _read_heredoc_content(self, redirect):
        """Read heredoc content from input until delimiter is found."""
        # Skip if content is already populated (from parser)
        if redirect.heredoc_content is not None:
            return
            
        # Fall back to reading from stdin (for interactive mode)
        lines = []
        delimiter = redirect.target
        
        # Read lines until we find the delimiter
        while True:
            try:
                line = input()
                if line.strip() == delimiter:
                    break
                if redirect.type == '<<-':
                    # Strip leading tabs
                    line = line.lstrip('\t')
                lines.append(line)
            except EOFError:
                break
        
        redirect.heredoc_content = '\n'.join(lines)
        if lines:  # Add final newline if there was content
            redirect.heredoc_content += '\n'
    
    def create_heredoc_file(self, content: str, strip_tabs: bool = False) -> str:
        """
        Create a temporary file for heredoc content.
        
        Args:
            content: The heredoc content
            strip_tabs: Whether to strip leading tabs (for <<- operator)
            
        Returns:
            Path to the temporary file
        """
        # Process content if needed
        if strip_tabs:
            lines = content.split('\n')
            processed_lines = []
            for line in lines:
                # Strip leading tabs only
                processed_lines.append(line.lstrip('\t'))
            content = '\n'.join(processed_lines)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            return f.name
    
    def expand_variables_in_heredoc(self, content: str, delimiter: str) -> str:
        """
        Expand variables in heredoc content if delimiter is not quoted.
        
        Args:
            content: The heredoc content
            delimiter: The heredoc delimiter (to check if quoted)
            
        Returns:
            Content with variables expanded (if applicable)
        """
        # If delimiter was quoted, don't expand variables
        if delimiter.startswith(("'", '"')) and delimiter.endswith(("'", '"')):
            return content
        
        # Otherwise, expand variables in the content
        return self.shell.expansion_manager.expand_string_variables(content)