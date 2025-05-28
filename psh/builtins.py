#!/usr/bin/env python3
"""Built-in commands for Python Shell (psh)."""

import os
import sys
import stat
from .exceptions import FunctionReturn


class BuiltinCommands:
    """Container for all built-in shell commands."""
    
    def __init__(self, shell):
        """Initialize with reference to the shell instance."""
        self.shell = shell
    
    def get_builtin_map(self):
        """Return dictionary mapping builtin names to methods."""
        return {
            'exit': self.exit,
            'cd': self.cd,
            'export': self.export,
            'pwd': self.pwd,
            'echo': self.echo,
            'env': self.env,
            'unset': self.unset,
            'source': self.source,
            '.': self.source,
            'history': self.history,
            'set': self.set,
            'version': self.version,
            'alias': self.alias,
            'unalias': self.unalias,
            'declare': self.declare,
            'return': self.return_builtin,
            'jobs': self.jobs,
            'fg': self.fg,
            'test': self.test,
            '[': self.test,
            'bg': self.bg,
            'true': self.true,
            'false': self.false,
        }
    
    def exit(self, args):
        """Exit the shell with optional exit code."""
        # Save history before exiting
        self.shell._save_history()
        
        if len(args) > 1:
            try:
                exit_code = int(args[1])
            except ValueError:
                print(f"exit: {args[1]}: numeric argument required", file=sys.stderr)
                exit_code = 2
        else:
            exit_code = 0
        sys.exit(exit_code)
    
    def cd(self, args):
        """Change directory."""
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
    
    def export(self, args):
        """Export variables to environment."""
        if len(args) == 1:
            # No arguments, print all exported variables
            for key, value in sorted(self.shell.env.items()):
                print(f'export {key}="{value}"')
        else:
            for arg in args[1:]:
                if '=' in arg:
                    # Variable assignment
                    key, value = arg.split('=', 1)
                    self.shell.env[key] = value
                    self.shell.variables[key] = value
                else:
                    # Export existing variable
                    if arg in self.shell.variables:
                        self.shell.env[arg] = self.shell.variables[arg]
        return 0
    
    def pwd(self, args):
        """Print working directory."""
        print(os.getcwd())
        return 0
    
    def echo(self, args):
        """Echo arguments to stdout."""
        # Simple echo implementation
        if len(args) > 1:
            print(' '.join(args[1:]))
        else:
            print()
        return 0
    
    def env(self, args):
        """Display environment variables."""
        if len(args) == 1:
            # No arguments, print all environment variables
            for key, value in sorted(self.shell.env.items()):
                print(f"{key}={value}")
        else:
            # Run command with modified environment (simplified)
            # For now, just print error
            print("env: running commands not yet implemented", file=sys.stderr)
            return 1
        return 0
    
    def unset(self, args):
        """Unset variables or functions."""
        if len(args) < 2:
            print("unset: not enough arguments", file=sys.stderr)
            return 1
        
        # Check for -f flag
        if '-f' in args:
            # Remove functions
            exit_code = 0
            for arg in args[1:]:
                if arg != '-f':
                    if not self.shell.function_manager.undefine_function(arg):
                        print(f"unset: {arg}: not a function", file=sys.stderr)
                        exit_code = 1
            return exit_code
        else:
            # Remove variables
            for var in args[1:]:
                # Remove from both shell variables and environment
                self.shell.variables.pop(var, None)
                self.shell.env.pop(var, None)
            return 0
    
    def source(self, args):
        """Source a script file."""
        if len(args) < 2:
            print("source: filename argument required", file=sys.stderr)
            return 1
        
        filename = args[1]
        source_args = args[2:] if len(args) > 2 else []
        
        # Find the script file
        script_path = self.shell._find_source_file(filename)
        if script_path is None:
            print(f"source: {filename}: No such file or directory", file=sys.stderr)
            return 1
        
        # Validate the script file
        validation_result = self.shell._validate_script_file(script_path)
        if validation_result != 0:
            return validation_result
        
        # Save current shell state
        old_positional = self.shell.positional_params.copy()
        old_script_name = self.shell.script_name
        old_script_mode = self.shell.is_script_mode
        
        # Set new state for sourced script
        self.shell.positional_params = source_args
        self.shell.script_name = script_path
        # Keep current script mode (sourcing inherits mode)
        
        try:
            from .input_sources import FileInput
            with FileInput(script_path) as input_source:
                # Execute with no history since it's sourced
                return self.shell._execute_from_source(input_source, add_to_history=False)
        except Exception as e:
            print(f"source: {script_path}: {e}", file=sys.stderr)
            return 1
        finally:
            # Restore previous state
            self.shell.positional_params = old_positional
            self.shell.script_name = old_script_name
            self.shell.is_script_mode = old_script_mode
    
    def history(self, args):
        """Display command history."""
        # Simple history implementation
        if len(args) > 1:
            try:
                count = int(args[1])
                start = max(0, len(self.shell.history) - count)
                history_slice = self.shell.history[start:]
            except ValueError:
                print(f"history: {args[1]}: numeric argument required", file=sys.stderr)
                return 1
        else:
            # Default to showing last 10 commands (bash behavior)
            count = 10
            start = max(0, len(self.shell.history) - count)
            history_slice = self.shell.history[start:]
        
        # Print with line numbers
        start_num = len(self.shell.history) - len(history_slice) + 1
        for i, cmd in enumerate(history_slice):
            print(f"{start_num + i:5d}  {cmd}")
        return 0
    
    def set(self, args):
        """Set shell options and positional parameters."""
        if len(args) == 1:
            # No arguments, display all variables
            # Show shell variables
            for var, value in sorted(self.shell.variables.items()):
                print(f"{var}={value}")
            # Also show set options
            print(f"edit_mode={self.shell.edit_mode}")
        elif len(args) >= 3 and args[1] == '-o':
            # Set option: set -o vi or set -o emacs
            option = args[2].lower()
            if option in ('vi', 'emacs'):
                self.shell.edit_mode = option
                print(f"Edit mode set to {option}")
            else:
                print(f"psh: set: invalid option: {option}", file=sys.stderr)
                print("Valid options: vi, emacs", file=sys.stderr)
                return 1
        elif args[1] == '-o' and len(args) == 2:
            # Show current options
            print(f"edit_mode {self.shell.edit_mode}")
        elif args[1] == '+o' and len(args) >= 3:
            # Unset option (for compatibility, we just set to emacs)
            option = args[2].lower()
            if option == 'vi':
                self.shell.edit_mode = 'emacs'
                print("Edit mode set to emacs")
        else:
            # Set positional parameters
            self.shell.positional_params = args[1:]
        return 0
    
    def version(self, args):
        """Display version information."""
        if len(args) > 1 and args[1] == '--short':
            # Just print version number
            from .version import __version__
            print(__version__)
        else:
            # Full version info
            from .version import get_version_info
            print(get_version_info())
        return 0
    
    def alias(self, args):
        """Define or display aliases."""
        if len(args) == 1:
            # No arguments - list all aliases
            for name, value in sorted(self.shell.alias_manager.list_aliases()):
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
                    self.shell.alias_manager.define_alias(name, value)
                except ValueError as e:
                    print(f"psh: alias: {e}", file=sys.stderr)
                    exit_code = 1
            else:
                # Show specific alias
                value = self.shell.alias_manager.get_alias(arg)
                if value is not None:
                    # Escape single quotes in value for display
                    escaped_value = value.replace("'", "'\"'\"'")
                    print(f"alias {arg}='{escaped_value}'")
                else:
                    print(f"psh: alias: {arg}: not found", file=sys.stderr)
                    exit_code = 1
            
            i += 1
        
        return exit_code
    
    def unalias(self, args):
        """Remove aliases."""
        if len(args) == 1:
            print("unalias: usage: unalias [-a] name [name ...]", file=sys.stderr)
            return 1
        
        if args[1] == '-a':
            # Remove all aliases
            self.shell.alias_manager.clear_aliases()
            return 0
        
        exit_code = 0
        for name in args[1:]:
            if not self.shell.alias_manager.undefine_alias(name):
                print(f"psh: unalias: {name}: not found", file=sys.stderr)
                exit_code = 1
        
        return exit_code
    
    def declare(self, args):
        """Declare variables and functions."""
        if '-f' in args:
            if len(args) == 2:  # declare -f
                # List all functions
                for name, func in self.shell.function_manager.list_functions():
                    self._print_function_definition(name, func)
            else:  # declare -f name
                for arg in args[2:]:
                    func = self.shell.function_manager.get_function(arg)
                    if func:
                        self._print_function_definition(arg, func)
                    else:
                        print(f"psh: declare: {arg}: not found", file=sys.stderr)
                        return 1
        else:
            # For now, just list variables (like set with no args)
            for var, value in sorted(self.shell.variables.items()):
                print(f"{var}={value}")
        return 0
    
    def _print_function_definition(self, name, func):
        """Print a function definition in a format that can be re-executed."""
        print(f"{name} () {{")
        # We need to pretty-print the function body
        # For now, just indicate it's defined
        print(f"    # function body")
        print("}")
    
    def return_builtin(self, args):
        """Return from a function with optional exit code."""
        if not self.shell.function_stack:
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
    
    def jobs(self, args):
        """List active jobs."""
        for line in self.shell.job_manager.list_jobs():
            print(line)
        return 0
    
    def fg(self, args):
        """Bring job to foreground."""
        job_spec = args[1] if len(args) > 1 else '%+'
        job = self.shell.job_manager.parse_job_spec(job_spec)
        
        if not job:
            print(f"fg: {job_spec}: no such job", file=sys.stderr)
            return 1
        
        # Print job info
        print(job.command)
        
        # Give it terminal control FIRST before sending SIGCONT
        self.shell.job_manager.set_foreground_job(job)
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
            from .job_control import JobState
            job.state = JobState.RUNNING
            
            # Send SIGCONT to the process group
            import signal
            os.killpg(job.pgid, signal.SIGCONT)
        
        # Wait for it
        exit_status = self.shell.job_manager.wait_for_job(job)
        
        # Restore terminal control to shell
        try:
            os.tcsetpgrp(0, os.getpgrp())
        except OSError:
            pass
        
        # Remove job if completed
        from .job_control import JobState
        if job.state == JobState.DONE:
            self.shell.job_manager.remove_job(job.job_id)
        
        return exit_status
    
    def bg(self, args):
        """Resume job in background."""
        job_spec = args[1] if len(args) > 1 else '%+'
        job = self.shell.job_manager.parse_job_spec(job_spec)
        
        if not job:
            print(f"bg: {job_spec}: no such job", file=sys.stderr)
            return 1
        
        if job.state.value == 'stopped':
            # Mark processes as running again
            for proc in job.processes:
                if proc.stopped:
                    proc.stopped = False
            from .job_control import JobState
            job.state = JobState.RUNNING
            job.foreground = False
            
            # Send SIGCONT to resume
            import signal
            os.killpg(job.pgid, signal.SIGCONT)
            print(f"[{job.job_id}]+ {job.command} &")
        return 0
    
    def test(self, args):
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
    
    def true(self, args):
        """Always return success (exit code 0)."""
        return 0
    
    def false(self, args):
        """Always return failure (exit code 1)."""
        return 1