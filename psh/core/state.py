"""Shell state management."""
import os
import sys
from typing import List, Dict, Optional, Any
from .scope_enhanced import EnhancedScopeManager
from .variables import VarAttributes
from ..version import __version__

class ShellState:
    """Container for shell state that can be shared across components."""
    
    def __init__(self, args=None, script_name=None, debug_ast=False, 
                 debug_tokens=False, debug_scopes=False, debug_expansion=False, debug_expansion_detail=False,
                 debug_exec=False, debug_exec_fork=False, norc=False, rcfile=None):
        # Environment and variables
        self.env = os.environ.copy()
        
        # Initialize enhanced scope manager for variable scoping with attributes
        self.scope_manager = EnhancedScopeManager()
        
        # For backward compatibility, keep self.variables as a property
        # that delegates to scope_manager
        
        # Default prompt variables (set in global scope)
        self.scope_manager.set_variable('PS1', 'psh$ ')
        self.scope_manager.set_variable('PS2', '> ')
        
        # Shell version variable for compatibility
        self.scope_manager.set_variable('PSH_VERSION', __version__)
        
        # Import environment variables into scope manager with EXPORT attribute
        # This ensures they're properly tracked as exported variables
        for name, value in self.env.items():
            self.scope_manager.set_variable(name, value, attributes=VarAttributes.EXPORT, local=False)
        
        # Ensure PWD is set to current working directory if not already in environment
        if 'PWD' not in self.env:
            current_dir = os.getcwd()
            self.env['PWD'] = current_dir
            self.scope_manager.set_variable('PWD', current_dir, attributes=VarAttributes.EXPORT, local=False)
        
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
            'debug-expansion': debug_expansion,
            'debug-expansion-detail': debug_expansion_detail,
            'debug-exec': debug_exec,
            'debug-exec-fork': debug_exec_fork,
            # Shell options (existing)
            'errexit': False,      # -e: exit on error
            'nounset': False,      # -u: error on undefined variables
            'xtrace': False,       # -x: print commands before execution
            'pipefail': False,     # -o pipefail: pipeline fails if any command fails
            # New POSIX options
            'allexport': False,    # -a: auto-export all variables
            'notify': False,       # -b: async job completion notifications
            'noclobber': False,    # -C: prevent file overwriting with >
            'noglob': False,       # -f: disable pathname expansion
            'hashcmds': False,     # -h: hash command locations
            'monitor': False,      # -m: job control mode (default for interactive)
            'noexec': False,       # -n: read commands but don't execute
            'verbose': False,      # -v: echo input lines as read
            'ignoreeof': False,    # -o ignoreeof: don't exit on EOF
            'nolog': False,        # -o nolog: don't log function definitions
            # Bash compatibility options
            'braceexpand': True,   # -o braceexpand: enable brace expansion (default on)
            'emacs': False,        # -o emacs: emacs key bindings (context-dependent)
            'vi': False,           # -o vi: vi key bindings (off for set -o display)
            'histexpand': True,    # -o histexpand: enable history expansion (default on)
            # Parser configuration options (enhanced features now standard)
            'posix': False,        # -o posix: strict POSIX mode
            'collect_errors': False,  # -o collect_errors: collect multiple parse errors
            'debug-parser': False, # -o debug-parser: enable parser tracing
            'validate-context': False,     # -o validate-context: validate token contexts
            'validate-semantics': False,   # -o validate-semantics: validate semantic types
            'analyze-semantics': False,    # -o analyze-semantics: perform semantic analysis
            'enhanced-error-recovery': True, # -o enhanced-error-recovery: use enhanced error recovery
            'parser-mode': 'balanced', # -o parser-mode: performance mode (performance/balanced/development)
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

        # Terminal capabilities (set by _detect_terminal_capabilities)
        self.terminal_fd: Optional[int] = None
        self.supports_job_control: bool = False
        self.is_terminal: bool = False

        # Special mode for specific eval tests that need output capture
        self._eval_test_mode = False
        
        # I/O streams (for backward compatibility)
        # Store initial values
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._stdin = sys.stdin
        
        # PS4 prompt for xtrace
        self.scope_manager.set_variable('PS4', '+ ')
        
        # Initialize getopts variables
        self.scope_manager.set_variable('OPTIND', '1')
        self.scope_manager.set_variable('OPTERR', '1')
        
        # PSH-specific variables
        self.scope_manager.set_variable('PSH_AST_FORMAT', 'tree')  # Default AST format
        
        # Trap handlers: signal -> command string
        # Maps signal names (e.g., 'INT', 'TERM', 'EXIT') to trap command strings
        self.trap_handlers = {}
        
        # Original signal handlers for restoration
        # Used when traps are removed to restore original behavior
        self._original_signal_handlers = {}

        # Detect terminal capabilities after initialization
        self._detect_terminal_capabilities()
    
    @property
    def eval_test_mode(self) -> bool:
        """Whether we're in special eval test mode for output capture."""
        return self._eval_test_mode
    
    def enable_eval_test_mode(self):
        """Enable special eval test mode for output capture."""
        self._eval_test_mode = True
    
    def disable_eval_test_mode(self):
        """Disable special eval test mode."""
        self._eval_test_mode = False
    
    @property
    def stdout(self):
        """Always return current sys.stdout for test compatibility."""
        # If we have a custom stdout set, use it
        if hasattr(self, '_custom_stdout'):
            return self._custom_stdout
        # Otherwise return current sys.stdout (which pytest might have replaced)
        return sys.stdout
    
    @stdout.setter
    def stdout(self, value):
        """Allow setting a custom stdout."""
        self._custom_stdout = value
    
    @property
    def stderr(self):
        """Always return current sys.stderr for test compatibility."""
        if hasattr(self, '_custom_stderr'):
            return self._custom_stderr
        return sys.stderr
    
    @stderr.setter  
    def stderr(self, value):
        """Allow setting a custom stderr."""
        self._custom_stderr = value
    
    @property
    def stdin(self):
        """Always return current sys.stdin for test compatibility."""
        if hasattr(self, '_custom_stdin'):
            return self._custom_stdin
        return sys.stdin
    
    @stdin.setter
    def stdin(self, value):
        """Allow setting a custom stdin."""
        self._custom_stdin = value
    
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
        # If allexport is enabled, set with export attribute
        if self.options.get('allexport', False):
            self.scope_manager.set_variable(name, value, attributes=VarAttributes.EXPORT, local=False)
            # Also update both internal and system environment
            self.env[name] = value
            os.environ[name] = value
            # Sync all exports to environment
            self.scope_manager.sync_exports_to_environment(self.env)
        else:
            # Use scope manager (will set in global scope if not in function,
            # or global scope if in function per bash behavior)
            self.scope_manager.set_variable(name, value, local=False)
    
    def export_variable(self, name: str, value: str):
        """Export a variable to the environment."""
        # Set variable with EXPORT attribute in global scope
        self.scope_manager.set_variable(name, value, attributes=VarAttributes.EXPORT, local=False)
        # Also update both internal and system environment
        self.env[name] = value
        os.environ[name] = value
        # Sync all exports to environment
        self.scope_manager.sync_exports_to_environment(self.env)
    
    def get_positional_param(self, index: int) -> str:
        """Get positional parameter by index (1-based)."""
        if 1 <= index <= len(self.positional_params):
            return self.positional_params[index - 1]
        return ''
    
    def set_positional_params(self, params):
        """Set positional parameters ($1, $2, etc.)."""
        self.positional_params = params.copy() if params else []
    
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
        elif name == '-':
            return self.get_option_string()
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
    
    def get_option_string(self) -> str:
        """Get string representation of set options for $- special variable."""
        opts = []
        # Single-letter options in alphabetical order
        if self.options.get('allexport'): opts.append('a')
        if self.options.get('notify'): opts.append('b')
        if self.options.get('noclobber'): opts.append('C')
        if self.options.get('errexit'): opts.append('e')
        if self.options.get('noglob'): opts.append('f')
        if self.options.get('hashcmds'): opts.append('h')
        if self.options.get('monitor'): opts.append('m')
        if self.options.get('noexec'): opts.append('n')
        if self.options.get('nounset'): opts.append('u')
        if self.options.get('verbose'): opts.append('v')
        if self.options.get('xtrace'): opts.append('x')
        return ''.join(opts)

    def _detect_terminal_capabilities(self):
        """Detect if we have a controlling terminal with job control support.

        This determines whether we can use tcsetpgrp(), tcgetpgrp(), etc.
        Results are cached in state for efficient checks.
        """
        try:
            # Check if stdin is a TTY
            if os.isatty(0):
                self.is_terminal = True
                self.terminal_fd = 0

                # Check if we can actually do job control
                # Some TTY environments don't support it (e.g., emacs shell-mode)
                try:
                    current_pgid = os.tcgetpgrp(0)
                    self.supports_job_control = True

                    if self.options.get('debug-exec'):
                        print(f"DEBUG: Terminal detected, job control available (pgid={current_pgid})",
                              file=sys.stderr)
                except OSError as e:
                    # TTY but no job control available
                    self.supports_job_control = False
                    if self.options.get('debug-exec'):
                        print(f"DEBUG: Terminal detected but job control unavailable: {e}",
                              file=sys.stderr)
            else:
                self.is_terminal = False
                self.supports_job_control = False
                if self.options.get('debug-exec'):
                    print(f"DEBUG: Not running on a terminal (stdin is not a TTY)",
                          file=sys.stderr)
        except (OSError, AttributeError):
            # Platform doesn't support TTY detection
            self.is_terminal = False
            self.supports_job_control = False
            if self.options.get('debug-exec'):
                print(f"DEBUG: Platform doesn't support TTY detection",
                      file=sys.stderr)