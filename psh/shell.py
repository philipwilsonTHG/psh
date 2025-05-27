import os
import sys
import subprocess
import readline
import signal
import glob
import pwd
from .tokenizer import tokenize
from .parser import parse, ParseError
from .ast_nodes import Command, Pipeline, CommandList, AndOrList, Redirect
from .line_editor import LineEditor
from .version import get_version_info


class Shell:
    def __init__(self, args=None):
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported to environment)
        self.positional_params = args if args else []  # $1, $2, etc.
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
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Ignore Ctrl-Z in shell
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Ignore terminal output stops
    
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
            return 'psh'  # Shell name
        elif var_name == '@':
            # Expand to separate words
            return ' '.join(f'"{param}"' for param in self.positional_params)
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
    
    def _setup_external_redirections(self, command: Command):
        """Set up redirections for external commands. Returns file handles."""
        stdin = None
        stdout = None
        stderr = None
        
        for redirect in command.redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self._expand_tilde(target)
            
            if redirect.type == '<':
                stdin = open(target, 'r')
            elif redirect.type in ('<<', '<<-'):
                # For heredocs, we need to use PIPE and write content
                stdin = subprocess.PIPE
            elif redirect.type == '<<<':
                # For here strings, we also use PIPE
                stdin = subprocess.PIPE
            elif redirect.type == '>' and redirect.fd == 2:
                stderr = open(target, 'w')
            elif redirect.type == '>>' and redirect.fd == 2:
                stderr = open(target, 'a')
            elif redirect.type == '>' and (redirect.fd is None or redirect.fd == 1):
                stdout = open(target, 'w')
            elif redirect.type == '>>' and (redirect.fd is None or redirect.fd == 1):
                stdout = open(target, 'a')
            elif redirect.type == '>&':
                # Handle fd duplication like 2>&1
                if redirect.fd == 2 and redirect.dup_fd == 1:
                    stderr = subprocess.STDOUT
        
        return stdin, stdout, stderr
    
    def _close_external_redirections(self, stdin, stdout, stderr):
        """Close file handles opened for external command redirections"""
        if stdin and stdin != sys.stdin and stdin != subprocess.PIPE:
            stdin.close()
        if stdout and stdout != sys.stdout and stdout != subprocess.PIPE and stdout != subprocess.STDOUT:
            stdout.close()
        if stderr and stderr != sys.stderr and stderr != subprocess.PIPE and stderr != subprocess.STDOUT:
            stderr.close()
    
    def _execute_builtin(self, args: list, command: Command) -> int:
        """Execute a built-in command with proper redirection handling"""
        stdin_backup, stdout_backup, stderr_backup = self._setup_builtin_redirections(command)
        try:
            return self.builtins[args[0]](args)
        finally:
            self._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
    
    def _execute_external(self, args: list, command: Command) -> int:
        """Execute an external command with proper redirection and process handling"""
        stdin, stdout, stderr = self._setup_external_redirections(command)
        
        try:
            # Run the command
            proc = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=self.env
            )
            
            # Write heredoc/here string content if using PIPE
            if stdin == subprocess.PIPE:
                for redirect in command.redirects:
                    if redirect.type in ('<<', '<<-'):
                        # Write content even if empty (empty heredoc is valid)
                        content = redirect.heredoc_content or ''
                        proc.stdin.write(content.encode())
                        proc.stdin.close()
                        break
                    elif redirect.type == '<<<':
                        # Write here string content with newline
                        content = redirect.target + '\n'
                        proc.stdin.write(content.encode())
                        proc.stdin.close()
                        break
            
            if command.background:
                print(f"[{proc.pid}]")
                self.last_bg_pid = proc.pid
                return 0
            else:
                proc.wait()
                # Handle signal termination
                if proc.returncode < 0:
                    # Process was killed by signal
                    return 128 + abs(proc.returncode)
                return proc.returncode
        
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1
        finally:
            self._close_external_redirections(stdin, stdout, stderr)
    
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
        
        # Execute built-in or external command
        if args[0] in self.builtins:
            return self._execute_builtin(args, command)
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
    
    def execute_pipeline(self, pipeline: Pipeline):
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            return self.execute_command(pipeline.commands[0])
        
        # Execute pipeline using fork and pipe
        num_commands = len(pipeline.commands)
        pipes = []
        pids = []
        pgid = None
        
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
        
        # Give terminal control to the pipeline
        if original_pgid is not None and not pipeline.commands[-1].background:
            self.foreground_pgid = pgid
            try:
                os.tcsetpgrp(0, pgid)
            except:
                pass
        
        # Parent: Close all pipes
        for pipe_read, pipe_write in pipes:
            os.close(pipe_read)
            os.close(pipe_write)
        
        # Wait for all children and get exit status
        last_status = self._wait_for_pipeline(pids)
        
        # Restore terminal control
        if original_pgid is not None and not pipeline.commands[-1].background:
            self.foreground_pgid = None
            try:
                os.tcsetpgrp(0, original_pgid)
            except:
                pass
        
        return last_status
    
    def execute_and_or_list(self, and_or_list: AndOrList):
        """Execute pipelines with && and || operators, implementing short-circuit evaluation"""
        if not and_or_list.pipelines:
            return 0
        
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
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        for and_or_list in command_list.and_or_lists:
            exit_code = self.execute_and_or_list(and_or_list)
            self.last_exit_code = exit_code
        return exit_code
    
    def run_command(self, command_string: str, add_to_history=True):
        # Add to history if not empty and add_to_history is True
        if add_to_history and command_string.strip():
            self._add_to_history(command_string.strip())
        
        try:
            tokens = tokenize(command_string)
            ast = parse(tokens)
            
            # Collect here documents if any
            self._collect_heredocs(ast)
            
            exit_code = self.execute_command_list(ast)
            return exit_code
        except ParseError as e:
            print(f"psh: {e}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
        except Exception as e:
            print(f"psh: unexpected error: {e}", file=sys.stderr)
            self.last_exit_code = 1
            return 1
    
    def interactive_loop(self):
        # Set up readline for better line editing
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims(' \t\n;|&<>')
        
        # Set up tab completion with current edit mode
        line_editor = LineEditor(self.history, edit_mode=self.edit_mode)
        
        while True:
            try:
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
        
        for var in args[1:]:
            # Remove from both shell variables and environment
            self.variables.pop(var, None)
            self.env.pop(var, None)
        return 0
    
    def _builtin_source(self, args):
        if len(args) < 2:
            print("source: filename argument required", file=sys.stderr)
            return 1
        
        filename = args[1]
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Don't add source commands to history
                        self.run_command(line, add_to_history=False)
            return 0
        except FileNotFoundError:
            print(f"source: {filename}: No such file or directory", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"source: {filename}: {e}", file=sys.stderr)
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
        
        # Check for built-in commands
        if args[0] in self.builtins:
            try:
                return self.builtins[args[0]](args)
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