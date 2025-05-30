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
        if not shell.job_manager.jobs:
            print("fg: no current job", file=sys.stderr)
            return 1
        
        # Determine which job to foreground
        if len(args) > 1:
            job_spec = args[1]
            job_id = shell.job_manager.parse_job_spec(job_spec)
            if job_id is None:
                print(f"fg: {job_spec}: no such job", file=sys.stderr)
                return 1
        else:
            # No argument - use current job
            if shell.job_manager.current_job is None:
                print("fg: %+: no such job", file=sys.stderr)
                return 1
            job_id = shell.job_manager.current_job.job_id
        
        job = shell.job_manager.get_job(job_id)
        if not job:
            print(f"fg: %{job_id}: no such job", file=sys.stderr)
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
        if not shell.job_manager.jobs:
            print("bg: no current job", file=sys.stderr)
            return 1
        
        # Determine which job to background
        if len(args) > 1:
            job_spec = args[1]
            job_id = shell.job_manager.parse_job_spec(job_spec)
            if job_id is None:
                print(f"bg: {job_spec}: no such job", file=sys.stderr)
                return 1
        else:
            # No argument - use current job
            if shell.job_manager.current_job is None:
                print("bg: %+: no such job", file=sys.stderr)
                return 1
            job_id = shell.job_manager.current_job.job_id
        
        job = shell.job_manager.get_job(job_id)
        if not job:
            print(f"bg: %{job_id}: no such job", file=sys.stderr)
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