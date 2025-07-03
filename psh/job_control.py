"""Job control functionality for psh."""

import os
import sys
import signal
import termios
from typing import Dict, List, Optional, Tuple
from enum import Enum


class JobState(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    DONE = "done"


class Process:
    """Represents a single process in a job."""
    def __init__(self, pid: int, command: str):
        self.pid = pid
        self.command = command
        self.status = None  # Will be set by waitpid
        self.stopped = False
        self.completed = False
    
    def update_status(self, status: int):
        """Update process status from waitpid result."""
        self.status = status
        
        if os.WIFSTOPPED(status):
            self.stopped = True
            self.completed = False
        elif os.WIFEXITED(status) or os.WIFSIGNALED(status):
            self.stopped = False
            self.completed = True
        else:
            # Process is running
            self.stopped = False
            self.completed = False


class Job:
    """Represents a job (pipeline or single command)."""
    def __init__(self, job_id: int, pgid: int, command: str):
        self.job_id = job_id
        self.pgid = pgid
        self.command = command
        self.processes: List[Process] = []
        self.state = JobState.RUNNING
        self.foreground = True
        self.notified = False
        self.tmodes = None  # Terminal modes when suspended
    
    def add_process(self, pid: int, command: str):
        """Add a process to this job."""
        self.processes.append(Process(pid, command))
    
    def update_process_status(self, pid: int, status: int):
        """Update status of a specific process."""
        for proc in self.processes:
            if proc.pid == pid:
                proc.update_status(status)
                break
    
    def all_processes_stopped(self) -> bool:
        """Check if all processes in job are stopped."""
        return all(p.stopped for p in self.processes)
    
    def all_processes_completed(self) -> bool:
        """Check if all processes in job are completed."""
        return all(p.completed for p in self.processes)
    
    def any_process_running(self) -> bool:
        """Check if any process is still running."""
        return any(not p.stopped and not p.completed for p in self.processes)
    
    def update_state(self):
        """Update job state based on process states."""
        if self.all_processes_completed():
            self.state = JobState.DONE
        elif self.all_processes_stopped():
            self.state = JobState.STOPPED
        else:
            self.state = JobState.RUNNING
    
    def format_status(self, is_current: bool, is_previous: bool) -> str:
        """Format job status for display."""
        marker = '+' if is_current else '-' if is_previous else ' '
        state_str = {
            JobState.RUNNING: "Running",
            JobState.STOPPED: "Stopped",
            JobState.DONE: "Done"
        }[self.state]
        
        return f"[{self.job_id}]{marker}  {state_str:<12} {self.command}"


class JobManager:
    """Manages all jobs in the shell."""
    def __init__(self):
        self.jobs: Dict[int, Job] = {}
        self.next_job_id = 1
        self.current_job: Optional[Job] = None
        self.previous_job: Optional[Job] = None
        self.shell_pgid = os.getpgrp()
        self.shell_tmodes = None
        self.shell_state = None  # Will be set by shell
        
        # Save shell's terminal modes
        try:
            self.shell_tmodes = termios.tcgetattr(0)
        except:
            pass
    
    def set_shell_state(self, state):
        """Set reference to shell state for option checking."""
        self.shell_state = state
    
    def create_job(self, pgid: int, command: str) -> Job:
        """Create a new job."""
        job = Job(self.next_job_id, pgid, command)
        self.jobs[self.next_job_id] = job
        self.next_job_id += 1
        return job
    
    def remove_job(self, job_id: int):
        """Remove a job from tracking."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            
            # Update current/previous references
            if job == self.current_job:
                self.current_job = self.previous_job
                self.previous_job = None
            elif job == self.previous_job:
                self.previous_job = None
            
            del self.jobs[job_id]
    
    def get_job(self, job_id: int) -> Optional[Job]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def get_job_by_pid(self, pid: int) -> Optional[Job]:
        """Find job containing the given PID."""
        for job in self.jobs.values():
            for proc in job.processes:
                if proc.pid == pid:
                    return job
        return None
    
    def get_job_by_pgid(self, pgid: int) -> Optional[Job]:
        """Find job by process group ID."""
        for job in self.jobs.values():
            if job.pgid == pgid:
                return job
        return None
    
    def set_foreground_job(self, job: Optional[Job]):
        """Set the current foreground job."""
        # Save current job's terminal modes if it exists
        if self.current_job and self.current_job != job:
            try:
                self.current_job.tmodes = termios.tcgetattr(0)
            except:
                pass
            self.previous_job = self.current_job
        
        self.current_job = job
        
        # Restore job's terminal modes if it has them
        if job and job.tmodes:
            try:
                termios.tcsetattr(0, termios.TCSADRAIN, job.tmodes)
            except:
                pass
        elif job is None and self.shell_tmodes:
            # Restore shell's terminal modes
            try:
                termios.tcsetattr(0, termios.TCSADRAIN, self.shell_tmodes)
            except:
                pass
    
    def count_active_jobs(self) -> int:
        """Count jobs that are running or stopped."""
        return sum(1 for job in self.jobs.values() 
                  if job.state != JobState.DONE)
    
    def notify_completed_jobs(self):
        """Print notifications for completed background jobs."""
        completed = []
        for job_id, job in list(self.jobs.items()):
            if job.state == JobState.DONE and not job.notified and not job.foreground:
                print(f"\n[{job.job_id}]+  Done                    {job.command}")
                job.notified = True
                completed.append(job_id)
        
        # Remove completed jobs after notification
        for job_id in completed:
            self.remove_job(job_id)
    
    def notify_stopped_jobs(self):
        """Print notifications for newly stopped jobs."""
        for job_id, job in list(self.jobs.items()):
            if job.state == JobState.STOPPED and not job.notified:
                # Mark with + if it's the current job
                marker = '+' if job == self.current_job else '-' if job == self.previous_job else ' '
                print(f"[{job.job_id}]{marker}  Stopped                 {job.command}")
                job.notified = True
    
    def list_jobs(self) -> List[str]:
        """Get formatted list of all jobs."""
        lines = []
        for job_id in sorted(self.jobs.keys()):
            job = self.jobs[job_id]
            is_current = (job == self.current_job)
            is_previous = (job == self.previous_job)
            lines.append(job.format_status(is_current, is_previous))
        return lines
    
    def parse_job_spec(self, spec: str) -> Optional[Job]:
        """Parse job specification like %1, %+, %-, %string."""
        if not spec:
            return self.current_job
        
        if not spec.startswith('%'):
            # Try to parse as PID
            try:
                pid = int(spec)
                return self.get_job_by_pid(pid)
            except ValueError:
                return None
        
        spec = spec[1:]  # Remove %
        
        if spec == '+' or spec == '' or spec == '%':
            return self.current_job
        elif spec == '-':
            return self.previous_job
        elif spec.isdigit():
            job_id = int(spec)
            return self.get_job(job_id)
        else:
            # Match by command prefix
            for job in self.jobs.values():
                if job.command.startswith(spec):
                    return job
            return None
    
    def wait_for_job(self, job: Job, collect_all_statuses: bool = False) -> int:
        """Wait for a job to complete or stop.
        
        Args:
            job: The job to wait for
            collect_all_statuses: If True, collect exit codes from all processes
            
        Returns:
            Exit status (or list of statuses if collect_all_statuses is True)
        """
        exit_status = 0
        all_exit_statuses = []
        
        while job.any_process_running():
            try:
                # Wait for any child in the job's process group
                pid, status = os.waitpid(-job.pgid, os.WUNTRACED)
                
                # Update process status
                job.update_process_status(pid, status)
                
                # Extract exit status
                proc_exit_status = 0
                if os.WIFEXITED(status):
                    proc_exit_status = os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    proc_exit_status = 128 + os.WTERMSIG(status)
                elif os.WIFSTOPPED(status):
                    proc_exit_status = 128 + os.WSTOPSIG(status)
                
                # Find which process this is
                for i, proc in enumerate(job.processes):
                    if proc.pid == pid:
                        if collect_all_statuses:
                            # Store exit status at the correct index
                            while len(all_exit_statuses) <= i:
                                all_exit_statuses.append(0)
                            all_exit_statuses[i] = proc_exit_status
                        
                        # If this was the last process in the pipeline
                        if i == len(job.processes) - 1:
                            exit_status = proc_exit_status
                
            except OSError:
                break
        
        # If processes were already reaped by SIGCHLD handler, get exit status from stored status
        if not job.any_process_running() and job.processes:
            for i, proc in enumerate(job.processes):
                if proc.completed and proc.status is not None:
                    status = proc.status
                    proc_exit_status = 0
                    if os.WIFEXITED(status):
                        proc_exit_status = os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        proc_exit_status = 128 + os.WTERMSIG(status)
                    elif os.WIFSTOPPED(status):
                        proc_exit_status = 128 + os.WSTOPSIG(status)
                    
                    if collect_all_statuses:
                        while len(all_exit_statuses) <= i:
                            all_exit_statuses.append(0)
                        all_exit_statuses[i] = proc_exit_status
                    
                    # Last process determines default exit status
                    if i == len(job.processes) - 1:
                        exit_status = proc_exit_status
        
        # Update job state
        old_state = job.state
        job.update_state()
        
        # If notify option is enabled and job just completed, notify immediately
        if (self.shell_state and self.shell_state.options.get('notify', False) and
            old_state != JobState.DONE and job.state == JobState.DONE and
            not job.foreground and not job.notified):
            print(f"\n[{job.job_id}]+  Done                    {job.command}")
            job.notified = True
        
        if collect_all_statuses:
            return all_exit_statuses
        return exit_status