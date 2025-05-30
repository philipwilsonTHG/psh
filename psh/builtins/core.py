"""Core shell builtins (exit, :, true, false)."""

import sys
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
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Exit the shell with optional exit code."""
        # Save history before exiting
        if hasattr(shell, '_save_history'):
            shell._save_history()
        
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
        
        sys.exit(exit_code)


@builtin
class ColonBuiltin(Builtin):
    """Null command - does nothing and returns success."""
    
    @property
    def name(self) -> str:
        return ":"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Do nothing and return success."""
        return 0
    
    @property
    def help(self) -> str:
        return """: : [arguments]
    
    Null command. This command does nothing and always returns success (0).
    Any arguments are ignored. Useful as a placeholder or for parameter expansion
    side effects."""


@builtin
class TrueBuiltin(Builtin):
    """Always return success."""
    
    @property
    def name(self) -> str:
        return "true"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Always return success (0)."""
        return 0
    
    @property
    def help(self) -> str:
        return """true: true
    
    Always returns success (exit code 0). Useful in conditional expressions."""


@builtin
class FalseBuiltin(Builtin):
    """Always return failure."""
    
    @property
    def name(self) -> str:
        return "false"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Always return failure (1)."""
        return 1
    
    @property
    def help(self) -> str:
        return """false: false
    
    Always returns failure (exit code 1). Useful in conditional expressions."""