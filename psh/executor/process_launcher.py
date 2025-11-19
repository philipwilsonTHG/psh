"""Unified process launcher for all command execution.

This module provides a centralized component for launching processes with
proper job control setup. It eliminates code duplication across pipelines,
external commands, and subshells.
"""

import os
import sys
import signal
from typing import Optional, Callable, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..core.state import ShellState
    from ..job_control import JobManager, Job
    from ..io_redirect.manager import IOManager
    from ..ast_nodes import Redirect


class ProcessRole(Enum):
    """Role of process in job control structure."""
    SINGLE = "single"                    # Standalone command
    PIPELINE_LEADER = "pipeline_leader"  # First command in pipeline
    PIPELINE_MEMBER = "pipeline_member"  # Non-first command in pipeline


@dataclass
class ProcessConfig:
    """Configuration for launching a process.

    Attributes:
        role: The process's role in job control
        pgid: Process group to join (None = create new)
        foreground: Whether this is a foreground job
        sync_pipe_r: Read end of sync pipe (pipeline synchronization)
        sync_pipe_w: Write end of sync pipe (pipeline synchronization)
        io_setup: Optional callback for I/O redirection setup
    """
    role: ProcessRole
    pgid: Optional[int] = None
    foreground: bool = True
    sync_pipe_r: Optional[int] = None
    sync_pipe_w: Optional[int] = None
    io_setup: Optional[Callable] = None


class ProcessLauncher:
    """Unified component for launching processes with proper job control.

    This class centralizes all process creation logic to ensure consistency
    across pipelines, external commands, and background jobs. It handles:

    - Process forking and error handling
    - Process group setup and synchronization
    - Signal handler reset in child processes
    - Job creation and tracking
    - Terminal control transfer

    Usage:
        # Get signal_manager for centralized child signal reset (H3)
        signal_manager = shell.interactive_manager.signal_manager if hasattr(shell, 'interactive_manager') else None
        launcher = ProcessLauncher(shell.state, shell.job_manager, shell.io_manager, signal_manager)

        # Simple foreground command
        config = ProcessConfig(role=ProcessRole.SINGLE, foreground=True)
        pid, pgid = launcher.launch(lambda: execute_command(), config)

        # Pipeline member with synchronization
        config = ProcessConfig(
            role=ProcessRole.PIPELINE_MEMBER,
            pgid=leader_pgid,
            sync_pipe_r=pipe_r
        )
        pid, pgid = launcher.launch(lambda: execute_command(), config)
    """

    def __init__(self, shell_state: 'ShellState', job_manager: 'JobManager',
                 io_manager: 'IOManager', signal_manager=None):
        """Initialize the process launcher.

        Args:
            shell_state: Shell state for options and configuration
            job_manager: Job manager for tracking processes
            io_manager: I/O manager for redirections
            signal_manager: Optional signal manager for child signal reset (H3)
        """
        self.state = shell_state
        self.job_manager = job_manager
        self.io_manager = io_manager
        self.signal_manager = signal_manager

    def launch(self, execute_fn: Callable[[], int],
               config: ProcessConfig) -> Tuple[int, int]:
        """Launch a process with proper job control setup.

        This is the main entry point for process creation. It handles forking,
        child/parent setup, and returns process information.

        Args:
            execute_fn: Function to execute in child (returns exit code)
            config: Process configuration

        Returns:
            (pid, pgid) tuple - process ID and process group ID

        Raises:
            OSError: If fork() fails
        """
        # Flush Python's stdout/stderr before forking to prevent buffered content
        # from being inherited by the child process and potentially written to
        # redirected output files
        import sys
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except (AttributeError, OSError):
            # stdout/stderr might not support flush() in some contexts
            pass

        pid = os.fork()

        if pid == 0:  # Child process
            self._child_setup_and_exec(execute_fn, config)
            # Does not return - child exits via os._exit()
        else:  # Parent process
            pgid = self._parent_setup(pid, config)
            return pid, pgid

    def _child_setup_and_exec(self, execute_fn: Callable[[], int],
                              config: ProcessConfig):
        """Child process setup and execution.

        This method handles all child process initialization:
        1. Set process group (with synchronization if needed)
        2. Reset signal handlers to default
        3. Set up I/O redirections
        4. Execute the command function
        5. Exit cleanly

        Args:
            execute_fn: Function to execute
            config: Process configuration
        """
        exit_code = 127  # Default: command not found

        try:
            # Mark that we're in a forked child
            self.state._in_forked_child = True

            # 1. Set process group based on role
            if config.role == ProcessRole.PIPELINE_LEADER:
                # First in pipeline: become process group leader
                os.setpgid(0, 0)

                # Close both sync pipe ends (leader doesn't wait)
                if config.sync_pipe_r is not None:
                    try:
                        os.close(config.sync_pipe_r)
                    except OSError:
                        pass
                if config.sync_pipe_w is not None:
                    try:
                        os.close(config.sync_pipe_w)
                    except OSError:
                        pass

                if self.state.options.get('debug-exec'):
                    print(f"DEBUG ProcessLauncher: Child {os.getpid()} is pipeline leader",
                          file=sys.stderr)

            elif config.role == ProcessRole.PIPELINE_MEMBER:
                # Non-first in pipeline: wait for parent signal
                # This uses pipe-based synchronization (C1 implementation)

                # Close write end (child won't write to it)
                if config.sync_pipe_w is not None:
                    try:
                        os.close(config.sync_pipe_w)
                    except OSError:
                        pass

                # Wait for parent to close its write end
                if config.sync_pipe_r is not None:
                    try:
                        # Block on read - will unblock when parent closes write end
                        os.read(config.sync_pipe_r, 1)
                    except OSError:
                        pass  # EOF or error - parent closed pipe
                    finally:
                        try:
                            os.close(config.sync_pipe_r)
                        except OSError:
                            pass

                if self.state.options.get('debug-exec'):
                    current_pgid = os.getpgrp()
                    print(f"DEBUG ProcessLauncher: Child {os.getpid()} synchronized, "
                          f"pgid={current_pgid}", file=sys.stderr)

            elif config.role == ProcessRole.SINGLE:
                # Standalone command: create own process group
                os.setpgid(0, 0)

                if self.state.options.get('debug-exec'):
                    print(f"DEBUG ProcessLauncher: Child {os.getpid()} is single command",
                          file=sys.stderr)

            # 2. Reset signals to default
            # Temporarily ignore SIGTTOU to avoid being stopped when setting terminal
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)

            # Reset other signals to default (use centralized method if available)
            if self.signal_manager:
                self.signal_manager.reset_child_signals()
            else:
                # Fallback for backward compatibility
                self._reset_child_signals()

            # For foreground jobs in final position, restore SIGTTOU to default
            # This will be set appropriately by the caller if needed

            # 3. Set up I/O redirections if provided
            if config.io_setup:
                config.io_setup()

            # 4. Execute command
            exit_code = execute_fn()

            # Ensure exit code is an integer
            if not isinstance(exit_code, int):
                exit_code = 0 if exit_code else 1

        except SystemExit as e:
            # Handle explicit exit() calls
            exit_code = e.code if isinstance(e.code, int) else 1

        except KeyboardInterrupt:
            # Ctrl-C
            exit_code = 130  # 128 + SIGINT(2)

        except Exception as e:
            # Unexpected error
            print(f"psh: error: {e}", file=sys.stderr)
            if self.state.options.get('debug-exec'):
                import traceback
                traceback.print_exc()
            exit_code = 1

        finally:
            # Ensure we always exit cleanly
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass
            os._exit(exit_code)

    def _parent_setup(self, pid: int, config: ProcessConfig) -> int:
        """Parent process setup after fork.

        This method handles process group assignment from the parent side.
        It must be called immediately after fork() to coordinate with the child.

        Args:
            pid: Child process ID
            config: Process configuration

        Returns:
            Process group ID
        """
        # Determine process group
        if config.role == ProcessRole.PIPELINE_LEADER or config.role == ProcessRole.SINGLE:
            # Child becomes its own process group leader
            pgid = pid
            try:
                os.setpgid(pid, pid)
            except OSError:
                pass  # Child may have already set it (race condition)
        else:
            # Child joins existing process group
            pgid = config.pgid if config.pgid is not None else pid
            try:
                os.setpgid(pid, pgid)
                if self.state.options.get('debug-exec'):
                    print(f"DEBUG ProcessLauncher: Parent set child {pid} to pgid {pgid}",
                          file=sys.stderr)
            except OSError as e:
                if self.state.options.get('debug-exec'):
                    print(f"DEBUG ProcessLauncher: Parent failed to set pgid for {pid}: {e}",
                          file=sys.stderr)
                pass  # Child may have already set it

        return pgid

    def _reset_child_signals(self):
        """Reset all signals to default in child process (fallback).

        This is a fallback implementation for when signal_manager is not available.
        The centralized version in SignalManager should be preferred.
        This is called after SIGTTOU is set to SIG_IGN to allow process group changes.
        """
        signals_to_reset = [
            signal.SIGINT,
            signal.SIGQUIT,
            signal.SIGTSTP,
            # SIGTTOU is already handled separately
            signal.SIGTTIN,
            signal.SIGCHLD,
            signal.SIGPIPE,
        ]

        for sig in signals_to_reset:
            try:
                signal.signal(sig, signal.SIG_DFL)
            except (OSError, ValueError):
                # Signal not available on this platform
                pass

    def launch_job(self, execute_fn: Callable[[], int],
                   command_str: str,
                   foreground: bool = True,
                   redirects: Optional[list] = None) -> 'Job':
        """Launch a single command as a job.

        This is a convenience method that combines process launching with
        job creation and terminal control. Use this for simple commands that
        aren't part of a pipeline.

        Args:
            execute_fn: Function to execute
            command_str: Command string (for job display)
            foreground: Foreground or background
            redirects: Optional I/O redirections

        Returns:
            Job object for tracking the process
        """
        # Save original terminal pgid for restoration
        original_pgid = None
        if foreground:
            try:
                original_pgid = os.tcgetpgrp(0)
            except:
                pass

        # Set up I/O redirection callback if needed
        io_setup = None
        if redirects:
            def io_setup():
                from ..ast_nodes import SimpleCommand
                # Parse command_str to get args (simplified)
                args = command_str.split()
                temp_command = SimpleCommand(args=args, redirects=redirects)
                self.io_manager.setup_child_redirections(temp_command)

        # Configure launch
        config = ProcessConfig(
            role=ProcessRole.SINGLE,
            foreground=foreground,
            io_setup=io_setup
        )

        pid, pgid = self.launch(execute_fn, config)

        # Create job for tracking
        job = self.job_manager.create_job(pgid, command_str)
        job.add_process(pid, command_str.split()[0] if command_str else "command")
        job.foreground = foreground

        # Transfer terminal control if foreground (H5)
        if foreground and original_pgid is not None:
            if self.job_manager.transfer_terminal_control(pgid, "ProcessLauncher"):
                self.state.foreground_pgid = pgid

        return job
