import os
import sys
import subprocess
import readline
import signal
import glob
import pwd
import stat
import fnmatch
import fcntl
from typing import List, Tuple
from .tokenizer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, Pipeline, CommandList, AndOrList, Redirect, TopLevel, FunctionDef, IfStatement, WhileStatement, ForStatement, BreakStatement, ContinueStatement, CaseStatement, CaseItem, CasePattern, ProcessSubstitution
from .line_editor import LineEditor
from .version import get_version_info
from .aliases import AliasManager
from .functions import FunctionManager
from .job_control import JobManager, JobState
from .builtins import registry as builtin_registry
from .builtins.function_support import FunctionReturn

class LoopBreak(Exception):
    """Exception used to implement break statement."""
    pass

class LoopContinue(Exception):
    """Exception used to implement continue statement."""
    pass

class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, debug_tokens=False):
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported to environment)
        self.positional_params = args if args else []  # $1, $2, etc.
        self.script_name = script_name or "psh"  # $0 value
        self.is_script_mode = script_name is not None and script_name != "psh"
        self.debug_ast = debug_ast  # Whether to print AST before execution
        self.debug_tokens = debug_tokens  # Whether to print tokens before parsing
        
        # For backward compatibility with redirections
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.stdin = sys.stdin
        
        # Use new builtin registry for migrated builtins
        self.builtin_registry = builtin_registry
        
        # All builtins are now handled by the registry
        self.builtins = {}
        # History setup
        self.history = []
        self.history_file = os.path.expanduser("~/.psh_history")
        self.max_history_size = 1000
        self._load_history()
        # Command history navigation
        self.history_index = -1
        self.current_line = ""
        
        self.last_exit_code = 0
        self.last_bg_pid = None
        self.foreground_pgid = None
        
        # Editor configuration
        self.edit_mode = 'emacs'  # Default to emacs mode
        
        # Alias management
        self.alias_manager = AliasManager()
        
        # Function management
        self.function_manager = FunctionManager()
        self.function_stack = []  # Track function call stack
        
        # Job control
        self.job_manager = JobManager()
        
        # Ensure shell is in its own process group for job control
        shell_pgid = os.getpid()
        try:
            os.setpgid(0, shell_pgid)
            # Make shell the foreground process group
            os.tcsetpgrp(0, shell_pgid)
        except OSError:
            # Not a terminal or already set
            pass
        
        # Set up signal handlers based on mode
        if self.is_script_mode:
            # Script mode: simpler signal handling
            signal.signal(signal.SIGINT, signal.SIG_DFL)  # Default SIGINT behavior
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)  # Default SIGTSTP behavior
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Still ignore terminal output stops
            signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Still ignore terminal input stops
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)  # Default child handling
        else:
            # Interactive mode: full signal handling
            signal.signal(signal.SIGINT, self._handle_sigint)
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Shell ignores SIGTSTP
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Ignore terminal output stops
            signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Ignore terminal input stops
            signal.signal(signal.SIGCHLD, self._handle_sigchld)  # Track child status
    
    def _expand_string_variables(self, text: str) -> str:
        """Expand variables and arithmetic in a string (for here strings and quoted strings)"""
        result = []
        i = 0
        while i < len(text):
            if text[i] == '$' and i + 1 < len(text):
                if text[i + 1] == '(' and i + 2 < len(text) and text[i + 2] == '(':
                    # $((...)) arithmetic expansion
                    # Find the matching ))
                    paren_count = 0
                    j = i + 3  # Start after $((
                    while j < len(text):
                        if text[j] == '(':
                            paren_count += 1
                        elif text[j] == ')':
                            if paren_count == 0 and j + 1 < len(text) and text[j + 1] == ')':
                                # Found the closing ))
                                arith_expr = text[i:j + 2]  # Include $((...)
                                result.append(str(self._execute_arithmetic_expansion(arith_expr)))
                                i = j + 2
                                break
                            else:
                                paren_count -= 1
                        j += 1
                    else:
                        # No matching )) found, treat as literal
                        result.append(text[i])
                        i += 1
                    continue
                elif text[i + 1] == '{':
                    # ${var} syntax
                    end = text.find('}', i + 2)
                    if end != -1:
                        var_name = text[i + 2:end]
                        result.append(self._expand_variable('$' + var_name))
                        i = end + 1
                        continue
                else:
                    # Check for special variables first
                    if text[i + 1] in '?$!#@*0123456789':
                        var_name = text[i + 1]
                        result.append(self._expand_variable('$' + var_name))
                        i += 2
                        continue
                    # $var syntax
                    j = i + 1
                    while j < len(text) and (text[j].isalnum() or text[j] == '_'):
                        j += 1
                    if j > i + 1:
                        var_name = text[i + 1:j]
                        result.append(self._expand_variable('$' + var_name))
                        i = j
                        continue
            result.append(text[i])
            i += 1
        return ''.join(result)
    
    def _expand_variable(self, var_expr: str) -> str:
        """Expand a variable expression starting with $"""
        if not var_expr.startswith('$'):
            return var_expr
        
        var_expr = var_expr[1:]  # Remove $
        
        # Handle ${var} syntax
        if var_expr.startswith('{') and var_expr.endswith('}'):
            var_content = var_expr[1:-1]
            
            # Handle ${var:-default} syntax
            if ':-' in var_content:
                var_name, default = var_content.split(':-', 1)
                value = self.variables.get(var_name, self.env.get(var_name, ''))
                return value if value else default
            else:
                var_name = var_content
        else:
            var_name = var_expr
        
        # Special variables
        if var_name == '?':
            return str(self.last_exit_code)
        elif var_name == '$':
            return str(os.getpid())
        elif var_name == '!':
            return str(self.last_bg_pid) if self.last_bg_pid else ''
        elif var_name == '#':
            return str(len(self.positional_params))
        elif var_name == '0':
            return self.script_name  # Shell or script name
        elif var_name == '@':
            # When in a string context (like echo "$@"), don't add quotes
            # The quotes are only added when $@ is unquoted
            return ' '.join(self.positional_params)
        elif var_name == '*':
            # Expand to single word
            return ' '.join(self.positional_params)
        elif var_name.isdigit():
            # Positional parameter
            index = int(var_name) - 1
            if 0 <= index < len(self.positional_params):
                return self.positional_params[index]
            return ''
        
        # Regular variables - check shell variables first, then environment
        return self.variables.get(var_name, self.env.get(var_name, ''))
    
    def _expand_tilde(self, path: str) -> str:
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
    
    def _execute_command_substitution(self, cmd_sub: str) -> str:
        """Execute command substitution and return output"""
        # Remove $(...) or `...`
        if cmd_sub.startswith('$(') and cmd_sub.endswith(')'):
            command = cmd_sub[2:-1]
        elif cmd_sub.startswith('`') and cmd_sub.endswith('`'):
            command = cmd_sub[1:-1]
        else:
            return ''
        
        # Use subprocess to capture output from both builtins and external commands
        import subprocess
        import tempfile
        
        # Create a temporary file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmpfile:
            temp_output = tmpfile.name
        
        try:
            # Create a temporary shell to execute the command with output redirected
            temp_shell = Shell(debug_ast=self.debug_ast, debug_tokens=self.debug_tokens)
            temp_shell.env = self.env.copy()
            temp_shell.variables = self.variables.copy()
            
            # Execute the command with output redirected to temp file
            temp_shell.run_command(f"{command} > {temp_output}", add_to_history=False)
            
            # Read the captured output
            with open(temp_output, 'r') as f:
                output = f.read()
            
            # Strip trailing newline (bash behavior)
            if output.endswith('\n'):
                output = output[:-1]
            
            return output
        finally:
            # Clean up temp file
            if os.path.exists(temp_output):
                os.unlink(temp_output)
    
    def _execute_arithmetic_expansion(self, expr: str) -> int:
        """Execute arithmetic expansion and return result"""
        # Remove $(( and ))
        if expr.startswith('$((') and expr.endswith('))'):
            arith_expr = expr[3:-2]
        else:
            return 0
        
        from .arithmetic import evaluate_arithmetic, ArithmeticError
        
        try:
            result = evaluate_arithmetic(arith_expr, self)
            return result
        except ArithmeticError as e:
            print(f"psh: arithmetic error: {e}", file=sys.stderr)
            return 0
    
    def _expand_arguments(self, command: Command) -> list:
        """Expand variables, command substitutions, tildes, and globs in command arguments"""
        args = []
        
        # Check if we have process substitutions
        has_proc_sub = any(command.arg_types[i] in ('PROCESS_SUB_IN', 'PROCESS_SUB_OUT') 
                          for i in range(len(command.arg_types)))
        
        if has_proc_sub:
            # Set up process substitutions first
            fds, substituted_args, child_pids = self._setup_process_substitutions(command)
            # Store for cleanup
            self._process_sub_fds = fds
            self._process_sub_pids = child_pids
            # Update command args with substituted paths
            command.args = substituted_args
            # Update arg_types to treat substituted paths as words
            command.arg_types = ['WORD'] * len(substituted_args)
        
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            
            if arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion
                expanded = self._expand_variable(arg)
                args.append(expanded)
            elif arg_type in ('COMMAND_SUB', 'COMMAND_SUB_BACKTICK'):
                # Command substitution
                output = self._execute_command_substitution(arg)
                # POSIX: apply word splitting to unquoted command substitution
                if output:
                    # Split on whitespace
                    words = output.split()
                    args.extend(words)
                # If output is empty, don't add anything
            elif arg_type == 'ARITH_EXPANSION':
                # Arithmetic expansion
                result = self._execute_arithmetic_expansion(arg)
                args.append(str(result))
            else:
                # Check if this is a STRING that might contain variables
                if arg_type == 'STRING' and '$' in arg:
                    # Special handling for "$@"
                    if arg == '$@':
                        # "$@" expands to multiple arguments, each properly quoted
                        args.extend(self.positional_params)
                        continue
                    else:
                        # Expand variables within the string
                        arg = self._expand_string_variables(arg)
                
                # Tilde expansion (only for unquoted words)
                if arg.startswith('~') and arg_type == 'WORD':
                    arg = self._expand_tilde(arg)
                
                # Check if the argument contains glob characters and wasn't quoted
                if any(c in arg for c in ['*', '?', '[']) and arg_type != 'STRING':
                    # Perform glob expansion
                    matches = glob.glob(arg)
                    if matches:
                        # Sort matches for consistent output
                        args.extend(sorted(matches))
                    else:
                        # No matches, use literal argument (bash behavior)
                        args.append(arg)
                else:
                    args.append(arg)
        return args
    
    def _handle_variable_assignment(self, args: list) -> int:
        """Handle variable assignment if present. Returns 0 if handled, -1 if not an assignment"""
        if not args or '=' not in args[0] or args[0].startswith('='):
            return -1
        
        # Check if all leading arguments are variable assignments
        assignments = []
        command_start = 0
        
        for i, arg in enumerate(args):
            if '=' in arg and not arg.startswith('='):
                # This looks like a variable assignment
                assignments.append(arg)
                command_start = i + 1
            else:
                # Not an assignment, this is where the command starts
                break
        
        if not assignments:
            return -1
        
        if command_start >= len(args):
            # Only assignments, no command
            for assignment in assignments:
                var_name, var_value = assignment.split('=', 1)
                # Expand variables in the value first
                if '$' in var_value:
                    var_value = self._expand_string_variables(var_value)
                
                # Expand arithmetic expansion in the value
                if '$((' in var_value and '))' in var_value:
                    # Find and expand all arithmetic expansions
                    import re
                    def expand_arith(match):
                        return str(self._execute_arithmetic_expansion(match.group(0)))
                    var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
                
                # Expand tilde in the value
                if var_value.startswith('~'):
                    var_value = self._expand_tilde(var_value)
                self.variables[var_name] = var_value
            return 0
        else:
            # Assignments followed by command - not handled here
            return -1
    
    def _setup_builtin_redirections(self, command: Command):
        """Set up redirections for built-in commands. Returns tuple of backup objects."""
        stdout_backup = None
        stderr_backup = None
        stdin_backup = None
        
        for redirect in command.redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self._expand_tilde(target)
            
            # Handle process substitution as redirect target
            if target and target.startswith(('<(', '>(')) and target.endswith(')'):
                # This is a process substitution used as a redirect target
                # Set up the process substitution and get the fd path
                if target.startswith('<('):
                    direction = 'in'
                    cmd_str = target[2:-1]
                else:
                    direction = 'out' 
                    cmd_str = target[2:-1]
                
                # Create pipe
                if direction == 'in':
                    read_fd, write_fd = os.pipe()
                    parent_fd = read_fd
                    child_fd = write_fd
                    child_stdout = child_fd
                    child_stdin = 0
                else:
                    read_fd, write_fd = os.pipe()
                    parent_fd = write_fd
                    child_fd = read_fd
                    child_stdout = 1
                    child_stdin = child_fd
                
                # Clear close-on-exec flag
                flags = fcntl.fcntl(parent_fd, fcntl.F_GETFD)
                fcntl.fcntl(parent_fd, fcntl.F_SETFD, flags & ~fcntl.FD_CLOEXEC)
                
                # Fork child
                pid = os.fork()
                if pid == 0:  # Child
                    os.close(parent_fd)
                    if direction == 'in':
                        os.dup2(child_stdout, 1)
                    else:
                        os.dup2(child_stdin, 0)
                    os.close(child_fd)
                    
                    try:
                        tokens = tokenize(cmd_str)
                        ast = parse(tokens)
                        temp_shell = Shell()
                        temp_shell.env = self.env.copy()
                        temp_shell.variables = self.variables.copy()
                        exit_code = temp_shell.execute_command_list(ast)
                        os._exit(exit_code)
                    except Exception as e:
                        print(f"psh: process substitution error: {e}", file=sys.stderr)
                        os._exit(1)
                else:  # Parent
                    os.close(child_fd)
                    # Store for cleanup
                    if not hasattr(self, '_builtin_proc_sub_fds'):
                        self._builtin_proc_sub_fds = []
                    if not hasattr(self, '_builtin_proc_sub_pids'):
                        self._builtin_proc_sub_pids = []
                    self._builtin_proc_sub_fds.append(parent_fd)
                    self._builtin_proc_sub_pids.append(pid)
                    # Use the fd path as target
                    target = f"/dev/fd/{parent_fd}"
            
            if redirect.type == '<':
                stdin_backup = sys.stdin
                sys.stdin = open(target, 'r')
            elif redirect.type in ('<<', '<<-'):
                stdin_backup = sys.stdin
                # Create a StringIO object from heredoc content
                import io
                sys.stdin = io.StringIO(redirect.heredoc_content or '')
            elif redirect.type == '<<<':
                stdin_backup = sys.stdin
                # For here string, add a newline to the content
                import io
                content = redirect.target + '\n'
                sys.stdin = io.StringIO(content)
            elif redirect.type == '>' and redirect.fd == 2:
                stderr_backup = sys.stderr
                sys.stderr = open(target, 'w')
            elif redirect.type == '>>' and redirect.fd == 2:
                stderr_backup = sys.stderr
                sys.stderr = open(target, 'a')
            elif redirect.type == '>' and (redirect.fd is None or redirect.fd == 1):
                stdout_backup = sys.stdout
                sys.stdout = open(target, 'w')
            elif redirect.type == '>>' and (redirect.fd is None or redirect.fd == 1):
                stdout_backup = sys.stdout
                sys.stdout = open(target, 'a')
            elif redirect.type == '>&':
                # Handle fd duplication like 2>&1
                if redirect.fd == 2 and redirect.dup_fd == 1:
                    stderr_backup = sys.stderr
                    sys.stderr = sys.stdout
        
        return stdin_backup, stdout_backup, stderr_backup
    
    def _restore_builtin_redirections(self, stdin_backup, stdout_backup, stderr_backup):
        """Restore original stdin/stdout/stderr after built-in execution"""
        if stdin_backup:
            if hasattr(sys.stdin, 'close') and sys.stdin != stdin_backup:
                sys.stdin.close()
            sys.stdin = stdin_backup
        if stdout_backup:
            if hasattr(sys.stdout, 'close') and sys.stdout != stdout_backup:
                sys.stdout.close()
            sys.stdout = stdout_backup
        if stderr_backup:
            if hasattr(sys.stderr, 'close') and sys.stderr != stderr_backup:
                sys.stderr.close()
            sys.stderr = stderr_backup
        
        # Clean up process substitution fds and wait for children
        if hasattr(self, '_builtin_proc_sub_fds'):
            for fd in self._builtin_proc_sub_fds:
                try:
                    os.close(fd)
                except:
                    pass
            del self._builtin_proc_sub_fds
        
        if hasattr(self, '_builtin_proc_sub_pids'):
            for pid in self._builtin_proc_sub_pids:
                try:
                    os.waitpid(pid, 0)
                except:
                    pass
            del self._builtin_proc_sub_pids
    
    def _execute_builtin(self, args: list, command: Command) -> int:
        """Execute a built-in command with proper redirection handling"""
        # Check new registry first
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            stdin_backup, stdout_backup, stderr_backup = self._setup_builtin_redirections(command)
            try:
                # Update sys streams for builtins that might use them
                self.stdout = sys.stdout
                self.stderr = sys.stderr
                self.stdin = sys.stdin
                return builtin.execute(args, self)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
        
        # Fall back to old builtins
        if args[0] in self.builtins:
            stdin_backup, stdout_backup, stderr_backup = self._setup_builtin_redirections(command)
            try:
                return self.builtins[args[0]](args)
            except FunctionReturn:
                # Re-raise FunctionReturn to propagate it up
                raise
            finally:
                self._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
        
        # Not a builtin
        return -1
    
    def _execute_external(self, args: list, command: Command) -> int:
        """Execute an external command with proper redirection and process handling"""
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        pid = os.fork()
        
        if pid == 0:  # Child process
            # Create new process group
            os.setpgid(0, 0)
            
            # Reset signal handlers to default
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)
            signal.signal(signal.SIGTTOU, signal.SIG_DFL)
            signal.signal(signal.SIGTTIN, signal.SIG_DFL)
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            
            # Set up redirections
            self._setup_child_redirections(command)
            
            # Execute the command
            try:
                os.execvpe(args[0], args, self.env)
            except FileNotFoundError:
                print(f"{args[0]}: command not found", file=sys.stderr)
                os._exit(127)
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                os._exit(1)
        
        else:  # Parent process
            # Set child's process group
            try:
                os.setpgid(pid, pid)
            except:
                pass  # Race condition - child may have already done it
            
            # Create job for tracking
            job = self.job_manager.create_job(pid, ' '.join(args))
            job.add_process(pid, args[0])
            
            if command.background:
                # Background job
                job.foreground = False
                print(f"[{job.job_id}] {pid}")
                self.last_bg_pid = pid
                return 0
            else:
                # Foreground job - give it terminal control
                job.foreground = True
                self.job_manager.set_foreground_job(job)
                
                if original_pgid is not None:
                    self.foreground_pgid = pid
                    try:
                        os.tcsetpgrp(0, pid)
                    except:
                        pass
                
                # Wait for the job
                exit_status = self.job_manager.wait_for_job(job)
                
                # Restore terminal control
                if original_pgid is not None:
                    self.foreground_pgid = None
                    self.job_manager.set_foreground_job(None)
                    try:
                        os.tcsetpgrp(0, original_pgid)
                    except:
                        pass
                
                # Remove completed job
                if job.state == JobState.DONE:
                    self.job_manager.remove_job(job.job_id)
                
                return exit_status
    
    def execute_command(self, command: Command):
        """Execute a single command"""
        # Preprocess here strings to expand variables
        for redirect in command.redirects:
            if redirect.type == '<<<':
                # Expand variables in here string content
                redirect.target = self._expand_string_variables(redirect.target)
        
        # Expand arguments (variables, command substitutions, globs)
        args = self._expand_arguments(command)
        
        if not args:
            return 0
        
        # Separate variable assignments from command
        assignments = []
        command_args = []
        in_command = False
        
        for arg in args:
            if not in_command and '=' in arg and not arg.startswith('='):
                # This is a variable assignment
                assignments.append(arg)
            else:
                # This is part of the command
                in_command = True
                command_args.append(arg)
        
        # If only assignments, handle them
        if not command_args:
            for assignment in assignments:
                var_name, var_value = assignment.split('=', 1)
                # Expand variables in the value first
                if '$' in var_value:
                    var_value = self._expand_string_variables(var_value)
                
                # Expand arithmetic expansion in the value
                if '$((' in var_value and '))' in var_value:
                    # Find and expand all arithmetic expansions
                    import re
                    def expand_arith(match):
                        return str(self._execute_arithmetic_expansion(match.group(0)))
                    var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
                
                # Expand tilde in the value
                if var_value.startswith('~'):
                    var_value = self._expand_tilde(var_value)
                self.variables[var_name] = var_value
            return 0
        
        # Save current values of variables that will be assigned
        saved_vars = {}
        for assignment in assignments:
            var_name = assignment.split('=', 1)[0]
            if var_name in self.variables:
                saved_vars[var_name] = self.variables[var_name]
            else:
                saved_vars[var_name] = None
        
        # Apply temporary assignments
        temp_env_vars = {}
        for assignment in assignments:
            var_name, var_value = assignment.split('=', 1)
            # Expand variables in the value
            if '$' in var_value:
                var_value = self._expand_string_variables(var_value)
            # Expand arithmetic expansion
            if '$((' in var_value and '))' in var_value:
                import re
                def expand_arith(match):
                    return str(self._execute_arithmetic_expansion(match.group(0)))
                var_value = re.sub(r'\$\(\([^)]+\)\)', expand_arith, var_value)
            # Expand tilde
            if var_value.startswith('~'):
                var_value = self._expand_tilde(var_value)
            self.variables[var_name] = var_value
            # Also temporarily set in environment for external commands
            temp_env_vars[var_name] = var_value
        
        # Execute the command with temporary variables
        try:
            # Check for function call BEFORE builtin check
            func = self.function_manager.get_function(command_args[0])
            if func:
                result = self._execute_function(func, command_args, command)
            elif self.builtin_registry.has(command_args[0]) or command_args[0] in self.builtins:
                # Execute builtin with command_args instead of args
                result = self._execute_builtin(command_args, command)
            else:
                # External command
                result = self._execute_external(command_args, command)
        finally:
            # Clean up process substitutions
            self._cleanup_process_substitutions()
            
            # Restore original variable values
            for var_name, original_value in saved_vars.items():
                if original_value is None:
                    self.variables.pop(var_name, None)
                else:
                    self.variables[var_name] = original_value
        
        return result
    
    def _setup_child_process(self, pgid, command_index, num_commands, pipes):
        """Set up a child process in a pipeline"""
        # Set process group - first child becomes group leader
        if pgid is None:
            pgid = os.getpid()
            os.setpgid(0, pgid)
        else:
            os.setpgid(0, pgid)
        
        # Reset signal handlers to default
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
        
        # Set up pipes
        if command_index > 0:  # Not first command - read from previous pipe
            os.dup2(pipes[command_index-1][0], 0)  # stdin = pipe_read
            
        if command_index < num_commands - 1:  # Not last command - write to next pipe
            os.dup2(pipes[command_index][1], 1)  # stdout = pipe_write
        
        # Close all pipe file descriptors
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        return pgid
    
    def _wait_for_pipeline(self, pids):
        """Wait for all processes in pipeline and return exit status of last"""
        last_status = 0
        for i, pid in enumerate(pids):
            try:
                _, status = os.waitpid(pid, 0)
                if i == len(pids) - 1:  # Last command
                    if os.WIFEXITED(status):
                        last_status = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        last_status = 128 + os.WTERMSIG(status)
                    else:
                        last_status = 1
            except OSError:
                # Child might have been killed by signal
                last_status = 1
        return last_status
    
    def _build_pipeline_string(self, pipeline: Pipeline) -> str:
        """Build a string representation of the pipeline for job display."""
        parts = []
        for command in pipeline.commands:
            cmd_str = ' '.join(command.args) if command.args else ''
            if command.background:
                cmd_str += ' &'
            parts.append(cmd_str)
        return ' | '.join(parts)
    
    def execute_pipeline(self, pipeline: Pipeline):
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            try:
                return self.execute_command(pipeline.commands[0])
            except FunctionReturn:
                # Propagate up
                raise
        
        # Build command string for job tracking
        command_string = self._build_pipeline_string(pipeline)
        
        # Execute pipeline using fork and pipe
        num_commands = len(pipeline.commands)
        pipes = []
        pids = []
        pgid = None
        job = None
        
        # Save current terminal foreground process group
        try:
            original_pgid = os.tcgetpgrp(0)
        except:
            original_pgid = None
        
        # Create pipes for inter-process communication
        for i in range(num_commands - 1):
            pipe_read, pipe_write = os.pipe()
            pipes.append((pipe_read, pipe_write))
        
        # Fork and execute each command
        for i, command in enumerate(pipeline.commands):
            pid = os.fork()
            
            if pid == 0:  # Child process
                pgid = self._setup_child_process(pgid, i, num_commands, pipes)
                exit_code = self._execute_in_child(command)
                os._exit(exit_code)
            
            else:  # Parent process
                if pgid is None:
                    pgid = pid
                    os.setpgid(pid, pgid)
                else:
                    try:
                        os.setpgid(pid, pgid)
                    except:
                        pass  # Race condition - child may have already done it
                pids.append(pid)
        
        # Create job entry for tracking
        job = self.job_manager.create_job(pgid, command_string)
        for i, pid in enumerate(pids):
            cmd_str = ' '.join(pipeline.commands[i].args) if pipeline.commands[i].args else ''
            job.add_process(pid, cmd_str)
        
        # Give terminal control to the pipeline
        is_background = pipeline.commands[-1].background
        
        if not is_background:
            # Foreground job
            self.foreground_pgid = pgid
            job.foreground = True
            self.job_manager.set_foreground_job(job)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, pgid)
                except:
                    pass
        else:
            # Background job
            job.foreground = False
            print(f"[{job.job_id}] {job.pgid}")
        
        # Parent: Close all pipes
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        # Wait for all children and get exit status
        if not is_background:
            # Foreground job - wait for it
            last_status = self.job_manager.wait_for_job(job)
            
            # Restore terminal control
            self.foreground_pgid = None
            self.job_manager.set_foreground_job(None)
            if original_pgid is not None:
                try:
                    os.tcsetpgrp(0, original_pgid)
                except:
                    pass
            
            # Remove completed job
            if job.state == JobState.DONE:
                self.job_manager.remove_job(job.job_id)
        else:
            # Background job - don't wait
            last_status = 0
            self.last_bg_pid = pids[-1] if pids else None
        
        return last_status
    
    def execute_and_or_list(self, and_or_list: AndOrList):
        """Execute pipelines with && and || operators, implementing short-circuit evaluation"""
        if not and_or_list.pipelines:
            return 0
        
        try:
            # Execute first pipeline
            exit_code = self.execute_pipeline(and_or_list.pipelines[0])
            self.last_exit_code = exit_code
            
            # Process remaining pipelines with operators
            for i, operator in enumerate(and_or_list.operators):
                if operator == '&&':
                    # AND: execute next pipeline only if previous succeeded (exit code 0)
                    if exit_code != 0:
                        continue  # Skip this pipeline
                elif operator == '||':
                    # OR: execute next pipeline only if previous failed (non-zero exit code)
                    if exit_code == 0:
                        continue  # Skip this pipeline
                
                # Execute the next pipeline
                exit_code = self.execute_pipeline(and_or_list.pipelines[i + 1])
                self.last_exit_code = exit_code
            
            return exit_code
        except FunctionReturn:
            # Propagate up
            raise
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        try:
            for item in command_list.statements:
                if isinstance(item, BreakStatement):
                    exit_code = self.execute_break_statement(item)
                elif isinstance(item, ContinueStatement):
                    exit_code = self.execute_continue_statement(item)
                elif isinstance(item, IfStatement):
                    exit_code = self.execute_if_statement(item)
                elif isinstance(item, WhileStatement):
                    exit_code = self.execute_while_statement(item)
                elif isinstance(item, ForStatement):
                    exit_code = self.execute_for_statement(item)
                elif isinstance(item, CaseStatement):
                    exit_code = self.execute_case_statement(item)
                elif isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        exit_code = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        exit_code = 1
                elif isinstance(item, AndOrList):
                    # Handle regular and_or_list
                    exit_code = self.execute_and_or_list(item)
                else:
                    print(f"psh: unknown statement type: {type(item).__name__}", file=sys.stderr)
                    exit_code = 1
                self.last_exit_code = exit_code
        except FunctionReturn:
            # Only catch FunctionReturn if we're in a function
            if self.function_stack:
                raise
            # Otherwise it's an error
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        except (LoopBreak, LoopContinue) as e:
            # Re-raise to be handled by enclosing loop
            raise
        return exit_code
    
    def execute_toplevel(self, toplevel: TopLevel):
        """Execute a top-level script/input containing functions and commands."""
        last_exit = 0
        
        try:
            for item in toplevel.items:
                if isinstance(item, FunctionDef):
                    # Register the function
                    try:
                        self.function_manager.define_function(item.name, item.body)
                        last_exit = 0
                    except ValueError as e:
                        print(f"psh: {e}", file=sys.stderr)
                        last_exit = 1
                elif isinstance(item, CommandList):
                    # Collect here documents if any
                    self._collect_heredocs(item)
                    # Execute commands
                    last_exit = self.execute_command_list(item)
                elif isinstance(item, IfStatement):
                    # Collect here documents
                    self._collect_heredocs(item)
                    # Execute if statement
                    last_exit = self.execute_if_statement(item)
                elif isinstance(item, WhileStatement):
                    # Collect here documents
                    self._collect_heredocs(item)
                    # Execute while statement
                    last_exit = self.execute_while_statement(item)
                elif isinstance(item, ForStatement):
                    # Collect here documents
                    self._collect_heredocs(item)
                    # Execute for statement
                    last_exit = self.execute_for_statement(item)
                elif isinstance(item, CaseStatement):
                    # Collect here documents
                    self._collect_heredocs(item)
                    # Execute case statement
                    last_exit = self.execute_case_statement(item)
                elif isinstance(item, BreakStatement):
                    # Execute break statement (this will raise LoopBreak)
                    last_exit = self.execute_break_statement(item)
                elif isinstance(item, ContinueStatement):
                    # Execute continue statement (this will raise LoopContinue)  
                    last_exit = self.execute_continue_statement(item)
        except (LoopBreak, LoopContinue) as e:
            # Break/continue outside of loops is an error
            stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
            print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
            last_exit = 1
        
        self.last_exit_code = last_exit
        return last_exit
    
    def execute_if_statement(self, if_stmt: IfStatement) -> int:
        """Execute an if/then/else/fi conditional statement."""
        # Apply redirections if present
        if if_stmt.redirects:
            saved_fds = self._apply_redirections(if_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            # Execute the condition and check its exit status
            condition_exit = self.execute_command_list(if_stmt.condition)
            
            # In shell, condition is true if exit code is 0, false otherwise
            if condition_exit == 0:
                # Execute then part
                if if_stmt.then_part.statements:
                    return self.execute_command_list(if_stmt.then_part)
                else:
                    return 0
            else:
                # Execute else part if it exists
                if if_stmt.else_part and if_stmt.else_part.statements:
                    return self.execute_command_list(if_stmt.else_part)
                else:
                    return 0
        finally:
            # Restore file descriptors
            if saved_fds:
                self._restore_redirections(saved_fds)
    
    def execute_while_statement(self, while_stmt: WhileStatement) -> int:
        """Execute a while/do/done loop statement."""
        # Apply redirections if present
        if while_stmt.redirects:
            saved_fds = self._apply_redirections(while_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            last_exit = 0
            
            while True:
                # Execute the condition and check its exit status
                condition_exit = self.execute_command_list(while_stmt.condition)
                
                # In shell, condition is true if exit code is 0, false otherwise
                if condition_exit != 0:
                    # Condition is false, exit the loop
                    break
                    
                # Condition is true, execute the body
                if while_stmt.body.statements:
                    try:
                        # Execute body commands
                        last_exit = self.execute_command_list(while_stmt.body)
                        # Note: We continue the loop regardless of body exit status
                    except LoopBreak:
                        # Break out of the loop
                        break
                    except LoopContinue:
                        # Continue to next iteration
                        continue
                    # (unlike some shells that might break on certain exit codes)
            
            return last_exit
        finally:
            # Restore file descriptors
            if saved_fds:
                self._restore_redirections(saved_fds)
    
    def execute_for_statement(self, for_stmt: ForStatement) -> int:
        """Execute a for/in/do/done loop statement."""
        # Apply redirections if present
        if for_stmt.redirects:
            saved_fds = self._apply_redirections(for_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            last_exit = 0
            
            # Expand the iterable list (handle variables, globs, command substitution, etc.)
            expanded_items = []
            for item in for_stmt.iterable:
                # Special handling for "$@" - it should expand to multiple items
                if item == '$@':
                    expanded_items.extend(self.positional_params)
                elif item.startswith('$(') and item.endswith(')'):
                    # Command substitution with $()
                    output = self._execute_command_substitution(item)
                    if output:
                        # Split on whitespace (word splitting)
                        expanded_items.extend(output.split())
                elif item.startswith('`') and item.endswith('`'):
                    # Command substitution with backticks
                    output = self._execute_command_substitution(item)
                    if output:
                        # Split on whitespace (word splitting)
                        expanded_items.extend(output.split())
                else:
                    # Expand variables in the item
                    expanded_item = self._expand_string_variables(item)
                    
                    # Handle glob patterns
                    if '*' in expanded_item or '?' in expanded_item or '[' in expanded_item:
                        # Use glob to expand patterns
                        import glob
                        matches = glob.glob(expanded_item)
                        if matches:
                            # Sort for consistent ordering
                            expanded_items.extend(sorted(matches))
                        else:
                            # No matches, use literal string
                            expanded_items.append(expanded_item)
                    else:
                        expanded_items.append(expanded_item)
            
            # If no items to iterate over, return successfully
            if not expanded_items:
                return 0
            
            # Save the current value of the loop variable (if it exists)
            loop_var = for_stmt.variable
            saved_value = self.variables.get(loop_var)
            
            try:
                # Iterate over each item
                for item in expanded_items:
                    # Set the loop variable to the current item
                    self.variables[loop_var] = item
                    
                    # Execute the body
                    if for_stmt.body.statements:
                        try:
                            # Execute body commands
                            last_exit = self.execute_command_list(for_stmt.body)
                            # Continue regardless of body exit status
                        except LoopBreak:
                            # Break out of the loop
                            break
                        except LoopContinue:
                            # Continue to next iteration
                            continue
            finally:
                # Restore the previous value of the loop variable
                if saved_value is not None:
                    self.variables[loop_var] = saved_value
                else:
                    # Variable didn't exist before, remove it
                    self.variables.pop(loop_var, None)
            
            return last_exit
        finally:
            # Restore file descriptors
            if saved_fds:
                self._restore_redirections(saved_fds)
    
    def execute_break_statement(self, break_stmt: BreakStatement) -> int:
        """Execute a break statement."""
        raise LoopBreak()
    
    def execute_continue_statement(self, continue_stmt: ContinueStatement) -> int:
        """Execute a continue statement."""
        raise LoopContinue()
    
    def execute_case_statement(self, case_stmt: CaseStatement) -> int:
        """Execute a case/esac statement."""
        # Apply redirections if present
        if case_stmt.redirects:
            saved_fds = self._apply_redirections(case_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            # Expand the case expression
            expr = self._expand_string_variables(case_stmt.expr)
            
            last_exit = 0
            fallthrough = False
            
            # Iterate through case items
            for i, item in enumerate(case_stmt.items):
                # Check if expression matches any pattern in this item
                matched = fallthrough  # Start with fallthrough state
                
                if not fallthrough:
                    # Only check patterns if not falling through
                    for pattern in item.patterns:
                        pattern_str = self._expand_string_variables(pattern.pattern)
                        if fnmatch.fnmatch(expr, pattern_str):
                            matched = True
                            break
                
                if matched:
                    # Execute commands for this case item
                    if item.commands.statements:
                        try:
                            # Execute commands
                            last_exit = self.execute_command_list(item.commands)
                        except LoopBreak:
                            # Break can be used in case statements to exit loops
                            raise
                        except LoopContinue:
                            # Continue can be used in case statements to continue loops
                            raise
                    
                    # Handle fallthrough based on terminator
                    if item.terminator == ';;':
                        # Standard terminator - stop after this case
                        break
                    elif item.terminator == ';&':
                        # Fallthrough to next case unconditionally
                        fallthrough = True
                    elif item.terminator == ';;&':
                        # Continue pattern matching (reset fallthrough)
                        fallthrough = False
                    else:
                        # Default to standard behavior
                        break
                else:
                    # Reset fallthrough if no match
                    fallthrough = False
            
            return last_exit
        finally:
            # Restore file descriptors
            if saved_fds:
                self._restore_redirections(saved_fds)
    
    def _execute_function(self, func, args: list, command: Command) -> int:
        """Execute a function with given arguments."""
        # Save current positional parameters
        saved_params = self.positional_params
        
        # Set up function environment
        self.positional_params = args[1:]  # args[0] is function name
        self.function_stack.append(func.name)
        
        # Apply redirections for the function call
        stdin_backup, stdout_backup, stderr_backup = self._setup_builtin_redirections(command)
        
        try:
            # Execute function body
            exit_code = self.execute_command_list(func.body)
            return exit_code
        except FunctionReturn as ret:
            return ret.exit_code
        finally:
            # Restore redirections
            self._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
            # Restore environment
            self.function_stack.pop()
            self.positional_params = saved_params
    
    def set_positional_params(self, params):
        """Set positional parameters ($1, $2, etc.)."""
        self.positional_params = params.copy() if params else []
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary by looking for null bytes and other indicators."""
        try:
            with open(file_path, 'rb') as f:
                # Read first 1024 bytes for analysis
                chunk = f.read(1024)
                
                if not chunk:
                    return False  # Empty file is not binary
                
                # Check for null bytes (strong indicator of binary)
                if b'\0' in chunk:
                    return True
                
                # Check for very high ratio of non-printable characters
                printable_chars = 0
                for byte in chunk:
                    # Count ASCII printable chars (32-126) plus common whitespace
                    if 32 <= byte <= 126 or byte in (9, 10, 13):  # tab, newline, carriage return
                        printable_chars += 1
                
                # If less than 70% printable characters, consider it binary
                if len(chunk) > 0 and (printable_chars / len(chunk)) < 0.70:
                    return True
                
                # Check for common binary file signatures
                binary_signatures = [
                    b'\x7fELF',      # ELF executable
                    b'MZ',           # DOS/Windows executable
                    b'\xca\xfe\xba\xbe',  # Java class file
                    b'\x89PNG',      # PNG image
                    b'\xff\xd8\xff', # JPEG image
                    b'GIF8',         # GIF image
                    b'%PDF',         # PDF file
                ]
                
                for sig in binary_signatures:
                    if chunk.startswith(sig):
                        return True
                
                return False
                
        except:
            return True  # If we can't read it, assume binary
    
    def _validate_script_file(self, script_path: str) -> int:
        """Validate script file and return appropriate exit code.
        
        Returns:
            0 if file is valid
            126 if permission denied
            127 if file not found
        """
        if not os.path.exists(script_path):
            print(f"psh: {script_path}: No such file or directory", file=sys.stderr)
            return 127
        
        if os.path.isdir(script_path):
            print(f"psh: {script_path}: Is a directory", file=sys.stderr)
            return 126
        
        if not os.access(script_path, os.R_OK):
            print(f"psh: {script_path}: Permission denied", file=sys.stderr)
            return 126
        
        if self._is_binary_file(script_path):
            print(f"psh: {script_path}: cannot execute binary file", file=sys.stderr)
            return 126
        
        return 0
    
    def run_script(self, script_path: str, script_args: list = None) -> int:
        """Execute a script file with optional arguments."""
        if script_args is None:
            script_args = []
            
        # Validate the script file first
        validation_result = self._validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Check for shebang and execute with appropriate interpreter
        if self._should_execute_with_shebang(script_path):
            return self._execute_with_shebang(script_path, script_args)
        
        # Save current script state
        old_script_name = self.script_name
        old_script_mode = self.is_script_mode
        old_positional = self.positional_params.copy()
        
        self.script_name = script_path
        self.is_script_mode = True
        self.positional_params = script_args
        
        try:
            from .input_sources import FileInput
            with FileInput(script_path) as input_source:
                return self._execute_from_source(input_source)
        except Exception as e:
            print(f"psh: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            self.script_name = old_script_name
            self.is_script_mode = old_script_mode
            self.positional_params = old_positional
    
    def _execute_from_source(self, input_source, add_to_history=True) -> int:
        """Execute commands from an input source with enhanced processing."""
        exit_code = 0
        command_buffer = ""
        command_start_line = 0
        
        while True:
            line = input_source.read_line()
            if line is None:  # EOF
                # Execute any remaining command in buffer
                if command_buffer.strip():
                    exit_code = self._execute_buffered_command(
                        command_buffer, input_source, command_start_line, add_to_history
                    )
                break
            
            # Skip empty lines when no command is being built
            if not command_buffer and not line.strip():
                continue
            
            # Skip comment lines when no command is being built
            if not command_buffer and line.strip().startswith('#'):
                continue
            
            # Handle line continuation (backslash at end)
            if line.endswith('\\'):
                # Remove the backslash and add to buffer
                if not command_buffer:
                    command_start_line = input_source.get_line_number()
                command_buffer += line[:-1] + ' '
                continue
            
            # Add current line to buffer
            if not command_buffer:
                command_start_line = input_source.get_line_number()
            # Add line to buffer with proper spacing
            if command_buffer and not command_buffer.endswith('\n'):
                command_buffer += '\n'
            command_buffer += line
            
            # Try to parse and execute the command
            if command_buffer.strip():
                # Check if command is complete by trying to parse it
                try:
                    from .tokenizer import tokenize
                    from .parser import parse, ParseError
                    tokens = tokenize(command_buffer)
                    # Try parsing to see if command is complete
                    parse(tokens)
                    # If parsing succeeds, execute the command
                    exit_code = self._execute_buffered_command(
                        command_buffer.rstrip('\n'), input_source, command_start_line, add_to_history
                    )
                    # Reset buffer for next command
                    command_buffer = ""
                    command_start_line = 0
                except ParseError as e:
                    # Check if this is an incomplete command
                    error_msg = str(e)
                    incomplete_patterns = [
                        ("Expected DO", "got EOF"),
                        ("Expected DONE", "got EOF"),
                        ("Expected FI", "got EOF"),
                        ("Expected THEN", "got EOF"),
                        ("Expected IN", "got EOF"),
                        ("Expected ESAC", "got EOF"),
                        ("Expected '}' to end compound command", None),  # Function bodies
                        ("Expected RPAREN", "got EOF"),
                    ]
                    
                    is_incomplete = False
                    for expected, got in incomplete_patterns:
                        if expected in error_msg:
                            if got is None or got in error_msg:
                                is_incomplete = True
                                break
                    
                    if is_incomplete:
                        # Command is incomplete, continue reading
                        continue
                    else:
                        # It's a real parse error, report it and reset
                        filename = input_source.get_name() if hasattr(input_source, 'get_name') else 'stdin'
                        print(f"{filename}:{command_start_line}: {e}", file=sys.stderr)
                        command_buffer = ""
                        command_start_line = 0
                        exit_code = 1
                        self.last_exit_code = 1
        
        return exit_code
    
    def _execute_buffered_command(self, command_string: str, input_source, start_line: int, add_to_history: bool) -> int:
        """Execute a buffered command with enhanced error reporting."""
        # Skip empty commands and comments
        if not command_string.strip() or command_string.strip().startswith('#'):
            return 0
        
        try:
            tokens = tokenize(command_string)
            
            # Debug: Print tokens if requested
            if self.debug_tokens:
                print("=== Token Debug Output ===", file=sys.stderr)
                print(self._format_tokens(tokens), file=sys.stderr)
                print("========================", file=sys.stderr)
            
            # Expand aliases
            tokens = self.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Debug: Print AST if requested
            if self.debug_ast:
                print("=== AST Debug Output ===", file=sys.stderr)
                print(self._format_ast(ast), file=sys.stderr)
                print("======================", file=sys.stderr)
            
            # Add to history if requested (for interactive or testing)
            if add_to_history and command_string.strip():
                self._add_to_history(command_string.strip())
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                try:
                    # Collect here documents if any
                    self._collect_heredocs(ast)
                    exit_code = self.execute_command_list(ast)
                    return exit_code
                except (LoopBreak, LoopContinue) as e:
                    # Break/continue outside of loops is an error
                    stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
                    print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
                    return 1
        except ParseError as e:
            # Enhanced error message with location
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
        except Exception as e:
            # Enhanced error message with location  
            location = f"{input_source.get_name()}:{start_line}" if start_line > 0 else "command"
            print(f"psh: {location}: unexpected error: {e}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
    
    def run_command(self, command_string: str, add_to_history=True):
        """Execute a command string using the unified input system."""
        from .input_sources import StringInput
        
        # Use the unified execution system for consistency
        input_source = StringInput(command_string, "<command>")
        return self._execute_from_source(input_source, add_to_history)
    
    def interactive_loop(self):
        # Set up readline for better line editing
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(' \t\n;|&<>')
        
        # Set up tab completion with current edit mode
        line_editor = LineEditor(self.history, edit_mode=self.edit_mode)
        
        while True:
            try:
                # Check for completed background jobs
                self.job_manager.notify_completed_jobs()
                
                # Check for stopped jobs (from Ctrl-Z)
                self.job_manager.notify_stopped_jobs()
                
                # Create prompt with exit status
                if self.last_exit_code == 0:
                    prompt = 'psh$ '
                else:
                    prompt = f'psh[{self.last_exit_code}]$ '
                
                # Use our custom input handler for tab completion
                command = line_editor.read_line(prompt)
                
                if command is None:  # EOF (Ctrl-D)
                    print()  # New line before exit
                    break
                
                if command.strip():
                    self.run_command(command)
                    
            except KeyboardInterrupt:
                # Ctrl-C pressed, just print newline and continue
                print()
                self.last_exit_code = 130  # 128 + SIGINT(2)
                continue
            except EOFError:
                # Ctrl-D pressed
                print()
                break
            except Exception as e:
                print(f"psh: {e}", file=sys.stderr)
                self.last_exit_code = 1
        
        # Save history on exit
        self._save_history()
    
    # Built-in commands have been moved to the builtins module
    
    def _parse_shebang(self, script_path: str) -> tuple:
        """Parse shebang line from script file.
        
        Returns:
            tuple: (has_shebang, interpreter_path, interpreter_args)
        """
        try:
            with open(script_path, 'rb') as f:
                # Read first line, max 1024 bytes
                first_line = f.readline(1024)
                
                # Check for shebang
                if not first_line.startswith(b'#!'):
                    return (False, None, [])
                
                # Decode shebang line
                try:
                    shebang_line = first_line[2:].decode('utf-8', errors='ignore').strip()
                except UnicodeDecodeError:
                    return (False, None, [])
                
                if not shebang_line:
                    return (False, None, [])
                
                # Parse interpreter and arguments
                parts = shebang_line.split()
                if not parts:
                    return (False, None, [])
                
                interpreter = parts[0]
                interpreter_args = parts[1:] if len(parts) > 1 else []
                
                return (True, interpreter, interpreter_args)
                
        except (IOError, OSError):
            return (False, None, [])
    
    def _should_execute_with_shebang(self, script_path: str) -> bool:
        """Determine if script should be executed with its shebang interpreter."""
        has_shebang, interpreter, interpreter_args = self._parse_shebang(script_path)
        
        if not has_shebang:
            return False
        
        # If interpreter is psh or our script name, use psh directly
        if interpreter.endswith('/psh') or interpreter == 'psh':
            return False
        
        # Handle /usr/bin/env pattern - check the actual interpreter
        if interpreter.endswith('/env') or interpreter == 'env':
            # Get the actual interpreter from interpreter_args
            if not interpreter_args:
                return False
            actual_interpreter = interpreter_args[0]
            if actual_interpreter.endswith('/psh') or actual_interpreter == 'psh':
                return False
        
        # Check if interpreter exists and is executable
        if interpreter.startswith('/'):
            # Absolute path
            return os.path.exists(interpreter) and os.access(interpreter, os.X_OK)
        else:
            # Search in PATH
            path_dirs = self.env.get('PATH', '').split(':')
            for path_dir in path_dirs:
                if path_dir:
                    full_path = os.path.join(path_dir, interpreter)
                    if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                        return True
            return False
    
    def _execute_with_shebang(self, script_path: str, script_args: list) -> int:
        """Execute script using its shebang interpreter."""
        has_shebang, interpreter, interpreter_args = self._parse_shebang(script_path)
        
        if not has_shebang:
            return 1
        
        # Build command line for interpreter
        cmd_args = []
        
        # Add interpreter
        cmd_args.append(interpreter)
        
        # Add interpreter arguments
        cmd_args.extend(interpreter_args)
        
        # Add script path
        cmd_args.append(script_path)
        
        # Add script arguments
        cmd_args.extend(script_args)
        
        try:
            # Execute the interpreter
            import subprocess
            result = subprocess.run(cmd_args, env=self.env)
            return result.returncode
        except FileNotFoundError:
            print(f"psh: {interpreter}: No such file or directory", file=sys.stderr)
            return 127
        except PermissionError:
            print(f"psh: {interpreter}: Permission denied", file=sys.stderr)
            return 126
        except Exception as e:
            print(f"psh: {interpreter}: {e}", file=sys.stderr)
            return 1
    
    def _collect_heredocs(self, node):
        """Collect here document content for all commands in a node"""
        if isinstance(node, CommandList):
            # Process all statements in the command list
            for item in node.statements:
                self._collect_heredocs(item)
        elif isinstance(node, AndOrList):
            # Process pipelines in and_or_list
            for pipeline in node.pipelines:
                for command in pipeline.commands:
                    for redirect in command.redirects:
                        if redirect.type in ('<<', '<<-'):
                            # Collect here document content
                            lines = []
                            delimiter = redirect.target
                            
                            # Read lines until we find the delimiter
                            while True:
                                try:
                                    line = input()
                                    if line.strip() == delimiter:
                                        break
                                    if redirect.type == '<<-':
                                        # Strip leading tabs
                                        line = line.lstrip('\t')
                                    lines.append(line)
                                except EOFError:
                                    break
                            
                            redirect.heredoc_content = '\n'.join(lines)
                            if lines:  # Add final newline if there was content
                                redirect.heredoc_content += '\n'
        elif isinstance(node, IfStatement):
            # Recursively collect for if statement parts
            self._collect_heredocs(node.condition)
            self._collect_heredocs(node.then_part)
            if node.else_part:
                self._collect_heredocs(node.else_part)
        elif isinstance(node, WhileStatement):
            # Recursively collect for while statement parts
            self._collect_heredocs(node.condition)
            self._collect_heredocs(node.body)
        elif isinstance(node, ForStatement):
            # Recursively collect for for statement body
            self._collect_heredocs(node.body)
        elif isinstance(node, CaseStatement):
            # Recursively collect for case items
            for item in node.items:
                self._collect_heredocs(item.commands)
        # BreakStatement and ContinueStatement don't have heredocs
    
    def _add_to_history(self, command):
        """Add a command to history"""
        # Don't add duplicates of the immediately previous command
        if not self.history or self.history[-1] != command:
            self.history.append(command)
            readline.add_history(command)
            # Trim history if it exceeds max size
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]
    
    def _load_history(self):
        """Load command history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line:
                            self.history.append(line)
                            readline.add_history(line)
                # Trim to max size
                if len(self.history) > self.max_history_size:
                    self.history = self.history[-self.max_history_size:]
        except Exception:
            # Silently ignore history file errors
            pass
    
    def _save_history(self):
        """Save command history to file"""
        try:
            with open(self.history_file, 'w') as f:
                # Save only the last max_history_size commands
                for cmd in self.history[-self.max_history_size:]:
                    f.write(cmd + '\n')
        except Exception:
            # Silently ignore history file errors
            pass
    
    def _handle_sigint(self, signum, frame):
        """Handle Ctrl-C (SIGINT)"""
        # Just print a newline - the command loop will handle the rest
        print()
        # The signal will be delivered to the foreground process group
        # which is set in execute_pipeline
    
    def _handle_sigchld(self, signum, frame):
        """Handle child process state changes."""
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                
                job = self.job_manager.get_job_by_pid(pid)
                if job:
                    job.update_process_status(pid, status)
                    job.update_state()
                    
                    # Check if entire job is stopped
                    if job.state == JobState.STOPPED and job.foreground:
                        # Stopped foreground job - mark as not notified so it will be shown
                        job.notified = False
                        
                        # Return control to shell
                        try:
                            os.tcsetpgrp(0, os.getpgrp())
                        except OSError:
                            pass
                        
                        self.job_manager.set_foreground_job(None)
                        job.foreground = False
            except OSError:
                break
    
    def _apply_redirections(self, redirects: List[Redirect]) -> List[Tuple[int, int]]:
        """Apply redirections and return list of (fd, saved_fd) for restoration."""
        saved_fds = []
        
        # Save current Python file objects
        self._saved_stdout = self.stdout
        self._saved_stderr = self.stderr
        self._saved_stdin = self.stdin
        
        for redirect in redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self._expand_tilde(target)
            
            # Handle process substitution as redirect target
            if target and target.startswith(('<(', '>(')) and target.endswith(')'):
                # This is a process substitution used as a redirect target
                # Set up the process substitution and get the fd path
                if target.startswith('<('):
                    direction = 'in'
                    cmd_str = target[2:-1]
                else:
                    direction = 'out' 
                    cmd_str = target[2:-1]
                
                # Create pipe
                if direction == 'in':
                    read_fd, write_fd = os.pipe()
                    parent_fd = read_fd
                    child_fd = write_fd
                    child_stdout = child_fd
                    child_stdin = 0
                else:
                    read_fd, write_fd = os.pipe()
                    parent_fd = write_fd
                    child_fd = read_fd
                    child_stdout = 1
                    child_stdin = child_fd
                
                # Clear close-on-exec flag
                flags = fcntl.fcntl(parent_fd, fcntl.F_GETFD)
                fcntl.fcntl(parent_fd, fcntl.F_SETFD, flags & ~fcntl.FD_CLOEXEC)
                
                # Fork child
                pid = os.fork()
                if pid == 0:  # Child
                    os.close(parent_fd)
                    if direction == 'in':
                        os.dup2(child_stdout, 1)
                    else:
                        os.dup2(child_stdin, 0)
                    os.close(child_fd)
                    
                    try:
                        tokens = tokenize(cmd_str)
                        ast = parse(tokens)
                        temp_shell = Shell()
                        temp_shell.env = self.env.copy()
                        temp_shell.variables = self.variables.copy()
                        exit_code = temp_shell.execute_command_list(ast)
                        os._exit(exit_code)
                    except Exception as e:
                        print(f"psh: process substitution error: {e}", file=sys.stderr)
                        os._exit(1)
                else:  # Parent
                    os.close(child_fd)
                    # Store for cleanup
                    if not hasattr(self, '_redirect_proc_sub_fds'):
                        self._redirect_proc_sub_fds = []
                    if not hasattr(self, '_redirect_proc_sub_pids'):
                        self._redirect_proc_sub_pids = []
                    self._redirect_proc_sub_fds.append(parent_fd)
                    self._redirect_proc_sub_pids.append(pid)
                    # Use the fd path as target
                    target = f"/dev/fd/{parent_fd}"
            
            if redirect.type == '<':
                # Save current stdin
                saved_fds.append((0, os.dup(0)))
                fd = os.open(target, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)
            elif redirect.type in ('<<', '<<-'):
                # Save current stdin
                saved_fds.append((0, os.dup(0)))
                # Create a pipe for heredoc
                r, w = os.pipe()
                # Write heredoc content to pipe
                os.write(w, (redirect.heredoc_content or '').encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '<<<':
                # Save current stdin
                saved_fds.append((0, os.dup(0)))
                # Create a pipe for here string
                r, w = os.pipe()
                # Write here string content with newline
                content = redirect.target + '\n'
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '>':
                target_fd = redirect.fd if redirect.fd is not None else 1
                # Save current fd
                saved_fds.append((target_fd, os.dup(target_fd)))
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                os.dup2(fd, target_fd)
                os.close(fd)
            elif redirect.type == '>>':
                target_fd = redirect.fd if redirect.fd is not None else 1
                # Save current fd
                saved_fds.append((target_fd, os.dup(target_fd)))
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                os.dup2(fd, target_fd)
                os.close(fd)
            elif redirect.type == '>&':
                # Handle fd duplication like 2>&1
                if redirect.fd is not None and redirect.dup_fd is not None:
                    # Save current fd
                    saved_fds.append((redirect.fd, os.dup(redirect.fd)))
                    os.dup2(redirect.dup_fd, redirect.fd)
        
        # Note: We don't create new Python file objects here because:
        # 1. It can interfere with pytest's output capture
        # 2. External commands will inherit the redirected file descriptors
        # 3. Builtins should use os.write() directly to fd 1/2 for proper redirection
        
        return saved_fds
    
    def _restore_redirections(self, saved_fds: List[Tuple[int, int]]):
        """Restore file descriptors from saved list."""
        # Restore file descriptors
        for fd, saved_fd in saved_fds:
            os.dup2(saved_fd, fd)
            os.close(saved_fd)
        
        # Restore Python file objects
        if hasattr(self, '_saved_stdout'):
            self.stdout = self._saved_stdout
            self.stderr = self._saved_stderr
            self.stdin = self._saved_stdin
        
        # Clean up process substitution fds and wait for children
        if hasattr(self, '_redirect_proc_sub_fds'):
            for fd in self._redirect_proc_sub_fds:
                try:
                    os.close(fd)
                except:
                    pass
            del self._redirect_proc_sub_fds
        
        if hasattr(self, '_redirect_proc_sub_pids'):
            for pid in self._redirect_proc_sub_pids:
                try:
                    os.waitpid(pid, 0)
                except:
                    pass
            del self._redirect_proc_sub_pids
    
    def _setup_child_redirections(self, command: Command):
        """Set up redirections in child process (after fork) using dup2"""
        for redirect in command.redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self._expand_tilde(target)
            
            if redirect.type == '<':
                fd = os.open(target, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)
            elif redirect.type in ('<<', '<<-'):
                # Create a pipe for heredoc
                r, w = os.pipe()
                # Write heredoc content to pipe
                os.write(w, (redirect.heredoc_content or '').encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '<<<':
                # Create a pipe for here string
                r, w = os.pipe()
                # Write here string content with newline
                content = redirect.target + '\n'
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '>':
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                target_fd = redirect.fd if redirect.fd is not None else 1
                os.dup2(fd, target_fd)
                os.close(fd)
            elif redirect.type == '>>':
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                target_fd = redirect.fd if redirect.fd is not None else 1
                os.dup2(fd, target_fd)
                os.close(fd)
            elif redirect.type == '>&':
                # Handle fd duplication like 2>&1
                if redirect.fd is not None and redirect.dup_fd is not None:
                    os.dup2(redirect.dup_fd, redirect.fd)
    
    def _execute_in_child(self, command: Command):
        """Execute a command in a child process (after fork)"""
        # Expand arguments (reuse the same method as execute_command)
        args = self._expand_arguments(command)
        
        if not args:
            return 0
        
        # Set up redirections
        try:
            self._setup_child_redirections(command)
        except Exception as e:
            print(f"psh: {e}", file=sys.stderr)
            return 1
        
        # Check for function call BEFORE builtin check
        func = self.function_manager.get_function(args[0])
        if func:
            # Functions need special handling in child process
            # We can't use the normal _execute_function because it expects Command object
            # Save current positional parameters
            saved_params = self.positional_params
            self.positional_params = args[1:]
            self.function_stack.append(func.name)
            
            try:
                exit_code = self.execute_command_list(func.body)
                return exit_code
            except FunctionReturn as ret:
                return ret.exit_code
            finally:
                self.function_stack.pop()
                self.positional_params = saved_params
        
        # Check for built-in commands (new registry first, then old dict)
        builtin = self.builtin_registry.get(args[0])
        if builtin:
            try:
                return builtin.execute(args, self)
            except FunctionReturn:
                # Should not happen in child process
                print("return: can only `return' from a function or sourced script", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        elif args[0] in self.builtins:
            try:
                return self.builtins[args[0]](args)
            except FunctionReturn:
                # Should not happen in child process
                print("return: can only `return' from a function or sourced script", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        
        # Execute external command
        try:
            # Execute with execvpe to pass environment
            os.execvpe(args[0], args, self.env)
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1
    
    def _format_ast(self, node, indent=0):
        """Format AST node for debugging output."""
        spaces = "  " * indent
        
        if isinstance(node, TopLevel):
            result = f"{spaces}TopLevel:\n"
            for item in node.items:
                result += self._format_ast(item, indent + 1)
            return result
        
        elif isinstance(node, CommandList):
            result = f"{spaces}CommandList:\n"
            for stmt in node.statements:
                result += self._format_ast(stmt, indent + 1)
            return result
        
        elif isinstance(node, AndOrList):
            result = f"{spaces}AndOrList:\n"
            for i, pipeline in enumerate(node.pipelines):
                if i < len(node.operators):
                    result += f"{spaces}  Operator: {node.operators[i]}\n"
                result += self._format_ast(pipeline, indent + 1)
            return result
        
        elif isinstance(node, Pipeline):
            result = f"{spaces}Pipeline:\n"
            for cmd in node.commands:
                result += self._format_ast(cmd, indent + 1)
            return result
        
        elif isinstance(node, Command):
            result = f"{spaces}Command: {' '.join(node.args)}"
            if node.background:
                result += " &"
            result += "\n"
            for redirect in node.redirects:
                result += self._format_ast(redirect, indent + 1)
            return result
        
        elif isinstance(node, Redirect):
            result = f"{spaces}Redirect: "
            if node.fd is not None:
                result += f"{node.fd}"
            result += f"{node.type} {node.target}"
            if node.dup_fd is not None:
                result += f" (dup fd {node.dup_fd})"
            if node.heredoc_content:
                result += f" (heredoc: {len(node.heredoc_content)} chars)"
            result += "\n"
            return result
        
        elif isinstance(node, FunctionDef):
            result = f"{spaces}FunctionDef: {node.name}()\n"
            result += self._format_ast(node.body, indent + 1)
            return result
        
        elif isinstance(node, IfStatement):
            result = f"{spaces}IfStatement:\n"
            result += f"{spaces}  Condition:\n"
            result += self._format_ast(node.condition, indent + 2)
            result += f"{spaces}  Then:\n"
            result += self._format_ast(node.then_part, indent + 2)
            if node.else_part:
                result += f"{spaces}  Else:\n"
                result += self._format_ast(node.else_part, indent + 2)
            return result
        
        elif isinstance(node, WhileStatement):
            result = f"{spaces}WhileStatement:\n"
            result += f"{spaces}  Condition:\n"
            result += self._format_ast(node.condition, indent + 2)
            result += f"{spaces}  Body:\n"
            result += self._format_ast(node.body, indent + 2)
            return result
        
        elif isinstance(node, ForStatement):
            result = f"{spaces}ForStatement:\n"
            result += f"{spaces}  Variable: {node.variable}\n"
            result += f"{spaces}  Iterable: {node.iterable}\n"
            result += f"{spaces}  Body:\n"
            result += self._format_ast(node.body, indent + 2)
            return result
        
        elif isinstance(node, CaseStatement):
            result = f"{spaces}CaseStatement: {node.expr}\n"
            for item in node.items:
                result += self._format_ast(item, indent + 1)
            return result
        
        elif isinstance(node, CaseItem):
            patterns = " | ".join(p.pattern for p in node.patterns)
            result = f"{spaces}CaseItem: {patterns}) terminator={node.terminator}\n"
            result += self._format_ast(node.commands, indent + 1)
            return result
        
        elif isinstance(node, BreakStatement):
            return f"{spaces}BreakStatement\n"
        
        elif isinstance(node, ContinueStatement):
            return f"{spaces}ContinueStatement\n"
        
        else:
            return f"{spaces}{type(node).__name__}: {repr(node)}\n"
    
    def _format_tokens(self, tokens):
        """Format token list for debugging output."""
        from .tokenizer import Token
        
        result = []
        for i, token in enumerate(tokens):
            if isinstance(token, Token):
                result.append(f"  [{i:3d}] {token.type.name:20s} '{token.value}'")
            else:
                # Handle legacy token format if any
                result.append(f"  [{i:3d}] {str(token)}")
        
        return "\n".join(result)
    
    def _setup_process_substitutions(self, command: Command) -> Tuple[List[int], List[str], List[int]]:
        """Set up process substitutions and return (fds, paths, child_pids)."""
        fds_to_keep = []
        substituted_args = []
        child_pids = []
        
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            
            if arg_type in ('PROCESS_SUB_IN', 'PROCESS_SUB_OUT'):
                # Extract command from <(cmd) or >(cmd)
                if arg.startswith('<('):
                    direction = 'in'
                    cmd_str = arg[2:-1]  # Remove <( and )
                elif arg.startswith('>('):
                    direction = 'out'
                    cmd_str = arg[2:-1]  # Remove >( and )
                else:
                    # Should not happen
                    substituted_args.append(arg)
                    continue
                
                # Create pipe
                if direction == 'in':
                    # For <(cmd), parent reads from pipe, child writes to it
                    read_fd, write_fd = os.pipe()
                    parent_fd = read_fd
                    child_fd = write_fd
                    child_stdout = child_fd
                    child_stdin = 0
                else:
                    # For >(cmd), parent writes to pipe, child reads from it
                    read_fd, write_fd = os.pipe()
                    parent_fd = write_fd
                    child_fd = read_fd
                    child_stdout = 1
                    child_stdin = child_fd
                
                # Clear close-on-exec flag for parent_fd so it survives exec
                flags = fcntl.fcntl(parent_fd, fcntl.F_GETFD)
                fcntl.fcntl(parent_fd, fcntl.F_SETFD, flags & ~fcntl.FD_CLOEXEC)
                
                # Fork child for process substitution
                pid = os.fork()
                if pid == 0:  # Child
                    # Close parent's end of pipe
                    os.close(parent_fd)
                    
                    # Set up child's stdio
                    if direction == 'in':
                        os.dup2(child_stdout, 1)
                    else:
                        os.dup2(child_stdin, 0)
                    
                    # Close the pipe fd we duplicated
                    os.close(child_fd)
                    
                    # Execute the substitution command
                    try:
                        # Parse and execute the command string
                        tokens = tokenize(cmd_str)
                        ast = parse(tokens)
                        # Create a new shell instance to avoid state pollution
                        temp_shell = Shell()
                        temp_shell.env = self.env.copy()
                        temp_shell.variables = self.variables.copy()
                        exit_code = temp_shell.execute_command_list(ast)
                        os._exit(exit_code)
                    except Exception as e:
                        print(f"psh: process substitution error: {e}", file=sys.stderr)
                        os._exit(1)
                
                else:  # Parent
                    # Close child's end of pipe
                    os.close(child_fd)
                    
                    # Keep track of what we need to clean up
                    fds_to_keep.append(parent_fd)
                    child_pids.append(pid)
                    
                    # Create path for this fd
                    # On Linux/macOS, we can use /dev/fd/N
                    fd_path = f"/dev/fd/{parent_fd}"
                    substituted_args.append(fd_path)
            else:
                # Not a process substitution, keep as-is
                substituted_args.append(arg)
        
        return fds_to_keep, substituted_args, child_pids
    
    def _cleanup_process_substitutions(self):
        """Clean up process substitution file descriptors and wait for children."""
        if hasattr(self, '_process_sub_fds'):
            for fd in self._process_sub_fds:
                try:
                    os.close(fd)
                except:
                    pass
            del self._process_sub_fds
        
        if hasattr(self, '_process_sub_pids'):
            for pid in self._process_sub_pids:
                try:
                    os.waitpid(pid, 0)
                except:
                    pass
            del self._process_sub_pids