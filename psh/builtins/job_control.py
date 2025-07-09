"""Job control builtin commands."""
import os
import signal
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin
from ..job_control import JobState

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class JobsBuiltin(Builtin):
    """List active jobs."""
    
    @property
    def name(self) -> str:
        return "jobs"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the jobs builtin."""
        # Parse options
        show_pids_only = False
        show_long_format = False
        
        for arg in args[1:]:
            if arg == '-p':
                show_pids_only = True
            elif arg == '-l':
                show_long_format = True
            elif arg.startswith('-'):
                self.error(f"invalid option: {arg}", shell)
                return 1
        
        if show_pids_only:
            # Show only PIDs
            for job_id in sorted(shell.job_manager.jobs.keys()):
                job = shell.job_manager.jobs[job_id]
                for proc in job.processes:
                    print(proc.pid)
        else:
            # Use list_jobs() method from JobManager
            for line in shell.job_manager.list_jobs():
                print(line)
        return 0


@builtin
class FgBuiltin(Builtin):
    """Bring job to foreground."""
    
    @property
    def name(self) -> str:
        return "fg"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the fg builtin."""
        # Determine which job to foreground
        if len(args) > 1:
            job_spec = args[1]
            job = shell.job_manager.parse_job_spec(job_spec)
            if job is None:
                print(f"fg: {job_spec}: no such job", file=sys.stderr)
                return 1
        else:
            # No argument - use current job
            if not shell.job_manager.jobs:
                print("fg: no current job", file=sys.stderr)
                return 1
            job = shell.job_manager.current_job
            if job is None:
                print("fg: %+: no such job", file=sys.stderr)
                return 1
        
        # Print the command being resumed
        print(job.command)
        
        # Give it terminal control FIRST before sending SIGCONT
        shell.job_manager.set_foreground_job(job)
        job.foreground = True
        try:
            os.tcsetpgrp(0, job.pgid)
        except OSError as e:
            print(f"fg: can't set terminal control: {e}", file=sys.stderr)
            return 1
        
        # Continue stopped job
        if job.state == JobState.STOPPED:
            # Mark processes as running again
            for proc in job.processes:
                if proc.stopped:
                    proc.stopped = False
            job.state = JobState.RUNNING
            
            # Send SIGCONT to the process group
            os.killpg(job.pgid, signal.SIGCONT)
        
        # Wait for it
        exit_status = shell.job_manager.wait_for_job(job)
        
        # Restore terminal control to shell
        try:
            os.tcsetpgrp(0, os.getpgrp())
        except OSError:
            pass
        
        # Remove job if completed
        if job.state == JobState.DONE:
            shell.job_manager.remove_job(job.job_id)
        
        return exit_status


@builtin
class BgBuiltin(Builtin):
    """Resume job in background."""
    
    @property
    def name(self) -> str:
        return "bg"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the bg builtin."""
        # Determine which job to background
        if len(args) > 1:
            job_spec = args[1]
            job = shell.job_manager.parse_job_spec(job_spec)
            if job is None:
                print(f"bg: {job_spec}: no such job", file=sys.stderr)
                return 1
        else:
            # No argument - use current job
            if not shell.job_manager.jobs:
                print("bg: no current job", file=sys.stderr)
                return 1
            job = shell.job_manager.current_job
            if job is None:
                print("bg: %+: no such job", file=sys.stderr)
                return 1
        
        # Resume job in background
        if job.state == JobState.STOPPED:
            # Mark processes as running again
            for proc in job.processes:
                if proc.stopped:
                    proc.stopped = False
            job.state = JobState.RUNNING
            job.foreground = False
            
            # Send SIGCONT to resume
            os.killpg(job.pgid, signal.SIGCONT)
            print(f"[{job.job_id}]+ {job.command} &")
        return 0


@builtin
class WaitBuiltin(Builtin):
    """Wait for processes to complete."""
    
    @property
    def name(self) -> str:
        return "wait"
    
    @property
    def synopsis(self) -> str:
        return "wait [pid|job_id ...]"
    
    @property
    def description(self) -> str:
        return "Wait for process completion and return exit status"
    
    @property
    def help(self) -> str:
        return """wait: wait [pid|job_id ...]
    Wait for process completion and return exit status.
    
    With no arguments, waits for all currently active child processes.
    With arguments, waits for specified processes or jobs.
    
    Arguments can be:
      pid         Process ID to wait for
      %job_id     Job specification (e.g., %1, %+, %-)
    
    Returns the exit status of the last process waited for.
    If a specified pid is not a child of this shell, returns 127.
    
    Examples:
      wait              # Wait for all background jobs
      wait %1           # Wait for job 1
      wait 1234         # Wait for process 1234
      wait %+ %-        # Wait for current and previous jobs"""
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the wait builtin."""
        if len(args) == 1:
            # No arguments - wait for all children
            return self._wait_for_all(shell)
        else:
            # Wait for specific processes/jobs
            return self._wait_for_specific(args[1:], shell)
    
    def _wait_for_all(self, shell: 'Shell') -> int:
        """Wait for all child processes to complete."""
        exit_status = 0
        
        # Wait for all jobs in job manager
        while shell.job_manager.count_active_jobs() > 0:
            # Get all active jobs
            active_jobs = [job for job in shell.job_manager.jobs.values() 
                          if job.state != JobState.DONE]
            
            if not active_jobs:
                break
                
            for job in active_jobs:
                if job.state == JobState.RUNNING:
                    # Wait for this job
                    status = shell.job_manager.wait_for_job(job)
                    exit_status = status
                    
                    # Clean up completed jobs
                    if job.state == JobState.DONE:
                        shell.job_manager.remove_job(job.job_id)
                elif job.state == JobState.STOPPED:
                    # Don't wait for stopped jobs - they won't complete
                    continue
        
        # Also check for any orphaned processes not in jobs
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                # Extract exit status
                exit_status = self._extract_exit_status(status)
            except (ChildProcessError, OSError):
                break
        
        return exit_status
    
    def _wait_for_specific(self, specs: List[str], shell: 'Shell') -> int:
        """Wait for specific processes or jobs."""
        exit_status = 0
        found_any = False
        
        for spec in specs:
            if spec.startswith('%'):
                # Job specification
                job = shell.job_manager.parse_job_spec(spec)
                if job is None:
                    print(f"wait: {spec}: no such job", file=shell.stderr)
                    exit_status = 127
                    continue
                
                found_any = True
                if job.state == JobState.DONE:
                    # Already completed - get exit status from last process
                    if job.processes:
                        last_proc = job.processes[-1]
                        if last_proc.status is not None:
                            exit_status = self._extract_exit_status(last_proc.status)
                elif job.state == JobState.STOPPED:
                    # Don't wait for stopped jobs
                    print(f"wait: {spec}: job is stopped", file=shell.stderr)
                    exit_status = 1
                else:
                    # Wait for job to complete
                    exit_status = shell.job_manager.wait_for_job(job)
                
                # Clean up if done
                if job.state == JobState.DONE:
                    shell.job_manager.remove_job(job.job_id)
                    
            else:
                # Process ID
                try:
                    pid = int(spec)
                except ValueError:
                    print(f"wait: {spec}: not a valid process id", file=shell.stderr)
                    exit_status = 127
                    continue
                
                # Check if it's a known job
                job = shell.job_manager.get_job_by_pid(pid)
                if job:
                    found_any = True
                    # Wait for the entire job containing this PID
                    if job.state != JobState.DONE:
                        if job.state == JobState.STOPPED:
                            print(f"wait: pid {pid}: job is stopped", file=shell.stderr)
                            exit_status = 1
                        else:
                            exit_status = shell.job_manager.wait_for_job(job)
                    else:
                        # Already done - find exit status
                        for proc in job.processes:
                            if proc.pid == pid and proc.status is not None:
                                exit_status = self._extract_exit_status(proc.status)
                                break
                    
                    # Clean up if done
                    if job.state == JobState.DONE:
                        shell.job_manager.remove_job(job.job_id)
                else:
                    # Try to wait for the specific PID
                    try:
                        _, status = os.waitpid(pid, os.WNOHANG)
                        if status != 0:
                            # Process already terminated
                            found_any = True
                            exit_status = self._extract_exit_status(status)
                        else:
                            # Process still running - wait for it
                            try:
                                _, status = os.waitpid(pid, 0)
                                found_any = True
                                exit_status = self._extract_exit_status(status)
                            except (ChildProcessError, OSError):
                                print(f"wait: pid {pid} is not a child of this shell", 
                                      file=shell.stderr)
                                exit_status = 127
                    except (ChildProcessError, OSError):
                        print(f"wait: pid {pid} is not a child of this shell", 
                              file=shell.stderr)
                        exit_status = 127
        
        return exit_status
    
    def _extract_exit_status(self, status: int) -> int:
        """Extract exit status from waitpid status."""
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            return 128 + os.WTERMSIG(status)
        elif os.WIFSTOPPED(status):
            return 128 + os.WSTOPSIG(status)
        return 0