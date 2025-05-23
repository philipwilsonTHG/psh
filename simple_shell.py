#!/usr/bin/env python3

import os
import sys
import subprocess
import readline
import signal
import glob
from tokenizer import tokenize
from parser import parse, ParseError
from ast_nodes import Command, Pipeline, CommandList, Redirect
from tab_completion import LineEditor


class Shell:
    def __init__(self, args=None):
        self.env = os.environ.copy()
        self.variables = {}  # Shell variables (not exported to environment)
        self.positional_params = args if args else []  # $1, $2, etc.
        self.last_exit_code = 0
        self.last_bg_pid = None  # For $!
        self.history = []
        self.history_file = os.path.expanduser("~/.psh_history")
        self.max_history_size = 1000
        self.foreground_pgid = None  # Track foreground process group
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        # Load history from file
        self._load_history()
        
        # Built-in command dispatch table
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
            'cat': self._builtin_cat,
        }
    
    def _expand_variable(self, var_expr: str) -> str:
        """Expand a variable expression starting with $"""
        if not var_expr.startswith('$'):
            return var_expr
            
        var_name = var_expr[1:]
        
        # Handle ${var} and ${var:-default} syntax
        if var_name.startswith('{') and var_name.endswith('}'):
            var_content = var_name[1:-1]
            if ':-' in var_content:
                # ${var:-default} - use default if var is unset or empty
                var_name, default = var_content.split(':-', 1)
                value = self._get_variable_value(var_name)
                return value if value else default
            else:
                # ${var} - simple expansion
                var_name = var_content
        
        # Handle special variables
        if var_name == '?':
            return str(self.last_exit_code)
        elif var_name == '$':
            return str(os.getpid())
        elif var_name == '!':
            return str(self.last_bg_pid) if self.last_bg_pid else ''
        elif var_name == '#':
            return str(len(self.positional_params))
        elif var_name == '@':
            # $@ expands to separate words
            return ' '.join(f'"{param}"' for param in self.positional_params)
        elif var_name == '*':
            # $* expands to a single word
            return ' '.join(self.positional_params)
        elif var_name == '0':
            # $0 is the shell name
            return 'psh'
        elif var_name.isdigit():
            # Positional parameters
            index = int(var_name) - 1
            if 0 <= index < len(self.positional_params):
                return self.positional_params[index]
            return ''
        else:
            return self._get_variable_value(var_name)
    
    def _get_variable_value(self, var_name: str) -> str:
        """Get value of a variable from shell variables or environment"""
        # Check shell variables first, then environment
        if var_name in self.variables:
            return self.variables[var_name]
        return self.env.get(var_name, '')
    
    def _execute_command_substitution(self, cmd_sub: str) -> str:
        """Execute a command substitution and return its output"""
        # Extract command from $(...) or `...`
        if cmd_sub.startswith('$(') and cmd_sub.endswith(')'):
            command = cmd_sub[2:-1]
        elif cmd_sub.startswith('`') and cmd_sub.endswith('`'):
            command = cmd_sub[1:-1]
        else:
            return cmd_sub  # Invalid format, return as-is
        
        # Execute the command in a subprocess
        try:
            # Create a new shell instance in the subprocess with current positional params
            shell_cmd = [sys.executable, __file__, "-c", command]
            # Pass positional parameters as additional arguments
            if self.positional_params:
                shell_cmd.extend(self.positional_params)
            
            # Merge shell variables into environment for subprocess
            sub_env = self.env.copy()
            sub_env.update(self.variables)
            
            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                env=sub_env,
                cwd=os.getcwd()
            )
            
            # Update exit status
            self.last_exit_code = result.returncode
            
            # POSIX: strip only trailing newlines
            output = result.stdout.rstrip('\n')
            
            return output
        except Exception:
            # If execution fails, return empty string
            self.last_exit_code = 1
            return ''
    
    def execute_command(self, command: Command):
        # Expand variables and globs in arguments
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
        
        if not args:
            return 0
        # Check for variable assignments (VAR=value)
        if '=' in args[0] and not args[0].startswith('='):
            # This is a variable assignment
            var_name, var_value = args[0].split('=', 1)
            if len(args) == 1:
                # Pure assignment, no command
                self.variables[var_name] = var_value
                return 0
            else:
                # Assignment followed by command - set temporarily
                # This is more complex, skip for now
                pass
        
        
        # Check for built-in commands
        if args[0] in self.builtins:
            # Handle redirections for built-ins
            stdout_backup = None
            stderr_backup = None
            stdin_backup = None
            try:
                for redirect in command.redirects:
                    if redirect.type == '<':
                        stdin_backup = sys.stdin
                        sys.stdin = open(redirect.target, 'r')
                    elif redirect.type in ('<<', '<<-'):
                        stdin_backup = sys.stdin
                        # Create a StringIO object from heredoc content
                        import io
                        sys.stdin = io.StringIO(redirect.heredoc_content or '')
                    elif redirect.type == '>' and redirect.fd == 2:
                        stderr_backup = sys.stderr
                        sys.stderr = open(redirect.target, 'w')
                    elif redirect.type == '>>' and redirect.fd == 2:
                        stderr_backup = sys.stderr
                        sys.stderr = open(redirect.target, 'a')
                    elif redirect.type == '>' and (redirect.fd is None or redirect.fd == 1):
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'w')
                    elif redirect.type == '>>' and (redirect.fd is None or redirect.fd == 1):
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'a')
                    elif redirect.type == '>&':
                        # Handle fd duplication like 2>&1
                        if redirect.fd == 2 and redirect.dup_fd == 1:
                            stderr_backup = sys.stderr
                            sys.stderr = sys.stdout
                
                return self.builtins[args[0]](args)
            finally:
                # Restore original stdin/stdout/stderr
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
        
        # Execute external command
        try:
            # Set up redirections
            stdin = None
            stdout = None
            stderr = None
            
            for redirect in command.redirects:
                if redirect.type == '<':
                    stdin = open(redirect.target, 'r')
                elif redirect.type in ('<<', '<<-'):
                    # For heredocs, we need to use PIPE and write content
                    stdin = subprocess.PIPE
                elif redirect.type == '>' and redirect.fd == 2:
                    stderr = open(redirect.target, 'w')
                elif redirect.type == '>>' and redirect.fd == 2:
                    stderr = open(redirect.target, 'a')
                elif redirect.type == '>' and (redirect.fd is None or redirect.fd == 1):
                    stdout = open(redirect.target, 'w')
                elif redirect.type == '>>' and (redirect.fd is None or redirect.fd == 1):
                    stdout = open(redirect.target, 'a')
                elif redirect.type == '>&':
                    # Handle fd duplication like 2>&1
                    if redirect.fd == 2 and redirect.dup_fd == 1:
                        stderr = subprocess.STDOUT
            
            # Run the command
            proc = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=self.env
            )
            
            # Write heredoc content if using PIPE
            if stdin == subprocess.PIPE:
                for redirect in command.redirects:
                    if redirect.type in ('<<', '<<-') and redirect.heredoc_content:
                        proc.stdin.write(redirect.heredoc_content.encode())
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
            # Close any opened files
            if stdin and stdin != sys.stdin and stdin != subprocess.PIPE:
                stdin.close()
            if stdout and stdout != sys.stdout and stdout != subprocess.PIPE and stdout != subprocess.STDOUT:
                stdout.close()
            if stderr and stderr != sys.stderr and stderr != subprocess.PIPE and stderr != subprocess.STDOUT:
                stderr.close()
    
    def execute_pipeline(self, pipeline: Pipeline):
        if len(pipeline.commands) == 1:
            # Simple command, no pipes
            return self.execute_command(pipeline.commands[0])
        
        # Execute pipeline using fork and pipe
        num_commands = len(pipeline.commands)
        pipes = []
        pids = []
        
        # Create a new process group for the pipeline
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
        
        for i, command in enumerate(pipeline.commands):
            pid = os.fork()
            
            if pid == 0:  # Child process
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
                if i > 0:  # Not first command - read from previous pipe
                    os.dup2(pipes[i-1][0], 0)  # stdin = pipe_read
                    
                if i < num_commands - 1:  # Not last command - write to next pipe
                    os.dup2(pipes[i][1], 1)  # stdout = pipe_write
                
                # Close all pipe file descriptors
                for pipe_read, pipe_write in pipes:
                    os.close(pipe_read)
                    os.close(pipe_write)
                
                # Execute the command
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
        
        # Wait for all children and get exit status of last command
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
        
        # Restore terminal control
        if original_pgid is not None and not pipeline.commands[-1].background:
            self.foreground_pgid = None
            try:
                os.tcsetpgrp(0, original_pgid)
            except:
                pass
        
        return last_status
    
    def execute_command_list(self, command_list: CommandList):
        exit_code = 0
        for pipeline in command_list.pipelines:
            exit_code = self.execute_pipeline(pipeline)
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
        print("Python Shell (psh) - Educational Unix Shell")
        print("Type 'exit' to quit")
        
        # Use LineEditor if terminal supports it, otherwise fall back to input()
        if sys.stdin.isatty():
            line_editor = LineEditor(self.history)
        else:
            line_editor = None
        
        while True:
            try:
                # Prompt with exit status indicator
                if self.last_exit_code != 0:
                    prompt = f"[{self.last_exit_code}] {os.getcwd()}$ "
                else:
                    prompt = f"{os.getcwd()}$ "
                
                # Get command using LineEditor or input()
                if line_editor:
                    command = line_editor.read_line(prompt)
                    if command is None:  # EOF
                        print("\nexit")
                        self._save_history()
                        break
                else:
                    command = input(prompt)
                
                if command.strip():
                    self.run_command(command)
                    # Print a newline-check marker like zsh does
                    if line_editor and sys.stdout.isatty():
                        # Print reverse-video % and newline to ensure clean prompt
                        sys.stdout.write('\033[7m%\033[0m\n')
                        sys.stdout.flush()
            
            except EOFError:
                print("\nexit")
                self._save_history()
                break
            except KeyboardInterrupt:
                if not line_editor:
                    print("^C")
                continue
    
    # Built-in command implementations
    def _builtin_exit(self, args):
        exit_code = int(args[1]) if len(args) > 1 else 0
        self._save_history()
        sys.exit(exit_code)
    
    def _builtin_cd(self, args):
        try:
            path = args[1] if len(args) > 1 else os.environ.get('HOME', '/')
            os.chdir(path)
            return 0
        except OSError as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1
    
    def _builtin_export(self, args):
        if len(args) > 1:
            if '=' in args[1]:
                var, value = args[1].split('=', 1)
                self.env[var] = value
                os.environ[var] = value
                # Also update shell variable
                self.variables[var] = value
            else:
                # Export existing shell variable
                var = args[1]
                if var in self.variables:
                    self.env[var] = self.variables[var]
                    os.environ[var] = self.variables[var]
        return 0
    
    def _builtin_pwd(self, args):
        print(os.getcwd())
        sys.stdout.flush()
        return 0
    
    def _builtin_echo(self, args):
        # Join args with spaces, handling empty args list
        # Simple implementation - doesn't handle -e flag
        output = ' '.join(args[1:])
        print(output)
        sys.stdout.flush()
        return 0
    
    def _builtin_env(self, args):
        # Print all environment variables
        for key, value in sorted(self.env.items()):
            print(f"{key}={value}")
        return 0
    
    def _builtin_unset(self, args):
        # Remove environment variables
        for var in args[1:]:
            self.env.pop(var, None)
            os.environ.pop(var, None)
        return 0
    
    def _builtin_source(self, args):
        if len(args) < 2:
            print(f"{args[0]}: filename argument required", file=sys.stderr)
            return 1
        try:
            with open(args[1], 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.run_command(line, add_to_history=False)
            return 0
        except FileNotFoundError:
            print(f"{args[0]}: {args[1]}: No such file or directory", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"{args[0]}: {args[1]}: {e}", file=sys.stderr)
            return 1
    
    def _builtin_history(self, args):
        """Display command history"""
        # Parse arguments
        show_count = 10  # Default
        if len(args) > 1:
            try:
                show_count = int(args[1])
            except ValueError:
                print(f"history: {args[1]}: numeric argument required", file=sys.stderr)
                return 1
        
        # Show last N commands
        start_idx = max(0, len(self.history) - show_count)
        for i in range(start_idx, len(self.history)):
            print(f"{i + 1:5d}  {self.history[i]}")
        return 0
    
    def _builtin_set(self, args):
        """Set positional parameters"""
        if len(args) > 1:
            # Set positional parameters to the arguments after 'set'
            self.positional_params = args[1:]
        else:
            # No arguments, show all variables
            # Show shell variables
            for var, value in sorted(self.variables.items()):
                print(f"{var}={value}")
        return 0
    
    def _builtin_cat(self, args):
        """Simple cat implementation for testing"""
        try:
            # If no args, read from stdin
            if len(args) == 1:
                for line in sys.stdin:
                    print(line, end='')
            else:
                # Read from files
                for filename in args[1:]:
                    with open(filename, 'r') as f:
                        for line in f:
                            print(line, end='')
        except Exception as e:
            print(f"cat: {e}", file=sys.stderr)
            return 1
        sys.stdout.flush()
        return 0
    
    def _collect_heredocs(self, command_list: CommandList):
        """Collect here document content for all commands"""
        for pipeline in command_list.pipelines:
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
        """Load history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.history = [line.rstrip('\n') for line in f]
                    # Trim to max size
                    if len(self.history) > self.max_history_size:
                        self.history = self.history[-self.max_history_size:]
                
                # Load into readline
                readline.clear_history()
                for cmd in self.history:
                    readline.add_history(cmd)
        except Exception:
            # Silently ignore history file errors
            pass
    
    def _save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w') as f:
                for cmd in self.history:
                    f.write(cmd + '\n')
        except Exception:
            # Silently ignore history file errors
            pass
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for the shell"""
        # Ignore SIGTTOU - we handle terminal control ourselves
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        
        # Handle SIGINT (Ctrl-C)
        signal.signal(signal.SIGINT, self._handle_sigint)
        
        # Handle SIGTSTP (Ctrl-Z) - for now, ignore it
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    
    def _handle_sigint(self, signum, frame):
        """Handle SIGINT (Ctrl-C)"""
        # If there's a foreground process group, it will handle the signal
        # We just need to print a newline for the prompt
        print()
        # The signal will be delivered to the foreground process group
        # which is set in execute_pipeline
    
    def _execute_in_child(self, command: Command):
        """Execute a command in a child process (after fork)"""
        # Expand variables and globs in arguments
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
        
        if not args:
            return 0
        
        # Check for built-in commands
        if args[0] in self.builtins:
            # Handle redirections for built-ins
            try:
                for redirect in command.redirects:
                    if redirect.type == '<':
                        fd = os.open(redirect.target, os.O_RDONLY)
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
                    elif redirect.type == '>':
                        fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        target_fd = redirect.fd if redirect.fd is not None else 1
                        os.dup2(fd, target_fd)
                        os.close(fd)
                    elif redirect.type == '>>':
                        fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                        target_fd = redirect.fd if redirect.fd is not None else 1
                        os.dup2(fd, target_fd)
                        os.close(fd)
                    elif redirect.type == '>&':
                        # Handle fd duplication like 2>&1
                        if redirect.fd is not None and redirect.dup_fd is not None:
                            os.dup2(redirect.dup_fd, redirect.fd)
                
                return self.builtins[args[0]](args)
            except Exception as e:
                print(f"{args[0]}: {e}", file=sys.stderr)
                return 1
        
        # Execute external command
        try:
            # Set up redirections
            for redirect in command.redirects:
                if redirect.type == '<':
                    fd = os.open(redirect.target, os.O_RDONLY)
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
                elif redirect.type == '>':
                    fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                    target_fd = redirect.fd if redirect.fd is not None else 1
                    os.dup2(fd, target_fd)
                    os.close(fd)
                elif redirect.type == '>>':
                    fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                    target_fd = redirect.fd if redirect.fd is not None else 1
                    os.dup2(fd, target_fd)
                    os.close(fd)
                elif redirect.type == '>&':
                    # Handle fd duplication like 2>&1
                    if redirect.fd is not None and redirect.dup_fd is not None:
                        os.dup2(redirect.dup_fd, redirect.fd)
            
            # Execute with execvpe to pass environment
            os.execvpe(args[0], args, self.env)
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"{args[0]}: {e}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    shell = Shell()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c" and len(sys.argv) > 2:
            # Execute command with -c flag
            command = sys.argv[2]
            exit_code = shell.run_command(command, add_to_history=False)
            sys.exit(exit_code)
        else:
            # Execute command from arguments
            command = ' '.join(sys.argv[1:])
            exit_code = shell.run_command(command)
            sys.exit(exit_code)
    else:
        # Interactive mode
        shell.interactive_loop()