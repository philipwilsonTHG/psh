"""I/O related builtins (echo, pwd)."""

import os
import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class EchoBuiltin(Builtin):
    """Echo arguments to stdout."""
    
    @property
    def name(self) -> str:
        return "echo"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Echo arguments to stdout."""
        if len(args) > 1:
            output = ' '.join(args[1:])
            print(output, file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        else:
            print(file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        return 0
    
    @property
    def help(self) -> str:
        return """echo: echo [arg ...]
    
    Display arguments separated by spaces, followed by a newline.
    If no arguments are given, print a blank line."""


@builtin
class PwdBuiltin(Builtin):
    """Print working directory."""
    
    @property
    def name(self) -> str:
        return "pwd"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Print the current working directory."""
        try:
            cwd = os.getcwd()
            print(cwd, file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            return 0
        except OSError as e:
            self.error(str(e), shell)
            return 1
    
    @property
    def help(self) -> str:
        return """pwd: pwd
    
    Print the current working directory."""