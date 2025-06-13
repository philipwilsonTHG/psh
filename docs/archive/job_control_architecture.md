# Job Control Architecture for psh

## Overview

Job control allows users to manage multiple processes from a single terminal session. It includes the ability to:
- Suspend foreground processes (Ctrl-Z)
- Move jobs between foreground and background
- List active jobs
- Resume suspended jobs
- Kill jobs by job ID

## Current State Analysis

psh already has several foundation elements for job control:

1. **Process Groups**: Pipeline commands create process groups (`setpgid`)
2. **Terminal Control**: Foreground process group management (`tcsetpgrp`)
3. **Signal Handling**: Basic SIGINT handling, SIGTSTP ignored
4. **Background Execution**: Background commands with `&` operator
5. **Exit Status Tracking**: Proper handling of signal-terminated processes

## Architectural Recommendations

### 1. Job Table Structure

Create a `JobManager` class to track all jobs:

```python
class Job:
    def __init__(self, job_id: int, pgid: int, command: str):
        self.job_id = job_id          # Job number (1, 2, 3...)
        self.pgid = pgid              # Process group ID
        self.command = command        # Original command string
        self.processes = []           # List of (pid, command) tuples
        self.state = 'running'        # 'running', 'stopped', 'done'
        self.foreground = True        # True if started in foreground
        self.notified = False         # For notification of state changes

class JobManager:
    def __init__(self):
        self.jobs = {}                # job_id -> Job
        self.next_job_id = 1
        self.current_job = None       # Current foreground job
        self.previous_job = None      # Previous job (for %- notation)
```

### 2. Process State Management

Extend signal handling to support job control:

```python
# In Shell.__init__
signal.signal(signal.SIGTSTP, signal.SIG_DFL)  # Allow Ctrl-Z
signal.signal(signal.SIGTTIN, signal.SIG_IGN)  # Ignore background tty input
signal.signal(signal.SIGTTOU, signal.SIG_IGN)  # Keep ignoring background tty output
signal.signal(signal.SIGCHLD, self._handle_sigchld)  # Track child state changes
```

### 3. Job Creation and Tracking

Modify `execute_pipeline` to register jobs:

```python
def execute_pipeline(self, pipeline: Pipeline):
    # ... existing code ...
    
    # Create job entry before forking
    if len(pipeline.commands) > 1 or pipeline.commands[0].background:
        job = self.job_manager.create_job(pgid, command_string)
        
    # ... fork processes ...
    
    # Add processes to job
    for pid, cmd in zip(pids, pipeline.commands):
        job.add_process(pid, cmd.args[0] if cmd.args else '')
    
    # Handle foreground vs background
    if not pipeline.commands[-1].background:
        self.job_manager.set_foreground_job(job)
        # Wait for job
        status = self._wait_for_job(job)
    else:
        print(f"[{job.job_id}] {job.pgid}")
        job.foreground = False
```

### 4. Built-in Commands for Job Control

Add new built-in commands:

```python
def _builtin_jobs(self, args):
    """List active jobs"""
    for job_id, job in sorted(self.job_manager.jobs.items()):
        status = '+' if job == self.job_manager.current_job else \
                 '-' if job == self.job_manager.previous_job else ' '
        state = 'Running' if job.state == 'running' else 'Stopped'
        print(f"[{job.job_id}]{status}  {state:8}  {job.command}")
    return 0

def _builtin_fg(self, args):
    """Bring job to foreground"""
    job = self._get_job_from_spec(args[1] if len(args) > 1 else '%+')
    if not job:
        return 1
    
    # Continue stopped job
    if job.state == 'stopped':
        os.killpg(job.pgid, signal.SIGCONT)
    
    # Give it terminal control
    self.job_manager.set_foreground_job(job)
    os.tcsetpgrp(0, job.pgid)
    
    # Wait for it
    return self._wait_for_job(job)

def _builtin_bg(self, args):
    """Resume job in background"""
    job = self._get_job_from_spec(args[1] if len(args) > 1 else '%+')
    if not job:
        return 1
    
    if job.state == 'stopped':
        job.state = 'running'
        job.foreground = False
        os.killpg(job.pgid, signal.SIGCONT)
        print(f"[{job.job_id}]+ {job.command} &")
    return 0
```

### 5. Job Specification Parsing

Support job specifications like `%1`, `%+`, `%-`, `%string`:

```python
def _get_job_from_spec(self, spec: str) -> Optional[Job]:
    if not spec.startswith('%'):
        # Try to parse as PID
        try:
            pid = int(spec)
            return self.job_manager.get_job_by_pid(pid)
        except ValueError:
            print(f"fg: {spec}: no such job", file=sys.stderr)
            return None
    
    spec = spec[1:]  # Remove %
    
    if spec == '+' or spec == '':
        return self.job_manager.current_job
    elif spec == '-':
        return self.job_manager.previous_job
    elif spec.isdigit():
        job_id = int(spec)
        return self.job_manager.jobs.get(job_id)
    else:
        # Match by command prefix
        for job in self.job_manager.jobs.values():
            if job.command.startswith(spec):
                return job
        print(f"fg: %{spec}: no such job", file=sys.stderr)
        return None
```

### 6. SIGCHLD Handler

Track job state changes:

```python
def _handle_sigchld(self, signum, frame):
    """Handle child process state changes"""
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
                
            job = self.job_manager.get_job_by_pid(pid)
            if job:
                job.update_process_status(pid, status)
                
                # Check if entire job is done/stopped
                if job.all_processes_done():
                    job.state = 'done'
                    if not job.foreground:
                        # Notify user of background job completion
                        print(f"\n[{job.job_id}]+  Done                    {job.command}")
                elif job.all_processes_stopped():
                    job.state = 'stopped'
                    if job.foreground:
                        # Notify user of stopped foreground job
                        print(f"\n[{job.job_id}]+  Stopped                 {job.command}")
                        # Return control to shell
                        os.tcsetpgrp(0, os.getpgrp())
        except OSError:
            break
```

### 7. Interactive Shell Modifications

Update the main shell loop to handle stopped jobs:

```python
def interactive_loop(self):
    # ... existing code ...
    
    while True:
        try:
            # Check for completed background jobs
            self.job_manager.notify_completed_jobs()
            
            # Show prompt with job count if jobs exist
            active_jobs = self.job_manager.count_active_jobs()
            if active_jobs > 0:
                prompt = f'psh[{active_jobs}]$ '
            else:
                prompt = 'psh$ '
            
            # ... rest of loop ...
        except KeyboardInterrupt:
            # ... existing handling ...
```

### 8. Terminal Modes

Save and restore terminal modes when switching between foreground jobs:

```python
import termios
import tty

class JobManager:
    def __init__(self):
        # ... existing init ...
        self.shell_tmodes = termios.tcgetattr(0)  # Save shell's terminal modes
    
    def set_foreground_job(self, job):
        # Save current terminal modes
        if self.current_job:
            self.current_job.tmodes = termios.tcgetattr(0)
        
        self.previous_job = self.current_job
        self.current_job = job
        
        # Restore job's terminal modes if it has them
        if hasattr(job, 'tmodes'):
            termios.tcsetattr(0, termios.TCSADRAIN, job.tmodes)
```

## Implementation Order

1. **Phase 1**: Job table and basic tracking
   - Implement `JobManager` and `Job` classes
   - Track all background processes
   - Implement `jobs` built-in

2. **Phase 2**: Signal handling
   - Enable SIGTSTP handling
   - Implement SIGCHLD handler
   - Handle stopped processes

3. **Phase 3**: Foreground/background control
   - Implement `fg` built-in
   - Implement `bg` built-in
   - Handle terminal control transfer

4. **Phase 4**: Job specifications
   - Parse job specs (`%1`, `%+`, etc.)
   - Support kill with job specs
   - Add wait built-in for job specs

5. **Phase 5**: Polish and edge cases
   - Terminal mode management
   - Notification improvements
   - Handle orphaned process groups
   - Implement `disown` built-in

## Testing Strategy

1. **Unit tests** for JobManager operations
2. **Integration tests** for job control scenarios:
   - Start job, stop it, resume in foreground/background
   - Multiple simultaneous jobs
   - Pipeline job control
   - Terminal control verification
3. **Manual testing** of interactive features:
   - Ctrl-Z behavior
   - Terminal mode preservation
   - Job notifications

## Compatibility Notes

- Follow POSIX job control semantics where possible
- Support both `%` notation and PID arguments
- Ensure compatibility with existing pipeline and background execution code
- Maintain clear error messages for job control operations