import os
import sys
import subprocess
import readline
import signal
import glob
import pwd
import stat
from .tokenizer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, Pipeline, CommandList, AndOrList, Redirect, TopLevel, FunctionDef, IfStatement
from .line_editor import LineEditor
from .version import get_version_info
from .aliases import AliasManager
from .functions import FunctionManager
from .job_control import JobManager, JobState


class FunctionReturn(Exception):
    """Exception used to implement return from functions."""
    def __init__(self, exit_code):
        self.exit_code = exit_code
        super().__init__()


class Shell:
    def __init__(self, args=None, script_name=None):
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported to environment)
        self.positional_params = args if args else []  # $1, $2, etc.
        self.script_name = script_name or "psh"  # $0 value
        self.is_script_mode = script_name is not None and script_name != "psh"
        self.builtins = {
            'exit': self._builtin_exit,
            'cd': self._builtin_cd,
            'export': self._builtin_export,
            'pwd': self._builtin_pwd,
            'echo': self._builtin_echo,
            'env': self._builtin_env,
            'unset': self._builtin_unset,
            'source': self._builtin_source,
            '.': self._builtin_source,
            'history': self._builtin_history,
            'set': self._builtin_set,
            'version': self._builtin_version,
            'alias': self._builtin_alias,
            'unalias': self._builtin_unalias,
            'declare': self._builtin_declare,
            'return': self._builtin_return,
            'jobs': self._builtin_jobs,
            'fg': self._builtin_fg,
            'test': self._builtin_test,
            '[': self._builtin_test,
            'bg': self._builtin_bg,
            'true': self._builtin_true,
            'false': self._builtin_false,
        }
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
        """Expand variables in a string (for here strings)"""
        result = []
        i = 0
        while i < len(text):
            if text[i] == '$' and i + 1 < len(text):
                if text[i + 1] == '{':
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
            temp_shell = Shell()
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
    
    def _expand_arguments(self, command: Command) -> list:
        """Expand variables, command substitutions, tildes, and globs in command arguments"""
        args = []
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
            else:
                # Check if this is a STRING that might contain variables
                if arg_type == 'STRING' and '$' in arg:
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
        
        # This is a variable assignment
        var_name, var_value = args[0].split('=', 1)
        if len(args) == 1:
            # Pure assignment, no command
            # Expand tilde in the value
            if var_value.startswith('~'):
                var_value = self._expand_tilde(var_value)
            self.variables[var_name] = var_value
            return 0
        else:
            # Assignment followed by command - set temporarily
            # This is more complex, skip for now
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
    
    def _execute_builtin(self, args: list, command: Command) -> int:
        """Execute a built-in command with proper redirection handling"""
        stdin_backup, stdout_backup, stderr_backup = self._setup_builtin_redirections(command)
        try:
            return self.builtins[args[0]](args)
        except FunctionReturn:
            # Re-raise FunctionReturn to propagate it up
            raise
        finally:
            self._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
    
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
        
        # Check for variable assignments
        assignment_result = self._handle_variable_assignment(args)
        if assignment_result != -1:
            return assignment_result
        
        # Check for function call BEFORE builtin check
        func = self.function_manager.get_function(args[0])
        if func:
            return self._execute_function(func, args, command)
        
        # Execute built-in or external command
        if args[0] in self.builtins:
            try:
                return self._execute_builtin(args, command)
            except FunctionReturn:
                # Re-raise to propagate up to function execution
                raise
        else:
            return self._execute_external(args, command)
    
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
        if original_pgid is not None and not pipeline.commands[-1].background:
            self.foreground_pgid = pgid
            job.foreground = True
            self.job_manager.set_foreground_job(job)
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
        if not pipeline.commands[-1].background:
            # Foreground job - wait for it
            last_status = self.job_manager.wait_for_job(job)
            
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
            for and_or_list in command_list.and_or_lists:
                exit_code = self.execute_and_or_list(and_or_list)
                self.last_exit_code = exit_code
        except FunctionReturn:
            # Only catch FunctionReturn if we're in a function
            if self.function_stack:
                raise
            # Otherwise it's an error
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        return exit_code
    
    def execute_toplevel(self, toplevel: TopLevel):
        """Execute a top-level script/input containing functions and commands."""
        last_exit = 0
        
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
                # Execute if statement
                last_exit = self.execute_if_statement(item)
        
        self.last_exit_code = last_exit
        return last_exit
    
    def execute_if_statement(self, if_stmt: IfStatement) -> int:
        """Execute an if/then/else/fi conditional statement."""
        # Collect here documents for condition
        self._collect_heredocs(if_stmt.condition)
        
        # Execute the condition and check its exit status
        condition_exit = self.execute_command_list(if_stmt.condition)
        
        # In shell, condition is true if exit code is 0, false otherwise
        if condition_exit == 0:
            # Execute then part
            if if_stmt.then_part.and_or_lists:
                self._collect_heredocs(if_stmt.then_part)
                return self.execute_command_list(if_stmt.then_part)
            else:
                return 0
        else:
            # Execute else part if it exists
            if if_stmt.else_part and if_stmt.else_part.and_or_lists:
                self._collect_heredocs(if_stmt.else_part)
                return self.execute_command_list(if_stmt.else_part)
            else:
                return 0
    
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
            command_buffer += line
            
            # Execute the complete command
            if command_buffer.strip():
                exit_code = self._execute_buffered_command(
                    command_buffer, input_source, command_start_line, add_to_history
                )
            
            # Reset buffer for next command
            command_buffer = ""
            command_start_line = 0
        
        return exit_code
    
    def _execute_buffered_command(self, command_string: str, input_source, start_line: int, add_to_history: bool) -> int:
        """Execute a buffered command with enhanced error reporting."""
        # Skip empty commands and comments
        if not command_string.strip() or command_string.strip().startswith('#'):
            return 0
        
        try:
            tokens = tokenize(command_string)
            # Expand aliases
            tokens = self.alias_manager.expand_aliases(tokens)
            ast = parse(tokens)
            
            # Add to history if requested (for interactive or testing)
            if add_to_history and command_string.strip():
                self._add_to_history(command_string.strip())
            
            # Handle TopLevel AST node (functions + commands)
            if isinstance(ast, TopLevel):
                return self.execute_toplevel(ast)
            else:
                # Backward compatibility - CommandList
                # Collect here documents if any
                self._collect_heredocs(ast)
                exit_code = self.execute_command_list(ast)
                return exit_code
        except ParseError as e:
            # Enhanced error message with location
            location = input_source.get_location() if start_line == 0 else f"{input_source.get_name()}:{start_line}"
            print(f"psh: {location}: {e.message}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
        except Exception as e:
            # Enhanced error message with location  
            location = input_source.get_location() if start_line == 0 else f"{input_source.get_name()}:{start_line}"
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
    
    # Built-in commands
    def _builtin_exit(self, args):
        # Save history before exiting
        self._save_history()
        
        if len(args) > 1:
            try:
                exit_code = int(args[1])
            except ValueError:
                print(f"exit: {args[1]}: numeric argument required", file=sys.stderr)
                exit_code = 2
        else:
            exit_code = 0
        sys.exit(exit_code)
    
    def _builtin_cd(self, args):
        if len(args) > 1:
            path = args[1]
        else:
            path = os.environ.get('HOME', '/')
        
        try:
            os.chdir(path)
            return 0
        except FileNotFoundError:
            print(f"cd: {path}: No such file or directory", file=sys.stderr)
            return 1
        except NotADirectoryError:
            print(f"cd: {path}: Not a directory", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"cd: {path}: Permission denied", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1
    
    def _builtin_export(self, args):
        if len(args) == 1:
            # No arguments, print all exported variables
            for key, value in sorted(self.env.items()):
                print(f'export {key}="{value}"')
        else:
            for arg in args[1:]:
                if '=' in arg:
                    # Variable assignment
                    key, value = arg.split('=', 1)
                    self.env[key] = value
                    self.variables[key] = value
                else:
                    # Export existing variable
                    if arg in self.variables:
                        self.env[arg] = self.variables[arg]
        return 0
    
    def _builtin_pwd(self, args):
        print(os.getcwd())
        return 0
    
    def _builtin_echo(self, args):
        # Simple echo implementation
        if len(args) > 1:
            print(' '.join(args[1:]))
        else:
            print()
        return 0
    
    def _builtin_env(self, args):
        if len(args) == 1:
            # No arguments, print all environment variables
            for key, value in sorted(self.env.items()):
                print(f"{key}={value}")
        else:
            # Run command with modified environment (simplified)
            # For now, just print error
            print("env: running commands not yet implemented", file=sys.stderr)
            return 1
        return 0
    
    def _builtin_unset(self, args):
        if len(args) < 2:
            print("unset: not enough arguments", file=sys.stderr)
            return 1
        
        # Check for -f flag
        if '-f' in args:
            # Remove functions
            exit_code = 0
            for arg in args[1:]:
                if arg != '-f':
                    if not self.function_manager.undefine_function(arg):
                        print(f"unset: {arg}: not a function", file=sys.stderr)
                        exit_code = 1
            return exit_code
        else:
            # Remove variables
            for var in args[1:]:
                # Remove from both shell variables and environment
                self.variables.pop(var, None)
                self.env.pop(var, None)
            return 0
    
    def _builtin_source(self, args):
        """Enhanced source builtin with PATH search and argument support."""
        if len(args) < 2:
            print("source: filename argument required", file=sys.stderr)
            return 1
        
        filename = args[1]
        source_args = args[2:] if len(args) > 2 else []
        
        # Find the script file
        script_path = self._find_source_file(filename)
        if script_path is None:
            print(f"source: {filename}: No such file or directory", file=sys.stderr)
            return 1
        
        # Validate the script file
        validation_result = self._validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Save current shell state
        old_positional = self.positional_params.copy()
        old_script_name = self.script_name
        old_script_mode = self.is_script_mode
        
        # Set new state for sourced script
        self.positional_params = source_args
        self.script_name = script_path
        # Keep current script mode (sourcing inherits mode)
        
        try:
            from .input_sources import FileInput
            with FileInput(script_path) as input_source:
                # Execute with no history since it's sourced
                return self._execute_from_source(input_source, add_to_history=False)
        except Exception as e:
            print(f"source: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            # Restore previous state
            self.positional_params = old_positional
            self.script_name = old_script_name
            self.is_script_mode = old_script_mode
    
    def _find_source_file(self, filename: str) -> str:
        """Find a source file, searching PATH if needed."""
        # If filename contains a slash, don't search PATH
        if '/' in filename:
            if os.path.exists(filename):
                return filename
            return None
        
        # First check current directory
        if os.path.exists(filename):
            return filename
        
        # Search in PATH
        path_dirs = self.env.get('PATH', '').split(':')
        for path_dir in path_dirs:
            if path_dir:  # Skip empty path components
                full_path = os.path.join(path_dir, filename)
                if os.path.exists(full_path):
                    return full_path
        
        return None
    
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
    
    def _builtin_history(self, args):
        # Simple history implementation
        if len(args) > 1:
            try:
                count = int(args[1])
                start = max(0, len(self.history) - count)
                history_slice = self.history[start:]
            except ValueError:
                print(f"history: {args[1]}: numeric argument required", file=sys.stderr)
                return 1
        else:
            # Default to showing last 10 commands (bash behavior)
            count = 10
            start = max(0, len(self.history) - count)
            history_slice = self.history[start:]
        
        # Print with line numbers
        start_num = len(self.history) - len(history_slice) + 1
        for i, cmd in enumerate(history_slice):
            print(f"{start_num + i:5d}  {cmd}")
        return 0
    
    def _builtin_set(self, args):
        if len(args) == 1:
            # No arguments, display all variables
            # Show shell variables
            for var, value in sorted(self.variables.items()):
                print(f"{var}={value}")
            # Also show set options
            print(f"edit_mode={self.edit_mode}")
        elif len(args) >= 3 and args[1] == '-o':
            # Set option: set -o vi or set -o emacs
            option = args[2].lower()
            if option in ('vi', 'emacs'):
                self.edit_mode = option
                print(f"Edit mode set to {option}")
            else:
                print(f"psh: set: invalid option: {option}", file=sys.stderr)
                print("Valid options: vi, emacs", file=sys.stderr)
                return 1
        elif args[1] == '-o' and len(args) == 2:
            # Show current options
            print(f"edit_mode {self.edit_mode}")
        elif args[1] == '+o' and len(args) >= 3:
            # Unset option (for compatibility, we just set to emacs)
            option = args[2].lower()
            if option == 'vi':
                self.edit_mode = 'emacs'
                print("Edit mode set to emacs")
        else:
            # Set positional parameters
            self.positional_params = args[1:]
        return 0
    
    def _builtin_version(self, args):
        """Display version information"""
        if len(args) > 1 and args[1] == '--short':
            # Just print version number
            from .version import __version__
            print(__version__)
        else:
            # Full version info
            print(get_version_info())
        return 0
    
    def _builtin_alias(self, args):
        """Define or display aliases"""
        if len(args) == 1:
            # No arguments - list all aliases
            for name, value in sorted(self.alias_manager.list_aliases()):
                # Escape single quotes in value for display
                escaped_value = value.replace("'", "'\"'\"'")
                print(f"alias {name}='{escaped_value}'")
            return 0
        
        exit_code = 0
        
        # Process each argument
        i = 1
        while i < len(args):
            arg = args[i]
            
            if '=' in arg:
                # This looks like an assignment
                equals_pos = arg.index('=')
                name = arg[:equals_pos]
                value_start = arg[equals_pos + 1:]
                
                # Check if value starts with a quote
                if value_start and value_start[0] in ("'", '"'):
                    quote_char = value_start[0]
                    # Need to find the closing quote, which might be in later args
                    value_parts = [value_start[1:]]  # Remove opening quote
                    
                    # Look for closing quote
                    found_close = False
                    j = i
                    
                    # Check if closing quote is in the same arg
                    if value_start[1:].endswith(quote_char):
                        value = value_start[1:-1]
                        found_close = True
                    else:
                        # Look in subsequent args
                        j = i + 1
                        while j < len(args):
                            if args[j].endswith(quote_char):
                                value_parts.append(args[j][:-1])  # Remove closing quote
                                found_close = True
                                break
                            else:
                                value_parts.append(args[j])
                            j += 1
                        
                        if found_close:
                            value = ' '.join(value_parts)
                            i = j  # Skip the args we consumed
                        else:
                            # No closing quote found
                            value = value_start
                else:
                    # No quotes, just use the value as is
                    value = value_start
                
                try:
                    self.alias_manager.define_alias(name, value)
                except ValueError as e:
                    print(f"psh: alias: {e}", file=sys.stderr)
                    exit_code = 1
            else:
                # Show specific alias
                value = self.alias_manager.get_alias(arg)
                if value is not None:
                    # Escape single quotes in value for display
                    escaped_value = value.replace("'", "'\"'\"'")
                    print(f"alias {arg}='{escaped_value}'")
                else:
                    print(f"psh: alias: {arg}: not found", file=sys.stderr)
                    exit_code = 1
            
            i += 1
        
        return exit_code
    
    def _builtin_unalias(self, args):
        """Remove aliases"""
        if len(args) == 1:
            print("unalias: usage: unalias [-a] name [name ...]", file=sys.stderr)
            return 1
        
        if args[1] == '-a':
            # Remove all aliases
            self.alias_manager.clear_aliases()
            return 0
        
        exit_code = 0
        for name in args[1:]:
            if not self.alias_manager.undefine_alias(name):
                print(f"psh: unalias: {name}: not found", file=sys.stderr)
                exit_code = 1
        
        return exit_code
    
    def _builtin_declare(self, args):
        """Declare variables and functions."""
        if '-f' in args:
            if len(args) == 2:  # declare -f
                # List all functions
                for name, func in self.function_manager.list_functions():
                    self._print_function_definition(name, func)
            else:  # declare -f name
                for arg in args[2:]:
                    func = self.function_manager.get_function(arg)
                    if func:
                        self._print_function_definition(arg, func)
                    else:
                        print(f"psh: declare: {arg}: not found", file=sys.stderr)
                        return 1
        else:
            # For now, just list variables (like set with no args)
            for var, value in sorted(self.variables.items()):
                print(f"{var}={value}")
        return 0
    
    def _print_function_definition(self, name, func):
        """Print a function definition in a format that can be re-executed."""
        print(f"{name} () {{")
        # We need to pretty-print the function body
        # For now, just indicate it's defined
        print(f"    # function body")
        print("}")
    
    def _builtin_return(self, args):
        """Return from a function with optional exit code."""
        if not self.function_stack:
            print("return: can only `return' from a function or sourced script", file=sys.stderr)
            return 1
        
        # Get return value
        if len(args) > 1:
            try:
                exit_code = int(args[1])
                # Ensure it's in valid range
                if exit_code < 0 or exit_code > 255:
                    print(f"return: {args[1]}: numeric argument required", file=sys.stderr)
                    return 1
            except ValueError:
                print(f"return: {args[1]}: numeric argument required", file=sys.stderr)
                return 1
        else:
            exit_code = 0
        
        # We can't actually "return" from the middle of execution in Python,
        # so we'll use an exception for control flow
        raise FunctionReturn(exit_code)
    
    def _builtin_jobs(self, args):
        """List active jobs."""
        for line in self.job_manager.list_jobs():
            print(line)
        return 0
    
    def _builtin_fg(self, args):
        """Bring job to foreground."""
        job_spec = args[1] if len(args) > 1 else '%+'
        job = self.job_manager.parse_job_spec(job_spec)
        
        if not job:
            print(f"fg: {job_spec}: no such job", file=sys.stderr)
            return 1
        
        # Print job info
        print(job.command)
        
        # Give it terminal control FIRST before sending SIGCONT
        self.job_manager.set_foreground_job(job)
        job.foreground = True
        try:
            os.tcsetpgrp(0, job.pgid)
        except OSError as e:
            print(f"fg: can't set terminal control: {e}", file=sys.stderr)
            return 1
        
        # Continue stopped job
        if job.state.value == 'stopped':
            # Mark processes as running again
            for proc in job.processes:
                if proc.stopped:
                    proc.stopped = False
            job.state = JobState.RUNNING
            
            # Send SIGCONT to the process group
            os.killpg(job.pgid, signal.SIGCONT)
        
        # Wait for it
        exit_status = self.job_manager.wait_for_job(job)
        
        # Restore terminal control to shell
        try:
            os.tcsetpgrp(0, os.getpgrp())
        except OSError:
            pass
        
        # Remove job if completed
        if job.state == JobState.DONE:
            self.job_manager.remove_job(job.job_id)
        
        return exit_status
    
    def _builtin_bg(self, args):
        """Resume job in background."""
        job_spec = args[1] if len(args) > 1 else '%+'
        job = self.job_manager.parse_job_spec(job_spec)
        
        if not job:
            print(f"bg: {job_spec}: no such job", file=sys.stderr)
            return 1
        
        if job.state.value == 'stopped':
            # Mark processes as running again
            for proc in job.processes:
                if proc.stopped:
                    proc.stopped = False
            job.state = JobState.RUNNING
            job.foreground = False
            
            # Send SIGCONT to resume
            os.killpg(job.pgid, signal.SIGCONT)
            print(f"[{job.job_id}]+ {job.command} &")
        return 0
    
    def _builtin_test(self, args):
        """Implement test command for conditionals."""
        if args[0] == '[':
            # For [ command, last argument must be ]
            if len(args) < 2 or args[-1] != ']':
                return 2  # Syntax error
            args = args[1:-1]  # Remove [ and ]
        else:
            args = args[1:]  # Remove 'test'
        
        if len(args) == 0:
            return 1  # False
        
        if len(args) == 1:
            # Single argument - true if non-empty string
            return 0 if args[0] else 1
        
        if len(args) == 2:
            # Unary operators
            op, arg = args
            if op == '-z':
                # True if string is empty
                return 0 if not arg else 1
            elif op == '-n':
                # True if string is non-empty
                return 0 if arg else 1
            elif op == '-f':
                # True if file exists and is regular file
                return 0 if os.path.isfile(arg) else 1
            elif op == '-d':
                # True if file exists and is directory
                return 0 if os.path.isdir(arg) else 1
            elif op == '-e':
                # True if file exists
                return 0 if os.path.exists(arg) else 1
            elif op == '-r':
                # True if file is readable
                return 0 if os.path.isfile(arg) and os.access(arg, os.R_OK) else 1
            elif op == '-w':
                # True if file is writable
                return 0 if os.path.isfile(arg) and os.access(arg, os.W_OK) else 1
            elif op == '-x':
                # True if file is executable
                return 0 if os.path.isfile(arg) and os.access(arg, os.X_OK) else 1
            elif op == '-s':
                # True if file exists and has size > 0
                try:
                    return 0 if os.path.isfile(arg) and os.path.getsize(arg) > 0 else 1
                except (OSError, IOError):
                    return 1
            elif op == '-L' or op == '-h':
                # True if file exists and is a symbolic link
                return 0 if os.path.islink(arg) else 1
            elif op == '-b':
                # True if file exists and is a block device
                try:
                    st = os.stat(arg)
                    return 0 if stat.S_ISBLK(st.st_mode) else 1
                except (OSError, IOError):
                    return 1
            elif op == '-c':
                # True if file exists and is a character device
                try:
                    st = os.stat(arg)
                    return 0 if stat.S_ISCHR(st.st_mode) else 1
                except (OSError, IOError):
                    return 1
            elif op == '-p':
                # True if file exists and is a named pipe (FIFO)
                try:
                    st = os.stat(arg)
                    return 0 if stat.S_ISFIFO(st.st_mode) else 1
                except (OSError, IOError):
                    return 1
            elif op == '-S':
                # True if file exists and is a socket
                try:
                    st = os.stat(arg)
                    return 0 if stat.S_ISSOCK(st.st_mode) else 1
                except (OSError, IOError):
                    return 1
            elif op == '-k':
                # True if file has sticky bit set
                try:
                    st = os.stat(arg)
                    return 0 if st.st_mode & stat.S_ISVTX else 1
                except (OSError, IOError):
                    return 1
            elif op == '-u':
                # True if file has setuid bit set
                try:
                    st = os.stat(arg)
                    return 0 if st.st_mode & stat.S_ISUID else 1
                except (OSError, IOError):
                    return 1
            elif op == '-g':
                # True if file has setgid bit set
                try:
                    st = os.stat(arg)
                    return 0 if st.st_mode & stat.S_ISGID else 1
                except (OSError, IOError):
                    return 1
            elif op == '-O':
                # True if file is owned by effective user ID
                try:
                    st = os.stat(arg)
                    return 0 if st.st_uid == os.geteuid() else 1
                except (OSError, IOError):
                    return 1
            elif op == '-G':
                # True if file is owned by effective group ID
                try:
                    st = os.stat(arg)
                    return 0 if st.st_gid == os.getegid() else 1
                except (OSError, IOError):
                    return 1
            elif op == '-N':
                # True if file was modified since it was last read
                try:
                    st = os.stat(arg)
                    return 0 if st.st_mtime > st.st_atime else 1
                except (OSError, IOError):
                    return 1
            elif op == '-t':
                # True if file descriptor is open and refers to a terminal
                try:
                    fd = int(arg)
                    return 0 if os.isatty(fd) else 1
                except (ValueError, OSError):
                    return 1
            else:
                return 2  # Unknown operator
        
        if len(args) == 3:
            # Binary operators
            arg1, op, arg2 = args
            if op == '=':
                return 0 if arg1 == arg2 else 1
            elif op == '!=':
                return 0 if arg1 != arg2 else 1
            elif op == '-eq':
                try:
                    return 0 if int(arg1) == int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-ne':
                try:
                    return 0 if int(arg1) != int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-lt':
                try:
                    return 0 if int(arg1) < int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-le':
                try:
                    return 0 if int(arg1) <= int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-gt':
                try:
                    return 0 if int(arg1) > int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-ge':
                try:
                    return 0 if int(arg1) >= int(arg2) else 1
                except ValueError:
                    return 2
            elif op == '-nt':
                # True if file1 is newer than file2 (modification time)
                try:
                    stat1 = os.stat(arg1)
                    stat2 = os.stat(arg2)
                    return 0 if stat1.st_mtime > stat2.st_mtime else 1
                except (OSError, IOError):
                    return 1
            elif op == '-ot':
                # True if file1 is older than file2 (modification time)
                try:
                    stat1 = os.stat(arg1)
                    stat2 = os.stat(arg2)
                    return 0 if stat1.st_mtime < stat2.st_mtime else 1
                except (OSError, IOError):
                    return 1
            elif op == '-ef':
                # True if file1 and file2 refer to the same file (same device and inode)
                try:
                    stat1 = os.stat(arg1)
                    stat2 = os.stat(arg2)
                    return 0 if (stat1.st_dev == stat2.st_dev and stat1.st_ino == stat2.st_ino) else 1
                except (OSError, IOError):
                    return 1
            else:
                return 2  # Unknown operator
        
        # More complex expressions not implemented yet
        return 2
    
    def _builtin_true(self, args):
        """Always return success (exit code 0)."""
        return 0
    
    def _builtin_false(self, args):
        """Always return failure (exit code 1)."""
        return 1
    
    def _collect_heredocs(self, command_list: CommandList):
        """Collect here document content for all commands"""
        for and_or_list in command_list.and_or_lists:
            for pipeline in and_or_list.pipelines:
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
                        # Stopped foreground job
                        print(f"\n[{job.job_id}]+  Stopped                 {job.command}")
                        # Return control to shell
                        try:
                            os.tcsetpgrp(0, os.getpgrp())
                        except OSError:
                            pass
                        self.job_manager.set_foreground_job(None)
                        job.foreground = False
            except OSError:
                break
    
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
        
        # Check for built-in commands
        if args[0] in self.builtins:
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