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


class Shell:
    def __init__(self):
        self.env = os.environ.copy()
        self.last_exit_code = 0
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
        }
    
    def execute_command(self, command: Command):
        # Expand variables and globs in arguments
        args = []
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            
            if arg.startswith('$'):
                var_name = arg[1:]
                # Handle special variable $?
                if var_name == '?':
                    args.append(str(self.last_exit_code))
                else:
                    args.append(self.env.get(var_name, ''))
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
            stdout_backup = None
            stdin_backup = None
            try:
                for redirect in command.redirects:
                    if redirect.type == '<':
                        stdin_backup = sys.stdin
                        sys.stdin = open(redirect.target, 'r')
                    elif redirect.type == '>':
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'w')
                    elif redirect.type == '>>':
                        stdout_backup = sys.stdout
                        sys.stdout = open(redirect.target, 'a')
                
                return self.builtins[args[0]](args)
            finally:
                # Restore original stdin/stdout
                if stdin_backup:
                    sys.stdin.close()
                    sys.stdin = stdin_backup
                if stdout_backup:
                    sys.stdout.close()
                    sys.stdout = stdout_backup
        
        # Execute external command
        try:
            # Set up redirections
            stdin = None
            stdout = None
            stderr = None
            
            for redirect in command.redirects:
                if redirect.type == '<':
                    stdin = open(redirect.target, 'r')
                elif redirect.type == '>':
                    stdout = open(redirect.target, 'w')
                elif redirect.type == '>>':
                    stdout = open(redirect.target, 'a')
            
            # Run the command
            proc = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=self.env
            )
            
            if command.background:
                print(f"[{proc.pid}]")
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
            if stdin and stdin != sys.stdin:
                stdin.close()
            if stdout and stdout != sys.stdout:
                stdout.close()
    
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
        
        while True:
            try:
                # Prompt with exit status indicator
                if self.last_exit_code != 0:
                    prompt = f"[{self.last_exit_code}] {os.getcwd()}$ "
                else:
                    prompt = f"{os.getcwd()}$ "
                command = input(prompt)
                
                if command.strip():
                    self.run_command(command)
            
            except EOFError:
                print("\nexit")
                self._save_history()
                break
            except KeyboardInterrupt:
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
        if len(args) > 1 and '=' in args[1]:
            var, value = args[1].split('=', 1)
            self.env[var] = value
            os.environ[var] = value
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
            
            if arg.startswith('$'):
                var_name = arg[1:]
                # Handle special variable $?
                if var_name == '?':
                    args.append(str(self.last_exit_code))
                else:
                    args.append(self.env.get(var_name, ''))
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
                    elif redirect.type == '>':
                        fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        os.dup2(fd, 1)
                        os.close(fd)
                    elif redirect.type == '>>':
                        fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                        os.dup2(fd, 1)
                        os.close(fd)
                
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
                elif redirect.type == '>':
                    fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                    os.dup2(fd, 1)
                    os.close(fd)
                elif redirect.type == '>>':
                    fd = os.open(redirect.target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                    os.dup2(fd, 1)
                    os.close(fd)
            
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
        # Execute command from arguments
        command = ' '.join(sys.argv[1:])
        exit_code = shell.run_command(command)
        sys.exit(exit_code)
    else:
        # Interactive mode
        shell.interactive_loop()