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
    
    def setup_builtin_redirections(self, command: Command) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Set up redirections for builtin commands, returning saved stdin/stdout/stderr."""
        # For now, delegate to shell's existing method
        return self.shell._setup_builtin_redirections(command)
    
    def restore_builtin_redirections(self, stdin_backup, stdout_backup, stderr_backup):
        """Restore stdin/stdout/stderr for builtin commands."""
        # For now, delegate to shell's existing method
        self.shell._restore_builtin_redirections(stdin_backup, stdout_backup, stderr_backup)
    
    def setup_child_redirections(self, command: Command):
        """Set up redirections in a child process."""
        # For now, delegate to shell's existing method
        self.shell._setup_child_redirections(command)
    
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