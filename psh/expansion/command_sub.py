"""Command substitution implementation."""
import os
import tempfile
from typing import TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class CommandSubstitution:
    """Handles command substitution $(...) and `...`."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
    
    def execute(self, cmd_sub: str) -> str:
        """Execute command substitution and return output"""
        # Remove $(...) or `...`
        if cmd_sub.startswith('$(') and cmd_sub.endswith(')'):
            command = cmd_sub[2:-1]
        elif cmd_sub.startswith('`') and cmd_sub.endswith('`'):
            command = cmd_sub[1:-1]
        else:
            return ''
        
        # Use subprocess to capture output from both builtins and external commands
        import subprocess
        
        # Create a temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmpfile:
            temp_output = tmpfile.name
        
        try:
            # Import Shell here to avoid circular import
            from ..shell import Shell
            
            # Create a temporary shell to execute the command with output redirected
            # Use the same executor as the parent shell
            temp_shell = Shell(
                debug_ast=self.state.debug_ast,
                debug_tokens=self.state.debug_tokens,
                use_visitor_executor=self.shell.use_visitor_executor,
                parent_shell=self.shell
            )
            
            # Execute the command with output redirected to temp file
            temp_shell.run_command(f"{command} > {temp_output}", add_to_history=False)
            
            # Read the captured output
            with open(temp_output, 'r') as f:
                output = f.read()
            
            # Strip trailing newline (bash behavior)
            if output.endswith('\n'):
                output = output[:-1]
            
            return output
        finally:
            # Clean up temp file
            if os.path.exists(temp_output):
                os.unlink(temp_output)