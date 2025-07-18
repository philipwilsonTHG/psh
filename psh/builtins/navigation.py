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
        # Store current directory as the old directory (use logical path if available)
        try:
            pwd = shell.state.get_variable('PWD')
            # Check if PWD is a valid string (not None or mock)
            current_dir = pwd if isinstance(pwd, str) and pwd else os.getcwd()
        except (AttributeError, TypeError):
            # Handle case where shell.state is a mock or doesn't exist
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
        
        # For relative paths, check CDPATH for directory search
        actual_path = path
        found_in_cdpath = False
        
        if not os.path.isabs(path):
            # If it's not a relative path starting with . or .., search CDPATH
            if not (path.startswith('./') or path.startswith('../') or path == '.' or path == '..'):
                # Check both shell variables and environment variables for CDPATH
                cdpath = shell.state.get_variable('CDPATH') or shell.env.get('CDPATH', '')
                if cdpath:
                    # Split CDPATH on colons and search each directory
                    for search_dir in cdpath.split(':'):
                        if search_dir == '':
                            # Empty string in CDPATH means current directory
                            search_dir = '.'
                        
                        candidate_path = os.path.join(search_dir, path)
                        if os.path.isdir(candidate_path):
                            actual_path = candidate_path
                            found_in_cdpath = True
                            break
        
        try:
            # Compute the logical new directory path
            if os.path.isabs(actual_path):
                # Absolute path - use as-is
                logical_new_dir = actual_path
            else:
                # Relative path - resolve logically from current PWD
                try:
                    pwd = shell.state.get_variable('PWD')
                    logical_current = pwd if isinstance(pwd, str) and pwd else os.getcwd()
                except (AttributeError, TypeError):
                    logical_current = os.getcwd()
                logical_new_dir = os.path.normpath(os.path.join(logical_current, actual_path))
            
            # Change to the actual directory
            os.chdir(actual_path)
            
            # If found via CDPATH, print the full path (bash behavior)
            if found_in_cdpath:
                print(logical_new_dir)
            
            # Update PWD and OLDPWD environment variables and shell variables
            shell.env['OLDPWD'] = current_dir
            shell.env['PWD'] = logical_new_dir
            # Also update shell state variables so they're available for expansion (if not mock)
            try:
                shell.state.set_variable('OLDPWD', current_dir)
                shell.state.set_variable('PWD', logical_new_dir)
            except (AttributeError, TypeError):
                # Handle case where shell.state is a mock
                pass
            
            # Print new directory for cd - command
            if print_new_dir:
                print(logical_new_dir)
            
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
    
    The variable CDPATH defines the search path for directories.
    When DIR is a relative path not starting with './' or '../',
    cd searches the directories in CDPATH (colon-separated list)
    for a directory named DIR. If found, the full path is printed.
    
    Special directories:
      ~     User's home directory
      -     Previous working directory
    
    Examples:
      cd              # Go to $HOME
      cd /usr/local   # Absolute path
      cd mydir        # Relative path (may search CDPATH)
      cd ./mydir      # Relative path (current dir only)
      cd -            # Previous directory
    
    Exit Status:
    Returns 0 if the directory is changed; non-zero otherwise."""
    
    @property
    def synopsis(self) -> str:
        return "cd [dir]"
    
    @property
    def description(self) -> str:
        return "Change directory"