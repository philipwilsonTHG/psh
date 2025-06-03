"""File redirection implementation."""
import os
import fcntl
from typing import List, Tuple, Optional, TYPE_CHECKING
from ..ast_nodes import Redirect

if TYPE_CHECKING:
    from ..shell import Shell


class FileRedirector:
    """Handles file-based I/O redirections."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
    
    def apply_redirections(self, redirects: List[Redirect]) -> List[Tuple[int, int]]:
        """
        Apply redirections and return list of (fd, saved_fd) for restoration.
        
        This handles all types of redirections:
        - < (input redirection)
        - > (output redirection) 
        - >> (append redirection)
        - << and <<- (here documents)
        - <<< (here strings)
        - >& (fd duplication like 2>&1)
        """
        saved_fds = []
        
        # Save current Python file objects
        self.shell._saved_stdout = self.state.stdout
        self.shell._saved_stderr = self.state.stderr
        self.shell._saved_stdin = self.state.stdin
        
        for redirect in redirects:
            # Expand tilde in target for file redirections
            target = redirect.target
            if target and redirect.type in ('<', '>', '>>') and target.startswith('~'):
                target = self.shell.expansion_manager.expand_tilde(target)
            
            # Handle process substitution as redirect target
            if target and target.startswith(('<(', '>(')) and target.endswith(')'):
                # Process substitution will be handled by process_sub module
                target = self._handle_process_sub_redirect(target, redirect)
            
            if redirect.type == '<':
                # Input redirection
                saved_fds.append((0, os.dup(0)))
                fd = os.open(target, os.O_RDONLY)
                os.dup2(fd, 0)
                os.close(fd)
                
            elif redirect.type in ('<<', '<<-'):
                # Here document
                saved_fds.append((0, os.dup(0)))
                r, w = os.pipe()
                # Write heredoc content to pipe
                os.write(w, (redirect.heredoc_content or '').encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
                
            elif redirect.type == '<<<':
                # Here string
                saved_fds.append((0, os.dup(0)))
                r, w = os.pipe()
                # Write here string content with newline
                content = redirect.target + '\n'
                os.write(w, content.encode())
                os.close(w)
                # Redirect stdin to read end
                os.dup2(r, 0)
                os.close(r)
                
            elif redirect.type == '>':
                # Output redirection (truncate)
                target_fd = redirect.fd if redirect.fd is not None else 1
                saved_fds.append((target_fd, os.dup(target_fd)))
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                os.dup2(fd, target_fd)
                os.close(fd)
                
            elif redirect.type == '>>':
                # Output redirection (append)
                target_fd = redirect.fd if redirect.fd is not None else 1
                saved_fds.append((target_fd, os.dup(target_fd)))
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
                os.dup2(fd, target_fd)
                os.close(fd)
                
            elif redirect.type == '>&':
                # FD duplication (e.g., 2>&1)
                if redirect.fd is not None and redirect.dup_fd is not None:
                    saved_fds.append((redirect.fd, os.dup(redirect.fd)))
                    os.dup2(redirect.dup_fd, redirect.fd)
        
        return saved_fds
    
    def restore_redirections(self, saved_fds: List[Tuple[int, int]]):
        """Restore file descriptors from saved list."""
        for fd, saved_fd in saved_fds:
            os.dup2(saved_fd, fd)
            os.close(saved_fd)
        
        # Restore Python file objects
        if hasattr(self.shell, '_saved_stdout'):
            self.state.stdout = self.shell._saved_stdout
            self.state.stderr = self.shell._saved_stderr
            self.state.stdin = self.shell._saved_stdin
            del self.shell._saved_stdout
            del self.shell._saved_stderr
            del self.shell._saved_stdin
    
    def _handle_process_sub_redirect(self, target: str, redirect: Redirect) -> str:
        """
        Handle process substitution used as a redirect target.
        This is a placeholder - the actual implementation will be in process_sub.py
        """
        # For now, delegate back to shell
        # This will be replaced when we extract process substitution
        from ..tokenizer import tokenize
        from ..parser import parse
        
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
                # Import Shell here to avoid circular import
                from ..shell import Shell
                tokens = tokenize(cmd_str)
                ast = parse(tokens)
                temp_shell = Shell()
                temp_shell.env = self.state.env.copy()
                temp_shell.variables = self.state.variables.copy()
                exit_code = temp_shell.execute_command_list(ast)
                os._exit(exit_code)
            except Exception as e:
                print(f"psh: process substitution error: {e}", file=sys.stderr)
                os._exit(1)
        else:  # Parent
            os.close(child_fd)
            # Store for cleanup
            if not hasattr(self.shell, '_redirect_proc_sub_fds'):
                self.shell._redirect_proc_sub_fds = []
            if not hasattr(self.shell, '_redirect_proc_sub_pids'):
                self.shell._redirect_proc_sub_pids = []
            self.shell._redirect_proc_sub_fds.append(parent_fd)
            self.shell._redirect_proc_sub_pids.append(pid)
            # Use the fd path as target
            return f"/dev/fd/{parent_fd}"