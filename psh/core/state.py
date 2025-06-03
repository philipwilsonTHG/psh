"""Shell state management."""
import os
import sys
from typing import List, Dict, Optional, Any

class ShellState:
    """Container for shell state that can be shared across components."""
    
    def __init__(self, args=None, script_name=None, debug_ast=False, 
                 debug_tokens=False, norc=False, rcfile=None):
        # Environment and variables
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported)
        
        # Default prompt variables
        self.variables['PS1'] = 'psh$ '
        self.variables['PS2'] = '> '
        
        # Positional parameters and script info
        self.positional_params = args if args else []
        self.script_name = script_name or "psh"
        self.is_script_mode = script_name is not None and script_name != "psh"
        
        # Debug flags
        self.debug_ast = debug_ast
        self.debug_tokens = debug_tokens
        
        # RC file options
        self.norc = norc
        self.rcfile = rcfile
        
        # Execution state
        self.last_exit_code = 0
        self.last_bg_pid = None
        self.foreground_pgid = None
        self.command_number = 0
        
        # History settings
        self.history = []
        self.history_file = os.path.expanduser("~/.psh_history")
        self.max_history_size = 1000
        self.history_index = -1
        self.current_line = ""
        
        # Editor configuration
        self.edit_mode = 'emacs'
        
        # Function call stack
        self.function_stack = []
        
        # Process state
        self._in_forked_child = False
        
        # I/O streams (for backward compatibility)
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stdin = sys.stdin
    
    def get_variable(self, name: str, default: str = '') -> str:
        """Get variable value, checking shell variables first, then environment."""
        return self.variables.get(name, self.env.get(name, default))
    
    def set_variable(self, name: str, value: str):
        """Set a shell variable."""
        self.variables[name] = value
    
    def export_variable(self, name: str, value: str):
        """Export a variable to the environment."""
        self.variables[name] = value
        self.env[name] = value
    
    def get_positional_param(self, index: int) -> str:
        """Get positional parameter by index (1-based)."""
        if 1 <= index <= len(self.positional_params):
            return self.positional_params[index - 1]
        return ''
    
    def get_special_variable(self, name: str) -> str:
        """Get special variable value ($?, $$, $!, etc.)."""
        if name == '?':
            return str(self.last_exit_code)
        elif name == '$':
            return str(os.getpid())
        elif name == '!':
            return str(self.last_bg_pid) if self.last_bg_pid else ''
        elif name == '#':
            return str(len(self.positional_params))
        elif name == '0':
            return self.script_name
        elif name == '@':
            return ' '.join(self.positional_params)
        elif name == '*':
            return ' '.join(self.positional_params)
        elif name.isdigit():
            return self.get_positional_param(int(name))
        return ''