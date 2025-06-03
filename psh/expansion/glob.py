"""Glob (pathname) expansion implementation."""
import glob
from typing import List, TYPE_CHECKING
from ..core.state import ShellState

if TYPE_CHECKING:
    from ..shell import Shell


class GlobExpander:
    """Handles pathname expansion (globbing)."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
    
    def expand(self, pattern: str) -> List[str]:
        """
        Expand glob pattern.
        
        Returns a list of matching filenames, or the original pattern
        if no matches are found (bash behavior).
        """
        # Check if the pattern contains glob characters
        if not any(c in pattern for c in ['*', '?', '[']):
            return [pattern]
        
        # Perform glob expansion
        matches = glob.glob(pattern)
        
        if matches:
            # Sort matches for consistent output
            return sorted(matches)
        else:
            # No matches, return literal pattern (bash behavior)
            return [pattern]
    
    def should_expand(self, arg: str, arg_type: str) -> bool:
        """
        Check if an argument should undergo glob expansion.
        
        Args:
            arg: The argument to check
            arg_type: The type of the argument (WORD, STRING, etc.)
            
        Returns:
            True if the argument should be expanded, False otherwise
        """
        # Don't expand quoted strings
        if arg_type == 'STRING':
            return False
        
        # Check if contains glob characters
        return any(c in arg for c in ['*', '?', '['])