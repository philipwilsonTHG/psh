"""Core shell builtins (exit, :, true, false, exec)."""

import sys
import os
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class ExitBuiltin(Builtin):
    """Exit the shell."""
    
    @property
    def name(self) -> str:
        return "exit"
    
    @property
    def synopsis(self) -> str:
        return "exit [n]"
    
    @property
    def description(self) -> str:
        return "Exit the shell"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Exit the shell with optional exit code."""
        exit_code = 0
        if len(args) > 1:
            try:
                exit_code = int(args[1])
                if exit_code < 0 or exit_code > 255:
                    self.error(f"{args[1]}: numeric argument required", shell)
                    exit_code = 2
            except ValueError:
                self.error(f"{args[1]}: numeric argument required", shell)
                exit_code = 2
        
        # Set the exit code in shell state for EXIT trap
        shell.state.last_exit_code = exit_code
        
        # Execute EXIT trap if set
        if hasattr(shell, 'trap_manager'):
            shell.trap_manager.execute_exit_trap()
        
        # Save history before exiting
        if hasattr(shell, '_save_history'):
            shell._save_history()
        
        sys.exit(exit_code)
    
    @property
    def help(self) -> str:
        return """exit: exit [n]
    Exit the shell.
    
    Exits the shell with a status of N. If N is omitted, the exit status
    is that of the last command executed.
    
    Exit Status:
    Returns N, or failure if an invalid argument is given."""


@builtin
class ColonBuiltin(Builtin):
    """Null command - does nothing and returns success."""
    
    @property
    def name(self) -> str:
        return ":"
    
    @property
    def synopsis(self) -> str:
        return ": [arguments]"
    
    @property
    def description(self) -> str:
        return "Null command that returns success"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Do nothing and return success."""
        return 0
    
    @property
    def help(self) -> str:
        return """: : [arguments]
    Null command.
    
    This command does nothing and always returns success (0).
    Any arguments are ignored. Useful as a placeholder or for parameter expansion
    side effects.
    
    Exit Status:
    Always returns success."""


@builtin
class TrueBuiltin(Builtin):
    """Always return success."""
    
    @property
    def name(self) -> str:
        return "true"
    
    @property
    def synopsis(self) -> str:
        return "true"
    
    @property
    def description(self) -> str:
        return "Always return success"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Always return success (0)."""
        return 0
    
    @property
    def help(self) -> str:
        return """true: true
    Always return success.
    
    Always returns success (exit code 0). Useful in conditional expressions.
    
    Exit Status:
    Always returns success."""


@builtin
class FalseBuiltin(Builtin):
    """Always return failure."""
    
    @property
    def name(self) -> str:
        return "false"
    
    @property
    def synopsis(self) -> str:
        return "false"
    
    @property
    def description(self) -> str:
        return "Always return failure"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Always return failure (1)."""
        return 1
    
    @property
    def help(self) -> str:
        return """false: false
    Always return failure.
    
    Always returns failure (exit code 1). Useful in conditional expressions.
    
    Exit Status:
    Always returns failure."""


@builtin
class ExecBuiltin(Builtin):
    """Execute commands and manipulate file descriptors."""
    
    @property
    def name(self) -> str:
        return "exec"
    
    @property
    def synopsis(self) -> str:
        return "exec [command [argument ...]]"
    
    @property
    def description(self) -> str:
        return "Execute commands and manipulate file descriptors"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute command or apply redirections."""
        # This is a placeholder implementation for registration.
        # The actual exec logic is handled specially in the executor
        # before normal builtin dispatch, since exec needs access to
        # the original SimpleCommand node with redirections.
        self.error("exec: internal error - should be handled by executor", shell)
        return 1
    
    @property
    def help(self) -> str:
        return """exec: exec [command [argument ...]]
    
    Execute commands and manipulate file descriptors.
    
    If command is specified, it replaces the shell without creating a new process.
    If no command is specified, any redirections take effect in the current shell.
    
    Examples:
        exec echo hello world    # Replace shell with echo command
        exec 3< file             # Open file descriptor 3 for reading
        exec 4> file             # Open file descriptor 4 for writing
        exec 5<&0                # Duplicate fd 0 to fd 5
        exec 3<&-                # Close file descriptor 3
    
    Exit Status:
        If command is specified: doesn't return (process replaced)
        Command not found: 127
        Command not executable: 126  
        Redirection error: 1-125
        Success (no command): 0"""