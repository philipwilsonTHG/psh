"""I/O redirection manager for handling all types of redirections."""
import os
import sys
from typing import List, Tuple, Optional, TYPE_CHECKING
from contextlib import contextmanager
from ..ast_nodes import Redirect, Command
from ..core.state import ShellState
from .file_redirect import FileRedirector
from .heredoc import HeredocHandler
from .process_sub import ProcessSubstitutionHandler

if TYPE_CHECKING:
    from ..shell import Shell


class IOManager:
    """Manages all I/O redirections including files, heredocs, and process substitutions."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Initialize sub-handlers
        self.file_redirector = FileRedirector(shell)
        self.heredoc_handler = HeredocHandler(shell)
        self.process_sub_handler = ProcessSubstitutionHandler(shell)
        
        # Track saved file descriptors for restoration
        self._saved_fds = []
        
        # Track temporary files for cleanup
        self._temp_files = []
    
    @contextmanager
    def with_redirections(self, redirects: List[Redirect]):
        """Context manager for applying redirections temporarily."""
        saved_fds = self.apply_redirections(redirects)
        try:
            yield
        finally:
            self.restore_redirections(saved_fds)
    
    def apply_redirections(self, redirects: List[Redirect]) -> List[Tuple[int, int]]:
        """Apply redirections and return list of saved FDs for restoration."""
        return self.file_redirector.apply_redirections(redirects)
    
    def restore_redirections(self, saved_fds: List[Tuple[int, int]]):
        """Restore file descriptors from saved list."""
        self.file_redirector.restore_redirections(saved_fds)
    
    def apply_permanent_redirections(self, redirects: List[Redirect]):
        """Apply redirections permanently (for exec builtin)."""
        return self.file_redirector.apply_permanent_redirections(redirects)
    
    def setup_builtin_redirections(self, command: Command) -> Tuple:
        """Set up redirections for built-in commands. Returns tuple of backup objects."""
        import io
        import fcntl
        from ..lexer import tokenize
        from ..parser import parse
        
        # DEBUG: Log builtin redirection setup
        if self.state.options.get('debug-exec'):
            print(f"DEBUG IOManager: setup_builtin_redirections called", file=sys.stderr)
            print(f"DEBUG IOManager: Redirects: {[(r.type, r.target, r.fd) for r in command.redirects]}", file=sys.stderr)
        
        stdout_backup = None
        stderr_backup = None
        stdin_backup = None
        stdin_fd_backup = None
        
        for redirect in command.redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self.shell.expansion_manager.expand_tilde(target)
            
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
                        # Import here to avoid circular dependency
                        from ..shell import Shell
                        # Create child shell with parent reference for proper inheritance
                        temp_shell = Shell(parent_shell=self.shell)
                        exit_code = temp_shell.execute_command_list(ast)
                        os._exit(exit_code)
                    except Exception as e:
                        print(f"psh: process substitution error: {e}", file=sys.stderr)
                        os._exit(1)
                else:  # Parent
                    os.close(child_fd)
                    # Store for cleanup
                    if not hasattr(self.shell, '_builtin_proc_sub_fds'):
                        self.shell._builtin_proc_sub_fds = []
                    if not hasattr(self.shell, '_builtin_proc_sub_pids'):
                        self.shell._builtin_proc_sub_pids = []
                    self.shell._builtin_proc_sub_fds.append(parent_fd)
                    self.shell._builtin_proc_sub_pids.append(pid)
                    # Use the fd path as target
                    target = f"/dev/fd/{parent_fd}"
            
            if redirect.type == '<':
                stdin_backup = sys.stdin
                # Also need to redirect the actual file descriptor for builtins that use os.read
                stdin_fd_backup = os.dup(0)
                fd = os.open(target, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)
                sys.stdin = open(target, 'r')
            elif redirect.type in ('<<', '<<-'):
                stdin_backup = sys.stdin
                # Also need to redirect the actual file descriptor
                stdin_fd_backup = os.dup(0)
                r, w = os.pipe()
                
                # Apply variable expansion to heredoc content based on delimiter quoting
                content = redirect.heredoc_content or ''
                heredoc_quoted = getattr(redirect, 'heredoc_quoted', False)
                if content and not heredoc_quoted:
                    # Delimiter was not quoted, so expand variables
                    content = self.shell.expansion_manager.expand_string_variables(content)
                
                # Write heredoc content to pipe
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
                # Create a StringIO object from heredoc content
                sys.stdin = io.StringIO(content)
            elif redirect.type == '<<<':
                stdin_backup = sys.stdin
                # Also need to redirect the actual file descriptor
                stdin_fd_backup = os.dup(0)
                r, w = os.pipe()
                # For here string, expand variables unless single quoted
                if redirect.quote_type == "'":
                    # Single quotes - no expansion
                    expanded_content = redirect.target
                else:
                    # Double quotes or no quotes - expand variables
                    expanded_content = self.shell.expansion_manager.expand_string_variables(redirect.target)
                # Add a newline to the content
                content = expanded_content + '\n'
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
                sys.stdin = io.StringIO(content)
            elif redirect.type == '>' and redirect.fd == 2:
                stderr_backup = sys.stderr
                
                # Check noclobber option - prevent overwriting existing files
                if self.state.options.get('noclobber', False) and os.path.exists(target):
                    raise OSError(f"psh: cannot overwrite existing file: {target}")
                
                sys.stderr = open(target, 'w')
            elif redirect.type == '>>' and redirect.fd == 2:
                stderr_backup = sys.stderr
                sys.stderr = open(target, 'a')
            elif redirect.type == '>' and (redirect.fd is None or redirect.fd == 1):
                stdout_backup = sys.stdout
                
                # Check noclobber option - prevent overwriting existing files
                if self.state.options.get('noclobber', False) and os.path.exists(target):
                    raise OSError(f"psh: cannot overwrite existing file: {target}")
                
                sys.stdout = open(target, 'w')
                # DEBUG: Log stdout redirection
                if self.state.options.get('debug-exec'):
                    print(f"DEBUG IOManager: Redirected stdout to file '{target}'", file=sys.stderr)
                    print(f"DEBUG IOManager: sys.stdout is now {sys.stdout}", file=sys.stderr)
            elif redirect.type == '>>' and (redirect.fd is None or redirect.fd == 1):
                stdout_backup = sys.stdout
                sys.stdout = open(target, 'a')
                # DEBUG: Log stdout append redirection
                if self.state.options.get('debug-exec'):
                    print(f"DEBUG IOManager: Redirected stdout (append) to file '{target}'", file=sys.stderr)
                    print(f"DEBUG IOManager: sys.stdout is now {sys.stdout}", file=sys.stderr)
            elif redirect.type == '>&':
                # Handle fd duplication like 2>&1, >&2, etc.
                if redirect.fd == 2 and redirect.dup_fd == 1:
                    # 2>&1: stderr to stdout
                    stderr_backup = sys.stderr
                    sys.stderr = sys.stdout
                elif redirect.fd == 1 and redirect.dup_fd == 2:
                    # 1>&2 or >&2: stdout to stderr
                    stdout_backup = sys.stdout
                    sys.stdout = sys.stderr
                # Note: Other fd combinations would require more complex handling
        
        return stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup
    
    def restore_builtin_redirections(self, stdin_backup, stdout_backup, stderr_backup, stdin_fd_backup=None):
        """Restore original stdin/stdout/stderr after built-in execution"""
        import io
        
        # Restore in reverse order
        if stderr_backup is not None:
            if hasattr(sys.stderr, 'close') and sys.stderr != stderr_backup:
                # Don't close StringIO objects as they might be reused
                if not isinstance(sys.stderr, io.StringIO):
                    sys.stderr.close()
            sys.stderr = stderr_backup
        
        if stdout_backup is not None:
            if hasattr(sys.stdout, 'close') and sys.stdout != stdout_backup:
                # Don't close StringIO objects as they might be reused
                if not isinstance(sys.stdout, io.StringIO):
                    sys.stdout.close()
            sys.stdout = stdout_backup
            
        if stdin_backup is not None:
            if hasattr(sys.stdin, 'close') and sys.stdin != stdin_backup:
                # Don't close StringIO objects as they might be reused
                if not isinstance(sys.stdin, io.StringIO):
                    sys.stdin.close()
            sys.stdin = stdin_backup
            
        # Restore stdin file descriptor if it was saved
        if stdin_fd_backup is not None:
            os.dup2(stdin_fd_backup, 0)
            os.close(stdin_fd_backup)
        
        # Clean up process substitution resources if any
        if hasattr(self.shell, '_builtin_proc_sub_fds'):
            for fd in self.shell._builtin_proc_sub_fds:
                try:
                    os.close(fd)
                except:
                    pass
            self.shell._builtin_proc_sub_fds = []
        
        if hasattr(self.shell, '_builtin_proc_sub_pids'):
            for pid in self.shell._builtin_proc_sub_pids:
                try:
                    os.waitpid(pid, 0)
                except:
                    pass
            self.shell._builtin_proc_sub_pids = []
    
    def setup_child_redirections(self, command: Command):
        """Set up redirections in child process (after fork) using dup2"""
        for redirect in command.redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self.shell.expansion_manager.expand_tilde(target)
            
            # Handle process substitution as redirect target
            if target and target.startswith(('<(', '>(')) and target.endswith(')'):
                # This is a process substitution used as a redirect target
                # We need to set it up here in the child process
                path, fd_to_close, pid = self.process_sub_handler.handle_redirect_process_sub(target)
                target = path
                # Note: We don't track these for cleanup since we're in the child that will exec
            
            if redirect.type == '<':
                fd = os.open(target, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)
            elif redirect.type in ('<<', '<<-'):
                # Create a pipe for heredoc
                r, w = os.pipe()
                
                # Apply variable expansion to heredoc content based on delimiter quoting
                content = redirect.heredoc_content or ''
                heredoc_quoted = getattr(redirect, 'heredoc_quoted', False)
                if content and not heredoc_quoted:
                    # Delimiter was not quoted, so expand variables
                    content = self.shell.expansion_manager.expand_string_variables(content)
                
                # Write heredoc content to pipe
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '<<<':
                # Create a pipe for here string
                r, w = os.pipe()
                # For here string, expand variables unless single quoted
                if redirect.quote_type == "'":
                    # Single quotes - no expansion
                    expanded_content = redirect.target
                else:
                    # Double quotes or no quotes - expand variables
                    expanded_content = self.shell.expansion_manager.expand_string_variables(redirect.target)
                # Write here string content with newline
                content = expanded_content + '\n'
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
            elif redirect.type == '>':
                # Check noclobber option
                if self.state.options.get('noclobber', False) and os.path.exists(target):
                    # Write error directly to stderr fd
                    error_msg = f"psh: cannot overwrite existing file: {target}\n"
                    os.write(2, error_msg.encode('utf-8'))
                    os._exit(1)
                
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
    
    def collect_heredocs(self, node):
        """Collect here document content for all commands in a node."""
        self.heredoc_handler.collect_heredocs(node)
    
    def setup_process_substitutions(self, command: Command) -> Tuple[List[int], List[str], List[int]]:
        """Set up process substitutions for a command."""
        return self.process_sub_handler.setup_process_substitutions(command)
    
    def cleanup_process_substitutions(self):
        """Clean up process substitution resources."""
        self.process_sub_handler.cleanup()
    
    def handle_heredoc(self, delimiter: str, content: str, strip_tabs: bool = False) -> str:
        """
        Handle here document creation.
        
        Args:
            delimiter: The heredoc delimiter
            content: The heredoc content
            strip_tabs: Whether to strip leading tabs (for <<- operator)
            
        Returns:
            Path to temporary file containing heredoc content
        """
        import tempfile
        
        # Process content if needed
        if strip_tabs:
            lines = content.split('\n')
            processed_lines = []
            for line in lines:
                # Strip leading tabs only
                processed_lines.append(line.lstrip('\t'))
            content = '\n'.join(processed_lines)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        self._temp_files.append(temp_path)
        return temp_path
    
    def cleanup_temp_files(self):
        """Clean up any temporary files created for redirections."""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except OSError:
                pass
        self._temp_files.clear()
    
    def is_valid_fd(self, fd: int) -> bool:
        """Check if a file descriptor is valid."""
        try:
            # Try to get flags for the FD
            import fcntl
            fcntl.fcntl(fd, fcntl.F_GETFD)
            return True
        except (OSError, IOError):
            return False
    
    def _is_heredoc_delimiter_quoted(self, delimiter: str) -> bool:
        """Check if heredoc delimiter was originally quoted."""
        # For now, this is a simple check - in a full implementation,
        # this information should be passed from the parser
        return delimiter.startswith(("'", '"')) and delimiter.endswith(("'", '"'))
