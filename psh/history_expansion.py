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
        result = []
        i = 0
        
        # Process the command character by character to handle quotes properly
        while i < len(command):
            char = command[i]
            
            # Handle single quotes - no expansion inside
            if char == "'":
                # Find the closing quote
                j = i + 1
                while j < len(command) and command[j] != "'":
                    j += 1
                # Include the entire quoted string
                result.append(command[i:j+1] if j < len(command) else command[i:])
                i = j + 1
                continue
            
            # Handle double quotes - no history expansion inside
            elif char == '"':
                # Find the closing quote, handling escapes
                j = i + 1
                while j < len(command):
                    if command[j] == '"' and (j == i + 1 or command[j-1] != '\\'):
                        break
                    j += 1
                # Include the entire quoted string
                result.append(command[i:j+1] if j < len(command) else command[i:])
                i = j + 1
                continue
            
            # Handle history expansion
            elif char == '!' and i + 1 < len(command) and command[i+1] != '=':
                # Skip if we're inside ${...} parameter expansion
                # Look backwards for ${ without closing }
                j = i - 1
                brace_depth = 0
                while j >= 0:
                    if command[j] == '}':
                        brace_depth += 1
                    elif command[j] == '{' and j > 0 and command[j-1] == '$':
                        if brace_depth == 0:
                            # We're inside ${...}, skip history expansion
                            result.append(char)
                            i += 1
                            break
                        else:
                            brace_depth -= 1
                    j -= 1
                else:
                    # Not inside ${...}, continue with history expansion
                    # Check for !!
                    if i + 1 < len(command) and command[i+1] == '!':
                        if history:
                            expanded = True
                            result.append(history[-1])
                            i += 2
                            continue
                        else:
                            print(f"psh: !!: event not found", file=sys.stderr)
                            return None
                    
                    # Check for numeric (!n or !-n)
                    j = i + 1
                    if j < len(command) and (command[j] == '-' or command[j].isdigit()):
                        # Collect the number
                        if command[j] == '-':
                            j += 1
                        while j < len(command) and command[j].isdigit():
                            j += 1
                        
                        n = int(command[i+1:j])
                        if n > 0:
                            # !n - absolute position (1-based)
                            if n <= len(history):
                                expanded = True
                                result.append(history[n - 1])
                                i = j
                                continue
                            else:
                                print(f"psh: !{n}: event not found", file=sys.stderr)
                                return None
                        else:
                            # !-n - relative position from end
                            if abs(n) <= len(history):
                                expanded = True
                                result.append(history[n])  # n is already negative
                                i = j
                                continue
                            else:
                                print(f"psh: !{n}: event not found", file=sys.stderr)
                                return None
                    
                    # Check for !?string?
                    if i + 1 < len(command) and command[i+1] == '?':
                        j = i + 2
                        while j < len(command) and command[j] != '?':
                            j += 1
                        if j < len(command):
                            search_str = command[i+2:j]
                            # Search backwards through history
                            for k in range(len(history) - 1, -1, -1):
                                if search_str in history[k]:
                                    expanded = True
                                    result.append(history[k])
                                    i = j + 1
                                    break
                            else:
                                print(f"psh: !?{search_str}?: event not found", file=sys.stderr)
                                return None
                            continue
                    
                    # Check for !string
                    j = i + 1
                    while j < len(command) and not command[j].isspace() and command[j] not in '!?;|&(){}[]<>':
                        j += 1
                    if j > i + 1:
                        search_prefix = command[i+1:j]
                        # Search backwards through history
                        for k in range(len(history) - 1, -1, -1):
                            if history[k].startswith(search_prefix):
                                expanded = True
                                result.append(history[k])
                                i = j
                                break
                        else:
                            print(f"psh: !{search_prefix}: event not found", file=sys.stderr)
                            return None
                        continue
                    
                    # If ! is not followed by any recognized pattern, treat it as a regular character
                    # This handles cases like [[ ! ... ]] where ! is followed by space
                    result.append(char)
                    i += 1
                    continue
                
                # If we broke from the while loop (we're inside ${...}), skip regular char processing
                continue
            
            # Regular character
            result.append(char)
            i += 1
        
        final_result = ''.join(result)
        
        # If we made expansions, print the expanded command
        if expanded and sys.stdin.isatty():
            print(final_result)
            
        return final_result
    
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