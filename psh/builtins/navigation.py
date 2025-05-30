"""Directory navigation builtins (cd)."""

import os
import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class CdBuiltin(Builtin):
    """Change directory."""
    
    @property
    def name(self) -> str:
        return "cd"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Change the current working directory."""
        if len(args) > 1:
            path = args[1]
        else:
            # No argument - go to home directory
            path = shell.env.get('HOME', '/')
        
        # Expand tilde if shell supports it
        if hasattr(shell, '_expand_tilde'):
            path = shell._expand_tilde(path)
        
        try:
            os.chdir(path)
            return 0
        except FileNotFoundError:
            self.error(f"{path}: No such file or directory", shell)
            return 1
        except NotADirectoryError:
            self.error(f"{path}: Not a directory", shell)
            return 1
        except PermissionError:
            self.error(f"{path}: Permission denied", shell)
            return 1
        except Exception as e:
            self.error(str(e), shell)
            return 1
    
    @property
    def help(self) -> str:
        return """cd: cd [dir]
    
    Change the current directory to dir. If dir is not specified,
    change to the value of the HOME environment variable."""