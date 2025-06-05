"""History expansion implementation for PSH.

This module implements bash-compatible history expansion, processing history
references like !!, !n, !-n, and !string before commands are tokenized.
"""

import re
import sys
from typing import List, Optional, Tuple


class HistoryExpander:
    """Handles history expansion for the shell."""
    
    def __init__(self, shell):
        self.shell = shell
        self.state = shell.state
        
    def expand_history(self, command: str) -> str:
        """Expand history references in a command string.
        
        Supports:
        - !! : Previous command
        - !n : Command number n
        - !-n : n commands back
        - !string : Most recent command starting with string
        - !?string? : Most recent command containing string
        """
        # Skip expansion if history expansion is disabled
        if hasattr(self.state, 'histexpand') and not self.state.histexpand:
            return command
            
        # Get history from the shell
        history = self.state.history
            
        # Track if we made any expansions
        expanded = False
        result = command
        
        # Pattern for history expansion
        # Matches: !!, !n, !-n, !string, !?string?
        # Use negative lookbehind to avoid matching ! preceded by !
        pattern = r'(?<![!])!(?:(!)|(-?\d+)|(\?[^?]+\?)|([^!?\s]+))'
        
        def replace_history(match):
            nonlocal expanded
            full_match = match.group(0)
            
            # !! - previous command
            if match.group(1):  # !!
                if history:
                    expanded = True
                    return history[-1]
                else:
                    print(f"psh: !!: event not found", file=sys.stderr)
                    raise ValueError("History expansion failed")
            
            # !n or !-n - numeric reference
            elif match.group(2):  # numeric
                n = int(match.group(2))
                
                if n > 0:
                    # !n - absolute position (1-based)
                    if n <= len(history):
                        expanded = True
                        return history[n - 1]
                    else:
                        print(f"psh: !{n}: event not found", file=sys.stderr)
                        raise ValueError("History expansion failed")
                else:
                    # !-n - relative position from end
                    if abs(n) <= len(history):
                        expanded = True
                        return history[n]  # n is already negative
                    else:
                        print(f"psh: !{n}: event not found", file=sys.stderr)
                        raise ValueError("History expansion failed")
            
            # !?string? - search for command containing string
            elif match.group(3):  # ?string?
                search_str = match.group(3)[1:-1]  # Remove the ? markers
                # Search backwards through history
                for i in range(len(history) - 1, -1, -1):
                    if search_str in history[i]:
                        expanded = True
                        return history[i]
                print(f"psh: !?{search_str}?: event not found", file=sys.stderr)
                raise ValueError("History expansion failed")
            
            # !string - search for command starting with string
            elif match.group(4):  # string
                search_prefix = match.group(4)
                # Search backwards through history
                for i in range(len(history) - 1, -1, -1):
                    if history[i].startswith(search_prefix):
                        expanded = True
                        return history[i]
                print(f"psh: !{search_prefix}: event not found", file=sys.stderr)
                raise ValueError("History expansion failed")
            
            # Should not reach here
            return full_match
        
        try:
            result = re.sub(pattern, replace_history, command)
            
            # If we made expansions, print the expanded command
            if expanded and sys.stdin.isatty():
                print(result)
                
            return result
            
        except ValueError:
            # History expansion failed, return None to indicate error
            return None
    
    def is_history_expansion_char(self, char: str) -> bool:
        """Check if a character might start a history expansion."""
        return char == '!'
    
    def get_history_list(self) -> List[str]:
        """Get the current history list."""
        return self.state.history.copy()
    
    def get_history_item(self, index: int) -> Optional[str]:
        """Get a specific history item by index (1-based)."""
        if 1 <= index <= len(self.state.history):
            return self.state.history[index - 1]
        return None