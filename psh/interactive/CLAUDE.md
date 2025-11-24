# Interactive & Job Control Subsystem

This document provides guidance for working with the PSH interactive shell and job control subsystem.

## Architecture Overview

The interactive subsystem handles the shell's REPL loop, history, completion, and job control for managing background processes.

```
Interactive Shell
       ↓
┌──────┴──────┬──────────┬──────────┬──────────┐
↓             ↓          ↓          ↓          ↓
REPL       History   Completion  Prompt    Signal
Loop       Manager    Manager   Manager   Manager
                                              ↓
                                        Job Control
                                        (job_control.py)
```

## Key Files

### Interactive (`psh/interactive/`)

| File | Purpose |
|------|---------|
| `repl_loop.py` | `REPLLoop` - main Read-Eval-Print Loop |
| `history_manager.py` | `HistoryManager` - command history |
| `completion_manager.py` | `CompletionManager` - tab completion |
| `prompt_manager.py` | `PromptManager` - prompt generation |
| `signal_manager.py` | `SignalManager` - signal handling, SIGCHLD |
| `base.py` | `InteractiveComponent` base class |

### Job Control (`psh/job_control.py`)

| Class | Purpose |
|-------|---------|
| `JobState` | Enum: RUNNING, STOPPED, DONE |
| `Process` | Individual process in a job |
| `Job` | Pipeline or single command |
| `JobManager` | Central job management |

## Core Patterns

### 1. Job State Machine

```python
class JobState(Enum):
    RUNNING = "running"   # Job is executing
    STOPPED = "stopped"   # Job suspended (Ctrl+Z)
    DONE = "done"         # Job completed
```

State transitions:
```
RUNNING → STOPPED (SIGTSTP)
STOPPED → RUNNING (fg/bg)
RUNNING → DONE (exit/signal)
STOPPED → DONE (kill)
```

### 2. Process Group Management

```python
class Job:
    def __init__(self, job_id: int, pgid: int, command: str):
        self.job_id = job_id
        self.pgid = pgid          # Process group ID
        self.command = command
        self.processes = []       # List of Process
        self.state = JobState.RUNNING
        self.foreground = True
        self.tmodes = None        # Terminal modes when suspended
```

### 3. Job Manager

```python
class JobManager:
    def __init__(self):
        self.jobs: Dict[int, Job] = {}
        self.next_job_id = 1
        self.current_job = None    # Most recent job (%)
        self.previous_job = None   # Previous job (%-)
        self.shell_pgid = os.getpgrp()
        self.shell_tmodes = None   # Shell's terminal modes
```

## Job Specification Parsing

| Spec | Meaning |
|------|---------|
| `%n` | Job number n |
| `%+` or `%%` | Current job |
| `%-` | Previous job |
| `%string` | Job starting with string |
| `%?string` | Job containing string |

```python
def parse_job_spec(self, spec: str) -> Optional[Job]:
    if spec == '%' or spec == '%%' or spec == '%+':
        return self.current_job
    elif spec == '%-':
        return self.previous_job
    elif spec.startswith('%') and spec[1:].isdigit():
        return self.get_job(int(spec[1:]))
```

## Interactive Components

### REPL Loop

```python
class REPLLoop:
    def run(self):
        while True:
            try:
                # 1. Show prompt
                prompt = self.prompt_manager.get_prompt()

                # 2. Read input (with readline)
                line = input(prompt)

                # 3. Add to history
                self.history_manager.add(line)

                # 4. Execute
                self.shell.execute(line)

                # 5. Process signals, notify jobs
                self.signal_manager.process_pending()
                self.shell.job_manager.notify_completed_jobs()

            except EOFError:
                break
            except KeyboardInterrupt:
                print()  # Newline after ^C
```

### Signal Handling

```python
class SignalManager:
    def __init__(self):
        # Self-pipe for safe signal handling
        self._read_fd, self._write_fd = os.pipe()

    def setup_handlers(self):
        signal.signal(signal.SIGCHLD, self._sigchld_handler)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Ignore in shell

    def _sigchld_handler(self, signum, frame):
        # Write to pipe to wake up main loop
        os.write(self._write_fd, b'\x00')

    def process_pending(self):
        # Reap children, update job states
        self._reap_children()
```

## Common Tasks

### Adding a Job Control Builtin

1. Create builtin in `psh/builtins/`:
```python
@builtin
class MyJobBuiltin(Builtin):
    name = "myjob"

    def execute(self, args, shell):
        job_manager = shell.job_manager

        # Parse job spec
        if len(args) > 1:
            job = job_manager.parse_job_spec(args[1])
        else:
            job = job_manager.current_job

        if not job:
            self.error("no such job", shell)
            return 1

        # Do something with job
        return 0
```

### Foreground a Job

```python
def foreground_job(self, job: Job):
    # 1. Give terminal control to job's process group
    try:
        os.tcsetpgrp(0, job.pgid)
    except OSError:
        pass

    # 2. Restore job's terminal modes
    if job.tmodes:
        termios.tcsetattr(0, termios.TCSADRAIN, job.tmodes)

    # 3. Continue stopped processes
    os.killpg(job.pgid, signal.SIGCONT)
    job.state = JobState.RUNNING
    job.foreground = True

    # 4. Wait for job
    self.wait_for_job(job)

    # 5. Return terminal to shell
    os.tcsetpgrp(0, self.shell_pgid)
    termios.tcsetattr(0, termios.TCSADRAIN, self.shell_tmodes)
```

### Background a Job

```python
def background_job(self, job: Job):
    # Continue stopped processes in background
    os.killpg(job.pgid, signal.SIGCONT)
    job.state = JobState.RUNNING
    job.foreground = False
    print(f"[{job.job_id}]+ {job.command} &")
```

## Key Implementation Details

### Terminal Control Transfer

```python
def transfer_terminal_control(self, pgid: int):
    """Give terminal control to a process group."""
    try:
        os.tcsetpgrp(0, pgid)  # 0 = stdin
    except OSError as e:
        # May fail if not controlling terminal
        pass
```

### Reaping Children

```python
def _reap_children(self):
    """Collect terminated children and update job states."""
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG | os.WUNTRACED)
            if pid == 0:
                break

            job = self.get_job_by_pid(pid)
            if job:
                job.update_process_status(pid, status)
                job.update_state()

        except ChildProcessError:
            break  # No more children
```

### Job Notification

```python
def notify_completed_jobs(self):
    """Print notifications for completed background jobs."""
    for job in list(self.jobs.values()):
        if job.state == JobState.DONE and not job.notified:
            if not job.foreground:
                print(f"\n[{job.job_id}]+  Done  {job.command}")
            job.notified = True
            self.remove_job(job.job_id)
```

## Testing

```bash
# Run job control tests
python -m pytest tests/unit/job_control/ -v

# Run interactive tests (may require special handling)
python -m pytest tests/system/interactive/ -v

# Test interactively
python -m psh
$ sleep 10 &
[1] 12345
$ jobs
[1]+  Running  sleep 10 &
$ fg %1
```

## Common Pitfalls

1. **Terminal Control**: Only the foreground process group can read from terminal.

2. **Signal Safety**: Only use async-signal-safe functions in signal handlers.

3. **Process Group Setup**: Child must call `setpgid()` before parent continues.

4. **Terminal Modes**: Save/restore terminal modes when suspending/resuming.

5. **Zombie Prevention**: Always reap children with `waitpid()`.

6. **Race Conditions**: Use self-pipe pattern for signal handling.

## Debug Options

```bash
python -m psh --debug-exec  # Debug process groups and signals
```

## Integration Points

### With Executor (`psh/executor/`)

- `ProcessLauncher` creates process groups
- Jobs registered with `JobManager` after fork
- Terminal control transferred for foreground jobs

### With Shell State (`psh/core/state.py`)

- `state.last_bg_pid` updated for `$!`
- `state.supports_job_control` checked before terminal ops
- `state.options['monitor']` enables job notifications

### With Builtins (`psh/builtins/`)

- `jobs`, `fg`, `bg`, `wait`, `disown`, `kill` interact with `JobManager`
- Access via `shell.job_manager`
