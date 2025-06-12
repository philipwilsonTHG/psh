"""Shell state management."""
import os
import sys
from typing import List, Dict, Optional, Any
from .scope_enhanced import EnhancedScopeManager
from .variables import VarAttributes

class ShellState:
    """Container for shell state that can be shared across components."""
    
    def __init__(self, args=None, script_name=None, debug_ast=False, 
                 debug_tokens=False, debug_scopes=False, norc=False, rcfile=None):
        # Environment and variables
        self.env = os.environ.copy()
        
        # Initialize enhanced scope manager for variable scoping with attributes
        self.scope_manager = EnhancedScopeManager()
        
        # For backward compatibility, keep self.variables as a property
        # that delegates to scope_manager
        
        # Default prompt variables (set in global scope)
        self.scope_manager.set_variable('PS1', 'psh$ ')
        self.scope_manager.set_variable('PS2', '> ')
        
        # Import environment variables into scope manager with EXPORT attribute
        # This ensures they're properly tracked as exported variables
        for name, value in self.env.items():
            self.scope_manager.set_variable(name, value, attributes=VarAttributes.EXPORT, local=False)
        
        # Positional parameters and script info
        self.positional_params = args if args else []
        self.script_name = script_name or "psh"
        self.is_script_mode = script_name is not None and script_name != "psh"
        
        # Centralized shell options dictionary
        self.options = {
            # Debug options (existing)
            'debug-ast': debug_ast,
            'debug-tokens': debug_tokens,
            'debug-scopes': debug_scopes,
            # New shell options (to be implemented)
            'errexit': False,      # -e: exit on error
            'nounset': False,      # -u: error on undefined variables
            'xtrace': False,       # -x: print commands before execution
            'pipefail': False,     # -o pipefail: pipeline fails if any command fails
        }
        
        # Enable debug mode on scope manager if debug-scopes is set
        if self.options['debug-scopes']:
            self.scope_manager.enable_debug(True)
        
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
        
        # PS4 prompt for xtrace
        self.scope_manager.set_variable('PS4', '+ ')
    
    # Backward-compatible properties for debug options
    @property
    def debug_ast(self):
        """Backward compatibility for debug_ast attribute."""
        return self.options.get('debug-ast', False)
    
    @debug_ast.setter
    def debug_ast(self, value):
        """Backward compatibility for debug_ast attribute."""
        self.options['debug-ast'] = value
    
    @property
    def debug_tokens(self):
        """Backward compatibility for debug_tokens attribute."""
        return self.options.get('debug-tokens', False)
    
    @debug_tokens.setter
    def debug_tokens(self, value):
        """Backward compatibility for debug_tokens attribute."""
        self.options['debug-tokens'] = value
    
    @property
    def debug_scopes(self):
        """Backward compatibility for debug_scopes attribute."""
        return self.options.get('debug-scopes', False)
    
    @debug_scopes.setter
    def debug_scopes(self, value):
        """Backward compatibility for debug_scopes attribute."""
        self.options['debug-scopes'] = value
        # Also update scope manager when this is set
        if hasattr(self, 'scope_manager'):
            self.scope_manager.enable_debug(value)
    
    @property
    def variables(self) -> Dict[str, str]:
        """Backward compatibility: return all visible variables as dict."""
        return self.scope_manager.get_all_variables()
    
    def get_variable(self, name: str, default: str = '') -> str:
        """Get variable value, checking shell variables first, then environment."""
        # Check scope manager first (includes locals and globals)
        result = self.scope_manager.get_variable(name)
        if result is not None:
            return result
        # Fall back to environment
        return self.env.get(name, default)
    
    def set_variable(self, name: str, value: str):
        """Set a shell variable."""
        # Use scope manager (will set in global scope if not in function,
        # or global scope if in function per bash behavior)
        self.scope_manager.set_variable(name, value, local=False)
    
    def export_variable(self, name: str, value: str):
        """Export a variable to the environment."""
        # Set variable with EXPORT attribute in global scope
        self.scope_manager.set_variable(name, value, attributes=VarAttributes.EXPORT, local=False)
        # Also update environment
        self.env[name] = value
        # Sync all exports to environment
        self.scope_manager.sync_exports_to_environment(self.env)
    
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
    
    # Backward-compatible properties for debug flags
    @property
    def debug_ast(self) -> bool:
        """Get debug-ast option."""
        return self.options.get('debug-ast', False)
    
    @debug_ast.setter
    def debug_ast(self, value: bool):
        """Set debug-ast option."""
        self.options['debug-ast'] = value
    
    @property
    def debug_tokens(self) -> bool:
        """Get debug-tokens option."""
        return self.options.get('debug-tokens', False)
    
    @debug_tokens.setter
    def debug_tokens(self, value: bool):
        """Set debug-tokens option."""
        self.options['debug-tokens'] = value
    
    @property
    def debug_scopes(self) -> bool:
        """Get debug-scopes option."""
        return self.options.get('debug-scopes', False)
    
    @debug_scopes.setter
    def debug_scopes(self, value: bool):
        """Set debug-scopes option."""
        self.options['debug-scopes'] = value
        # Also update scope manager
        if hasattr(self, 'scope_manager'):
            self.scope_manager.enable_debug(value)