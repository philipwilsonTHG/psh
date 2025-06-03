"""Tilde expansion implementation."""
import os
import pwd
from typing import TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class TildeExpander:
    """Handles tilde expansion (~, ~user)."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
    
    def expand(self, path: str) -> str:
        """Expand tilde in paths like ~ and ~user"""
        if not path.startswith('~'):
            return path
        
        # Just ~ or ~/path
        if path == '~' or path.startswith('~/'):
            # Get home directory from HOME env var, fallback to pwd
            home = os.environ.get('HOME')
            if not home:
                try:
                    home = pwd.getpwuid(os.getuid()).pw_dir
                except:
                    home = '/'
            
            if path == '~':
                return home
            else:
                return home + path[1:]  # Replace ~ with home
        
        # ~username or ~username/path
        else:
            # Find where username ends
            slash_pos = path.find('/')
            if slash_pos == -1:
                username = path[1:]  # Everything after ~
                rest = ''
            else:
                username = path[1:slash_pos]
                rest = path[slash_pos:]
            
            # Look up user's home directory
            try:
                user_info = pwd.getpwnam(username)
                return user_info.pw_dir + rest
            except KeyError:
                # User not found, return unchanged
                return path