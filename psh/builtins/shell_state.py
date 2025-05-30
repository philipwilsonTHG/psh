"""Shell state related builtins (history, version)."""

import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class HistoryBuiltin(Builtin):
    """Display command history."""
    
    @property
    def name(self) -> str:
        return "history"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Display command history."""
        if len(args) > 1:
            try:
                count = int(args[1])
                if count < 0:
                    self.error(f"{args[1]}: invalid option", shell)
                    return 1
            except ValueError:
                self.error(f"{args[1]}: numeric argument required", shell)
                return 1
        else:
            # Default to showing last 10 commands (bash behavior)
            count = 10
        
        # Calculate the starting index
        history = shell.history
        start = max(0, len(history) - count)
        history_slice = history[start:]
        
        # Print with line numbers
        start_num = len(history) - len(history_slice) + 1
        for i, cmd in enumerate(history_slice):
            print(f"{start_num + i:5d}  {cmd}", 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        
        return 0
    
    @property
    def help(self) -> str:
        return """history: history [n]
    
    Display the command history list with line numbers.
    If n is given, show only the last n entries.
    Default is to show the last 10 commands."""


@builtin
class VersionBuiltin(Builtin):
    """Display version information."""
    
    @property
    def name(self) -> str:
        return "version"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Display version information."""
        from ..version import __version__, get_version_info
        
        if len(args) > 1 and args[1] == '--short':
            # Just print version number
            print(__version__, 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        else:
            # Full version info
            print(get_version_info(), 
                  file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        
        return 0
    
    @property
    def help(self) -> str:
        return """version: version [--short]
    
    Display version information for Python Shell (psh).
    With --short, display only the version number."""