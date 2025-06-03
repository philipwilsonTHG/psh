"""Signal handling manager for interactive shell."""
import os
import signal
import sys
from typing import Optional, Callable, Dict
from .base import InteractiveComponent
from ..job_control import JobState


class SignalManager(InteractiveComponent):
    """Manages signal handling for the interactive shell."""
    
    def __init__(self, shell):
        super().__init__(shell)
        self._original_handlers: Dict[int, Callable] = {}
        self._interactive_mode = not shell.state.is_script_mode
        
    def execute(self, *args, **kwargs):
        """Set up signal handlers based on shell mode."""
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Configure signal handlers based on shell mode."""
        if self.state.is_script_mode:
            self._setup_script_mode_handlers()
        else:
            self._setup_interactive_mode_handlers()
            
    def _setup_script_mode_handlers(self):
        """Set up simpler signal handling for script mode."""
        # Script mode: use default signal behaviors
        signal.signal(signal.SIGINT, signal.SIG_DFL)   # Default SIGINT behavior
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)  # Default SIGTSTP behavior
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Still ignore terminal output stops
        signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Still ignore terminal input stops
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)  # Default child handling
        
    def _setup_interactive_mode_handlers(self):
        """Set up full signal handling for interactive mode."""
        # Store original handlers for restoration
        self._original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self._handle_sigint)
        self._original_handlers[signal.SIGTSTP] = signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        self._original_handlers[signal.SIGTTOU] = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        self._original_handlers[signal.SIGTTIN] = signal.signal(signal.SIGTTIN, signal.SIG_IGN)
        self._original_handlers[signal.SIGCHLD] = signal.signal(signal.SIGCHLD, self._handle_sigchld)
        
    def restore_default_handlers(self):
        """Restore default signal handlers."""
        # Restore all saved handlers
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
            except Exception:
                # Signal may not be valid on this platform
                pass
        self._original_handlers.clear()
        
    def _handle_sigint(self, signum, frame):
        """Handle Ctrl-C (SIGINT)."""
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
                            
            except OSError:
                # No more children
                break
                
    def ensure_foreground(self):
        """Ensure shell is in its own process group and is foreground."""
        shell_pgid = os.getpid()
        try:
            os.setpgid(0, shell_pgid)
            # Make shell the foreground process group
            os.tcsetpgrp(0, shell_pgid)
        except OSError:
            # Not a terminal or already set
            pass