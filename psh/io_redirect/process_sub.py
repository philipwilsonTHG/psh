"""Process substitution implementation."""
import os
import sys
import fcntl
from typing import List, Tuple, TYPE_CHECKING
from ..ast_nodes import Command, ProcessSubstitution

if TYPE_CHECKING:
    from ..shell import Shell


class ProcessSubstitutionHandler:
    """Handles process substitution <(...) and >(...)."""
    
    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state
        
        # Track process substitution resources
        self.active_fds = []
        self.active_pids = []
    
    def setup_process_substitutions(self, command: Command) -> Tuple[List[int], List[str], List[int]]:
        """
        Set up process substitutions for a command.
        
        Returns:
            Tuple of (file_descriptors, substituted_paths, child_pids)
        """
        fds_to_keep = []
        substituted_args = []
        child_pids = []
        
        for i, arg in enumerate(command.args):
            arg_type = command.arg_types[i] if i < len(command.arg_types) else 'WORD'
            
            if arg_type in ('PROCESS_SUB_IN', 'PROCESS_SUB_OUT'):
                fd, path, pid = self._create_process_substitution(arg, arg_type)
                fds_to_keep.append(fd)
                substituted_args.append(path)
                child_pids.append(pid)
            else:
                # Not a process substitution, keep as-is
                substituted_args.append(arg)
        
        # Track for cleanup
        self.active_fds.extend(fds_to_keep)
        self.active_pids.extend(child_pids)
        
        return fds_to_keep, substituted_args, child_pids
    
    def _create_process_substitution(self, arg: str, arg_type: str) -> Tuple[int, str, int]:
        """
        Create a single process substitution.
        
        Returns:
            Tuple of (file_descriptor, fd_path, child_pid)
        """
        # Extract command from <(cmd) or >(cmd)
        if arg.startswith('<('):
            direction = 'in'
            cmd_str = arg[2:-1]  # Remove <( and )
        elif arg.startswith('>('):
            direction = 'out'
            cmd_str = arg[2:-1]  # Remove >( and )
        else:
            raise ValueError(f"Invalid process substitution: {arg}")
        
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
                # Import here to avoid circular import
                from ..tokenizer import tokenize
                from ..parser import parse
                from ..shell import Shell
                
                # Parse and execute the command string
                tokens = tokenize(cmd_str)
                ast = parse(tokens)
                # Create a new shell instance to avoid state pollution
                temp_shell = Shell()
                temp_shell.env = self.state.env.copy()
                temp_shell.variables = self.state.variables.copy()
                exit_code = temp_shell.execute_command_list(ast)
                os._exit(exit_code)
            except Exception as e:
                print(f"psh: process substitution error: {e}", file=sys.stderr)
                os._exit(1)
        
        else:  # Parent
            # Close child's end of pipe
            os.close(child_fd)
            
            # Create path for this fd
            # On Linux/macOS, we can use /dev/fd/N
            fd_path = f"/dev/fd/{parent_fd}"
            
            return parent_fd, fd_path, pid
    
    def handle_redirect_process_sub(self, target: str) -> Tuple[str, int, int]:
        """
        Handle process substitution used as a redirect target.
        
        Args:
            target: The process substitution string (e.g., "<(cmd)" or ">(cmd)")
            
        Returns:
            Tuple of (fd_path, fd_to_close, child_pid)
        """
        if target.startswith('<('):
            arg_type = 'PROCESS_SUB_IN'
        elif target.startswith('>('):
            arg_type = 'PROCESS_SUB_OUT'
        else:
            raise ValueError(f"Invalid process substitution redirect: {target}")
        
        fd, path, pid = self._create_process_substitution(target, arg_type)
        
        # Track for cleanup
        self.active_fds.append(fd)
        self.active_pids.append(pid)
        
        return path, fd, pid
    
    def cleanup(self):
        """Clean up process substitution file descriptors and wait for children."""
        # Close file descriptors
        for fd in self.active_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self.active_fds.clear()
        
        # Wait for child processes
        for pid in self.active_pids:
            try:
                os.waitpid(pid, 0)
            except OSError:
                pass
        self.active_pids.clear()