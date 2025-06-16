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
        
        # Import Shell here to avoid circular import
        from ..shell import Shell
        
        # Create a pipe for capturing output
        read_fd, write_fd = os.pipe()
        
        pid = os.fork()
        if pid == 0:
            # Child process
            try:
                # Close read end
                os.close(read_fd)
                
                # Redirect stdout to write end of pipe
                os.dup2(write_fd, 1)
                os.close(write_fd)
                
                # Create a temporary shell to execute the command
                temp_shell = Shell(
                    debug_ast=self.state.debug_ast,
                    debug_tokens=self.state.debug_tokens,
                    parent_shell=self.shell,
                    norc=True
                )
                temp_shell.state._in_forked_child = True
                
                # Execute the command
                try:
                    exit_code = temp_shell.run_command(command, add_to_history=False)
                except SystemExit as e:
                    # Command substitution runs in a subshell, so exit should not affect parent
                    exit_code = e.code if e.code is not None else 0
                
                os._exit(exit_code)
            except Exception as e:
                # Exit with error
                os._exit(1)
        else:
            # Parent process
            # Close write end
            os.close(write_fd)
            
            # Read all output from child
            output_bytes = b''
            while True:
                chunk = os.read(read_fd, 4096)
                if not chunk:
                    break
                output_bytes += chunk
            
            os.close(read_fd)
            
            # Wait for child to finish
            try:
                _, status = os.waitpid(pid, 0)
            except OSError as e:
                # In some environments (like pytest), the child might have already been reaped
                # by a signal handler. In that case, assume it succeeded.
                if e.errno == 10:  # ECHILD - No child processes
                    status = 0
                else:
                    raise
            
            # Get exit code
            if os.WIFEXITED(status):
                exit_code = os.WEXITSTATUS(status)
            else:
                exit_code = 1
            
            # Update parent shell's last exit code for command substitution
            self.shell.state.last_exit_code = exit_code
            
            # Decode output
            output = output_bytes.decode('utf-8', errors='replace')
            
            # Strip trailing newline (bash behavior)
            if output.endswith('\n'):
                output = output[:-1]
            
            return output