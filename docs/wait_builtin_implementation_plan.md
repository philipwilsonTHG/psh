# Wait Builtin Implementation Plan for PSH

## Overview

The `wait` builtin is a POSIX-required command that allows a shell to wait for child processes to complete. It's essential for process synchronization in shell scripts and interactive use.

## POSIX Requirements

### Syntax
```
wait [pid|job_id ...]
```

### Behavior Specifications

1. **No arguments**: Wait for all child processes to terminate
2. **With arguments**: Wait for specified processes/jobs to terminate
3. **Exit status**: Returns the exit status of the last process waited for
4. **Job specifications**: Support `%job_id` notation for job control
5. **Already-terminated processes**: Should immediately return their exit status
6. **Invalid PIDs**: Should continue waiting for valid PIDs, return non-zero

## Current PSH Architecture Analysis

### Existing Components

1. **JobManager** (`psh/job_control.py`)
   - Already tracks jobs and processes
   - Has `wait_for_job()` method that handles process waiting
   - Manages job states (RUNNING, STOPPED, DONE)
   - Handles process group management

2. **Process Class** (`psh/job_control.py`)
   - Tracks individual process states
   - Stores exit status from `waitpid()`
   - Handles stopped/completed states

3. **Signal Handling** (`psh/interactive/signal_manager.py`)
   - SIGCHLD handler already reaps child processes
   - Updates job states when children change

4. **Background Process Tracking**
   - `state.last_bg_pid` tracks most recent background process
   - Jobs are properly registered in JobManager

## Implementation Design

### 1. Create WaitBuiltin Class

Location: `psh/builtins/job_control.py`

```python
@builtin
class WaitBuiltin(Builtin):
    """Wait for processes to complete."""
    
    @property
    def name(self) -> str:
        return "wait"
    
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
    If a specified pid is not a child of this shell, returns 127."""
```

### 2. Implementation Details

#### 2.1 Main execute() Method

```python
def execute(self, args: List[str], shell: 'Shell') -> int:
    """Execute the wait builtin."""
    if len(args) == 1:
        # No arguments - wait for all children
        return self._wait_for_all(shell)
    else:
        # Wait for specific processes/jobs
        return self._wait_for_specific(args[1:], shell)
```

#### 2.2 Wait for All Children

```python
def _wait_for_all(self, shell: 'Shell') -> int:
    """Wait for all child processes to complete."""
    exit_status = 0
    
    # Wait for all jobs in job manager
    while shell.job_manager.count_active_jobs() > 0:
        # Get all active jobs
        active_jobs = [job for job in shell.job_manager.jobs.values() 
                      if job.state != JobState.DONE]
        
        for job in active_jobs:
            if job.state == JobState.RUNNING:
                # Wait for this job
                status = shell.job_manager.wait_for_job(job)
                exit_status = status
                
                # Clean up completed jobs
                if job.state == JobState.DONE:
                    shell.job_manager.remove_job(job.job_id)
    
    # Also check for any orphaned processes not in jobs
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            # Extract exit status
            if os.WIFEXITED(status):
                exit_status = os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                exit_status = 128 + os.WTERMSIG(status)
        except ChildProcessError:
            break
    
    return exit_status
```

#### 2.3 Wait for Specific Processes

```python
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
                    exit_status = shell.job_manager.wait_for_job(job)
                else:
                    # Already done - find exit status
                    for proc in job.processes:
                        if proc.pid == pid and proc.status is not None:
                            exit_status = self._extract_exit_status(proc.status)
                            break
            else:
                # Try to wait for the specific PID
                try:
                    _, status = os.waitpid(pid, os.WNOHANG)
                    if status != 0:
                        found_any = True
                        exit_status = self._extract_exit_status(status)
                    else:
                        # Process still running - wait for it
                        _, status = os.waitpid(pid, 0)
                        found_any = True
                        exit_status = self._extract_exit_status(status)
                except ChildProcessError:
                    print(f"wait: pid {pid} is not a child of this shell", 
                          file=shell.stderr)
                    exit_status = 127
    
    return exit_status
```

#### 2.4 Helper Methods

```python
def _extract_exit_status(self, status: int) -> int:
    """Extract exit status from waitpid status."""
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    elif os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    elif os.WIFSTOPPED(status):
        return 128 + os.WSTOPSIG(status)
    return 0
```

### 3. Integration Points

#### 3.1 JobManager Enhancements

Add method to check for orphaned processes:

```python
def has_orphaned_processes(self) -> bool:
    """Check if there are child processes not tracked as jobs."""
    try:
        pid, _ = os.waitpid(-1, os.WNOHANG)
        return pid > 0
    except ChildProcessError:
        return False
```

#### 3.2 Handle Stopped Jobs

The wait builtin should handle stopped jobs appropriately:
- Don't wait for STOPPED jobs (they're not going to complete)
- Only wait for RUNNING jobs
- Report if all remaining jobs are stopped

### 4. Test Cases

#### 4.1 Basic Tests

1. **Wait with no arguments**
   ```bash
   sleep 2 &
   sleep 3 &
   wait
   echo $?  # Should be 0
   ```

2. **Wait for specific PID**
   ```bash
   sleep 2 &
   pid=$!
   wait $pid
   echo $?  # Should be 0
   ```

3. **Wait for specific job**
   ```bash
   sleep 2 &
   wait %1
   echo $?  # Should be 0
   ```

4. **Wait for multiple processes**
   ```bash
   sleep 2 &
   pid1=$!
   sleep 3 &
   pid2=$!
   wait $pid1 $pid2
   echo $?  # Exit status of last process
   ```

#### 4.2 Error Cases

1. **Invalid PID**
   ```bash
   wait 99999
   echo $?  # Should be 127
   ```

2. **Non-child process**
   ```bash
   wait 1  # init process
   echo $?  # Should be 127
   ```

3. **Invalid job spec**
   ```bash
   wait %99
   echo $?  # Should be 127
   ```

#### 4.3 Edge Cases

1. **Already completed process**
   ```bash
   sleep 0.1 &
   pid=$!
   sleep 1  # Let it complete
   wait $pid  # Should return immediately
   echo $?
   ```

2. **Mixed valid/invalid specs**
   ```bash
   sleep 2 &
   pid=$!
   wait $pid 99999  # One valid, one invalid
   echo $?  # Should be 127 (due to invalid)
   ```

3. **Stopped jobs**
   ```bash
   sleep 10 &
   kill -STOP %1
   wait  # Should not hang on stopped job
   ```

### 5. Implementation Steps

1. **Create basic WaitBuiltin class** in `psh/builtins/job_control.py`
2. **Implement no-argument wait** (wait for all children)
3. **Add PID-specific waiting**
4. **Add job specification support** (%1, %+, etc.)
5. **Handle error cases** (invalid PIDs, non-children)
6. **Add comprehensive tests** in `tests/test_wait_builtin.py`
7. **Update documentation**:
   - Add to builtin help system
   - Update POSIX compliance docs
   - Add to user guide

### 6. Special Considerations

1. **SIGCHLD Interaction**: The wait builtin must work correctly with the SIGCHLD handler that's already reaping children

2. **Race Conditions**: Handle cases where a process terminates between checking and waiting

3. **Stopped vs. Terminated**: Don't wait indefinitely for stopped jobs

4. **Exit Status Propagation**: Correctly extract and return exit statuses

5. **Zombie Prevention**: Ensure all waited processes are properly reaped

### 7. Documentation Updates

1. **POSIX Compliance**:
   - Update compliance percentage for built-in commands
   - Mark wait as implemented

2. **User Guide**:
   - Add wait command documentation
   - Include examples of common usage patterns

3. **Help Text**:
   - Comprehensive help with examples
   - Clear explanation of job specifications

## Summary

The wait builtin implementation will leverage PSH's existing job control infrastructure, particularly the JobManager and its process tracking capabilities. The implementation will be straightforward since most of the heavy lifting is already done by the job control system. The main challenges will be handling edge cases correctly and ensuring POSIX-compliant behavior in all scenarios.