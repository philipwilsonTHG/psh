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
        # Store current directory as the old directory
        current_dir = os.getcwd()
        
        if len(args) > 1:
            path = args[1]
            
            # Handle cd - (change to previous directory)
            if path == '-':
                oldpwd = shell.env.get('OLDPWD')
                if oldpwd is None:
                    self.error("OLDPWD not set", shell)
                    return 1
                path = oldpwd
                # Print the directory we're changing to (bash behavior)
                print_new_dir = True
            else:
                print_new_dir = False
        else:
            # No argument - go to home directory
            path = shell.env.get('HOME', '/')
            print_new_dir = False
        
        # Expand tilde if shell supports it
        if hasattr(shell, '_expand_tilde'):
            path = shell._expand_tilde(path)
        
        try:
            os.chdir(path)
            # Update PWD and OLDPWD environment variables
            new_dir = os.getcwd()
            shell.env['OLDPWD'] = current_dir
            shell.env['PWD'] = new_dir
            
            # Print new directory for cd - command
            if print_new_dir:
                print(new_dir)
            
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
    Change the current directory to DIR.
    
    The default DIR is the value of the HOME shell variable.
    The variable CDPATH defines the search path for the directory
    containing DIR.
    
    Special directories:
      ~     User's home directory
      -     Previous working directory
    
    Exit Status:
    Returns 0 if the directory is changed; non-zero otherwise."""
    
    @property
    def synopsis(self) -> str:
        return "cd [dir]"
    
    @property
    def description(self) -> str:
        return "Change directory"