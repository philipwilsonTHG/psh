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
from .ast_nodes import Command, Pipeline, CommandList, AndOrList, Redirect, TopLevel, FunctionDef, IfStatement, WhileStatement, ForStatement, BreakStatement, ContinueStatement, CaseStatement, CaseItem, CasePattern, ProcessSubstitution, EnhancedTestStatement, TestExpression, BinaryTestExpression, UnaryTestExpression, CompoundTestExpression, NegatedTestExpression
from .line_editor import LineEditor
from .multiline_handler import MultiLineInputHandler
from .version import get_version_info
from .aliases import AliasManager
from .functions import FunctionManager
from .job_control import JobManager, JobState
from .builtins import registry as builtin_registry
from .builtins.function_support import FunctionReturn

# Import from new core modules
from .core.exceptions import LoopBreak, LoopContinue
from .core.state import ShellState
from .utils.ast_formatter import ASTFormatter
from .utils.token_formatter import TokenFormatter
from .expansion.manager import ExpansionManager
from .io_redirect.manager import IOManager
from .executor.base import ExecutorManager
from .scripting.base import ScriptManager

class Shell:
    def __init__(self, args=None, script_name=None, debug_ast=False, debug_tokens=False, norc=False, rcfile=None):
        # Initialize state
        self.state = ShellState(args, script_name, debug_ast, 
                              debug_tokens, norc, rcfile)
        
        # Create backward compatibility properties
        self._setup_compatibility_properties()
        
        # Use new builtin registry for migrated builtins
        self.builtin_registry = builtin_registry
        
        # All builtins are now handled by the registry
        self.builtins = {}
        
        # Load history
        self._load_history()
        
        # Alias management
        self.alias_manager = AliasManager()
        
        # Function management
        self.function_manager = FunctionManager()
        
        # Job control
        self.job_manager = JobManager()
        
        # Expansion management
        self.expansion_manager = ExpansionManager(self)
        
        # I/O redirection management
        self.io_manager = IOManager(self)
        
        # Executor management
        self.executor_manager = ExecutorManager(self)
        
        # Script handling management
        self.script_manager = ScriptManager(self)
        
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
        
        # Load RC file for interactive shells
        # Allow force_interactive for testing purposes
        is_interactive = getattr(self, '_force_interactive', sys.stdin.isatty())
        if not self.is_script_mode and is_interactive and not self.norc:
            self._load_rc_file()
    
    def _setup_compatibility_properties(self):
        """Set up properties for backward compatibility."""
        # These will be removed in later phases
        self._state_properties = [
            'env', 'variables', 'positional_params', 'script_name',
            'is_script_mode', 'debug_ast', 'debug_tokens', 'norc', 'rcfile',
            'last_exit_code', 'last_bg_pid', 'foreground_pgid', 'command_number',
            'history', 'history_file', 'max_history_size', 'history_index',
            'current_line', 'edit_mode', 'function_stack', '_in_forked_child',
            'stdout', 'stderr', 'stdin'
        ]
    
    def __getattr__(self, name):
        """Delegate attribute access to state for compatibility."""
        if hasattr(self.state, name):
            return getattr(self.state, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Delegate attribute setting to state for compatibility."""
        if name in ('state', '_state_properties', 'builtin_registry', 'builtins', 
                   'alias_manager', 'function_manager', 'job_manager', 'expansion_manager',
                   'io_manager', 'executor_manager', 'script_manager'):
            super().__setattr__(name, value)
        elif hasattr(self, '_state_properties') and name in self._state_properties:
            setattr(self.state, name, value)
        else:
            super().__setattr__(name, value)
    
    def _expand_string_variables(self, text: str) -> str:
        """Expand variables and arithmetic in a string (for here strings and quoted strings)"""
        return self.expansion_manager.expand_string_variables(text)
    
    def _expand_variable(self, var_expr: str) -> str:
        """Expand a variable expression starting with $"""
        return self.expansion_manager.expand_variable(var_expr)
    
    def _expand_tilde(self, path: str) -> str:
        """Expand tilde in paths like ~ and ~user"""
        return self.expansion_manager.expand_tilde(path)
    
    def _execute_command_substitution(self, cmd_sub: str) -> str:
        """Execute command substitution and return output"""
        return self.expansion_manager.execute_command_substitution(cmd_sub)
    
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
            # Update quote_types as well
            command.quote_types = [None] * len(substituted_args)
        
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            quote_type = command.quote_types[i] if i < len(command.quote_types) else None
            
            if arg_type == 'STRING':
                # Handle quoted strings
                if quote_type == '"' and '$' in arg:
                    # Double-quoted string with variables - expand them
                    # Special handling for "$@"
                    if arg == '$@':
                        # "$@" expands to multiple arguments, each properly quoted
                        args.extend(self.positional_params)
                        continue
                    else:
                        # Expand variables within the string
                        arg = self._expand_string_variables(arg)
                        args.append(arg)
                else:
                    # Single-quoted string or no variables - no expansion
                    args.append(arg)
            elif arg.startswith('$') and not (arg.startswith('$(') or arg.startswith('`')):
                # Variable expansion for unquoted variables
                expanded = self._expand_variable(arg)
                args.append(expanded)
            elif '\\$' in arg and arg_type == 'WORD':
                # Escaped dollar sign in word - replace with literal $
                args.append(arg.replace('\\$', '$'))
            elif arg_type == 'COMPOSITE':
                # Composite argument - already concatenated in parser
                # Just perform glob expansion if it contains wildcards
                if any(c in arg for c in ['*', '?', '[']):
                    matches = glob.glob(arg)
                    if matches:
                        args.extend(sorted(matches))
                    else:
                        args.append(arg)
                else:
                    args.append(arg)
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
                # Handle regular words
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
            # Set flag to indicate we're in a forked child
            self._in_forked_child = True
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
        
        # For now, keep the existing implementation but gradually move to executor
        # This allows us to test incrementally
        
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
                exit_status = self.execute_command(pipeline.commands[0])
                # Apply negation if needed
                if pipeline.negated:
                    exit_status = 0 if exit_status != 0 else 1
                return exit_status
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
                # Set flag to indicate we're in a forked child
                self._in_forked_child = True
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
        
        # Apply negation if needed
        if pipeline.negated:
            last_status = 0 if last_status != 0 else 1
        
        return last_status
    
    def execute_and_or_list(self, and_or_list: AndOrList):
        """Execute pipelines with && and || operators, implementing short-circuit evaluation"""
        return self.executor_manager.statement_executor.execute_and_or_list(and_or_list)
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        try:
            for item in command_list.statements:
                if isinstance(item, BreakStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, ContinueStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute(item)
                elif isinstance(item, IfStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_if(item)
                elif isinstance(item, WhileStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_while(item)
                elif isinstance(item, ForStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_for(item)
                elif isinstance(item, CaseStatement):
                    exit_code = self.executor_manager.control_flow_executor.execute_case(item)
                elif isinstance(item, EnhancedTestStatement):
                    exit_code = self.execute_enhanced_test_statement(item)
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
                    exit_code = self.executor_manager.statement_executor.execute_and_or_list(item)
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
                elif isinstance(item, EnhancedTestStatement):
                    # Execute enhanced test statement
                    last_exit = self.execute_enhanced_test_statement(item)
        except (LoopBreak, LoopContinue) as e:
            # Break/continue outside of loops is an error
            stmt_name = "break" if isinstance(e, LoopBreak) else "continue"
            print(f"{stmt_name}: only meaningful in a `for' or `while' loop", file=sys.stderr)
            last_exit = 1
        
        self.last_exit_code = last_exit
        return last_exit
    
    def execute_if_statement(self, if_stmt: IfStatement) -> int:
        """Execute an if/then/else/fi conditional statement."""
        return self.executor_manager.control_flow_executor.execute_if(if_stmt)
    
    def execute_while_statement(self, while_stmt: WhileStatement) -> int:
        """Execute a while/do/done loop statement."""
        return self.executor_manager.control_flow_executor.execute_while(while_stmt)
    
    def execute_for_statement(self, for_stmt: ForStatement) -> int:
        """Execute a for/in/do/done loop statement."""
        return self.executor_manager.control_flow_executor.execute_for(for_stmt)
    
    def execute_break_statement(self, break_stmt: BreakStatement) -> int:
        """Execute a break statement."""
        return self.executor_manager.control_flow_executor.execute(break_stmt)
    
    def execute_continue_statement(self, continue_stmt: ContinueStatement) -> int:
        """Execute a continue statement."""
        return self.executor_manager.control_flow_executor.execute(continue_stmt)
    
    def execute_case_statement(self, case_stmt: CaseStatement) -> int:
        """Execute a case/esac statement."""
        return self.executor_manager.control_flow_executor.execute_case(case_stmt)
    
    def execute_enhanced_test_statement(self, test_stmt: EnhancedTestStatement) -> int:
        """Execute an enhanced test statement [[...]]."""
        # Apply redirections if present
        if test_stmt.redirects:
            saved_fds = self._apply_redirections(test_stmt.redirects)
        else:
            saved_fds = None
        
        try:
            result = self._evaluate_test_expression(test_stmt.expression)
            # DEBUG
            # print(f"DEBUG: Enhanced test result={result}, returning {0 if result else 1}", file=sys.stderr)
            return 0 if result else 1
        except Exception as e:
            print(f"psh: [[: {e}", file=sys.stderr)
            return 2  # Syntax error
        finally:
            # Restore file descriptors
            if saved_fds:
                self._restore_redirections(saved_fds)
    
    def _evaluate_test_expression(self, expr: TestExpression) -> bool:
        """Evaluate a test expression to boolean."""
        if isinstance(expr, BinaryTestExpression):
            return self._evaluate_binary_test(expr)
        elif isinstance(expr, UnaryTestExpression):
            return self._evaluate_unary_test(expr)
        elif isinstance(expr, CompoundTestExpression):
            return self._evaluate_compound_test(expr)
        elif isinstance(expr, NegatedTestExpression):
            return not self._evaluate_test_expression(expr.expression)
        else:
            raise ValueError(f"Unknown test expression type: {type(expr).__name__}")
    
    def _evaluate_binary_test(self, expr: BinaryTestExpression) -> bool:
        """Evaluate binary test expression."""
        # Expand variables in operands
        left = self._expand_string_variables(expr.left)
        right = self._expand_string_variables(expr.right)
        
        # Handle different operators
        if expr.operator == '=':
            return left == right
        elif expr.operator == '==':
            return left == right
        elif expr.operator == '!=':
            return left != right
        elif expr.operator == '<':
            # Lexicographic comparison
            return left < right
        elif expr.operator == '>':
            # Lexicographic comparison
            return left > right
        elif expr.operator == '=~':
            # Regex matching
            import re
            try:
                pattern = re.compile(right)
                return bool(pattern.search(left))
            except re.error as e:
                raise ValueError(f"invalid regex: {e}")
        elif expr.operator == '-eq':
            return self._to_int(left) == self._to_int(right)
        elif expr.operator == '-ne':
            return self._to_int(left) != self._to_int(right)
        elif expr.operator == '-lt':
            return self._to_int(left) < self._to_int(right)
        elif expr.operator == '-le':
            return self._to_int(left) <= self._to_int(right)
        elif expr.operator == '-gt':
            return self._to_int(left) > self._to_int(right)
        elif expr.operator == '-ge':
            return self._to_int(left) >= self._to_int(right)
        elif expr.operator == '-nt':
            # File newer than
            return self._file_newer_than(left, right)
        elif expr.operator == '-ot':
            # File older than
            return self._file_older_than(left, right)
        elif expr.operator == '-ef':
            # Files are the same
            return self._files_same(left, right)
        else:
            raise ValueError(f"unknown binary operator: {expr.operator}")
    
    def _evaluate_unary_test(self, expr: UnaryTestExpression) -> bool:
        """Evaluate unary test expression."""
        # Expand variables in operand
        operand = self._expand_string_variables(expr.operand)
        
        # Import test command's unary operators
        from .builtins.test_command import TestBuiltin
        test_cmd = TestBuiltin()
        
        # Reuse the existing unary operator implementation
        # Note: _evaluate_unary returns 0 for true, 1 for false (shell convention)
        # We need to convert to boolean
        result = test_cmd._evaluate_unary(expr.operator, operand)
        return result == 0
    
    def _evaluate_compound_test(self, expr: CompoundTestExpression) -> bool:
        """Evaluate compound test expression with && or ||."""
        left_result = self._evaluate_test_expression(expr.left)
        
        if expr.operator == '&&':
            # Short-circuit AND
            if not left_result:
                return False
            return self._evaluate_test_expression(expr.right)
        elif expr.operator == '||':
            # Short-circuit OR
            if left_result:
                return True
            return self._evaluate_test_expression(expr.right)
        else:
            raise ValueError(f"unknown compound operator: {expr.operator}")
    
    def _to_int(self, value: str) -> int:
        """Convert string to integer for numeric comparisons."""
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"integer expression expected: {value}")
    
    def _file_newer_than(self, file1: str, file2: str) -> bool:
        """Check if file1 is newer than file2."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return stat1.st_mtime > stat2.st_mtime
        except FileNotFoundError:
            return False
    
    def _file_older_than(self, file1: str, file2: str) -> bool:
        """Check if file1 is older than file2."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return stat1.st_mtime < stat2.st_mtime
        except FileNotFoundError:
            return False
    
    def _files_same(self, file1: str, file2: str) -> bool:
        """Check if two files are the same (same inode)."""
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            return (stat1.st_dev == stat2.st_dev and 
                    stat1.st_ino == stat2.st_ino)
        except FileNotFoundError:
            return False
    
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
        return self.script_manager.script_validator.is_binary_file(file_path)
    
    def _validate_script_file(self, script_path: str) -> int:
        """Validate script file and return appropriate exit code."""
        return self.script_manager.script_validator.validate_script_file(script_path)
    
    def run_script(self, script_path: str, script_args: list = None) -> int:
        """Execute a script file with optional arguments."""
        return self.script_manager.run_script(script_path, script_args)
    
    def _execute_from_source(self, input_source, add_to_history=True) -> int:
        """Execute commands from an input source with enhanced processing."""
        return self.script_manager.execute_from_source(input_source, add_to_history)
    
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
            
            # Increment command number for successful parse
            self.command_number += 1
            
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
        
        # Set up multi-line input handler
        multi_line_handler = MultiLineInputHandler(line_editor, self)
        
        while True:
            try:
                # Check for completed background jobs
                self.job_manager.notify_completed_jobs()
                
                # Check for stopped jobs (from Ctrl-Z)
                self.job_manager.notify_stopped_jobs()
                
                # Read command (possibly multi-line)
                command = multi_line_handler.read_command()
                
                if command is None:  # EOF (Ctrl-D)
                    print()  # New line before exit
                    break
                
                if command.strip():
                    self.run_command(command)
                    
            except KeyboardInterrupt:
                # Ctrl-C pressed, cancel multi-line input and continue
                multi_line_handler.reset()
                print("^C")
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
        """Parse shebang line from script file."""
        return self.script_manager.shebang_handler.parse_shebang(script_path)
    
    def _should_execute_with_shebang(self, script_path: str) -> bool:
        """Determine if script should be executed with its shebang interpreter."""
        return self.script_manager.shebang_handler.should_execute_with_shebang(script_path)
    
    def _execute_with_shebang(self, script_path: str, script_args: list) -> int:
        """Execute script using its shebang interpreter."""
        return self.script_manager.shebang_handler.execute_with_shebang(script_path, script_args)
    
    def _collect_heredocs(self, node):
        """Collect here document content for all commands in a node"""
        self.io_manager.collect_heredocs(node)
    
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
    
    def _load_rc_file(self):
        """Load ~/.pshrc or alternative RC file if it exists."""
        # Determine which RC file to load
        if self.rcfile:
            rc_file = os.path.expanduser(self.rcfile)
        else:
            rc_file = os.path.expanduser("~/.pshrc")
        
        # Check if file exists and is readable
        if os.path.isfile(rc_file) and os.access(rc_file, os.R_OK):
            # Check security before loading
            if not self._is_safe_rc_file(rc_file):
                print(f"psh: warning: {rc_file} has unsafe permissions, skipping", file=sys.stderr)
                return
            
            try:
                # Store current $0
                old_script_name = self.variables.get('0', self.script_name)
                self.variables['0'] = rc_file
                
                # Source the file without adding to history
                from .input_sources import FileInput
                with FileInput(rc_file) as input_source:
                    self._execute_from_source(input_source, add_to_history=False)
                
                # Restore $0
                self.variables['0'] = old_script_name
                
            except Exception as e:
                # Print warning but continue shell startup
                print(f"psh: warning: error loading {rc_file}: {e}", file=sys.stderr)
    
    def _is_safe_rc_file(self, filepath):
        """Check if RC file has safe permissions."""
        try:
            stat_info = os.stat(filepath)
            # Check if file is owned by user or root
            if stat_info.st_uid not in (os.getuid(), 0):
                return False
            # Check if file is world-writable
            if stat_info.st_mode & 0o002:
                return False
            return True
        except OSError:
            return False
    
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
        return self.io_manager.apply_redirections(redirects)
    
    def _restore_redirections(self, saved_fds: List[Tuple[int, int]]):
        """Restore file descriptors from saved list."""
        self.io_manager.restore_redirections(saved_fds)
    
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
        return ASTFormatter.format(node, indent)
    
    def _format_tokens(self, tokens):
        """Format token list for debugging output."""
        return TokenFormatter.format(tokens)
    
    def _setup_process_substitutions(self, command: Command) -> Tuple[List[int], List[str], List[int]]:
        """Set up process substitutions and return (fds, paths, child_pids)."""
        return self.io_manager.setup_process_substitutions(command)
    
    def _cleanup_process_substitutions(self):
        """Clean up process substitution file descriptors and wait for children."""
        self.io_manager.cleanup_process_substitutions()