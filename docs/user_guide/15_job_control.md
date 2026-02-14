# Chapter 15: Job Control

Job control allows you to manage multiple processes from a single terminal session. PSH provides comprehensive job control features in interactive mode, enabling you to run commands in the background, suspend running processes, and switch between multiple tasks efficiently.

## 15.1 Understanding Job Control

Job control is a feature that allows you to control the execution of processes, particularly useful when working interactively with long-running commands.

### What is a Job?

```bash
# A job is a pipeline of one or more processes
psh$ sleep 100              # Single process job
psh$ ls | grep txt | wc -l  # Pipeline job (3 processes)

# Jobs can be:
- Foreground: Has terminal control, receives keyboard input
- Background: Runs without terminal control
- Stopped: Suspended, not executing

# Each job has:
- Job ID: Sequential number assigned by shell
- Process Group ID: Groups related processes
- State: Running, stopped, or done
- Command: The command line that created it
```

### Enabling Job Control

```bash
# Job control is enabled by default in interactive mode
psh$ echo "Interactive shell with job control"

# Job control is disabled in:
- Non-interactive scripts
- Pipes and command substitution
- When shell is not connected to a terminal

# Check if job control is available
psh$ if [ -t 0 ] && [ -n "$PS1" ]; then
>     echo "Job control enabled"
> fi
```

### Process Groups and Sessions

```bash
# Process relationships
- Session: Group of process groups
- Process Group: Group of related processes
- Shell creates new process group for each pipeline

# View process information
psh$ ps -o pid,ppid,pgid,sid,cmd
  PID  PPID  PGID   SID CMD
12345 12340 12345 12340 psh
12350 12345 12350 12340 sleep 100

# Each pipeline gets its own process group
psh$ sleep 100 | sleep 200 &
[1] 12351
# Both sleep processes share process group 12351
```

## 15.2 Running Jobs in the Background

Background jobs run without terminal control, allowing you to continue using the shell.

### Starting Background Jobs

```bash
# Run command in background with &
psh$ sleep 300 &
[1] 12345

# Background job notification format:
# [job_id] process_group_id

# Multiple background jobs
psh$ compile_project &
[1] 12346
psh$ download_file &
[2] 12347
psh$ process_data &
[3] 12348

# Background pipelines
psh$ find / -name "*.log" 2>/dev/null | grep error > errors.txt &
[4] 12349

# Complex background commands
psh$ (cd /project && make clean && make all) &
[5] 12350
```

### Background Job Behavior

```bash
# Background jobs cannot read from terminal
psh$ cat &
[1] 12351
[1]+ Stopped     cat
# Job stopped when trying to read input

# Redirect input for background jobs
psh$ wc -l < input.txt &
[1] 12352

# Background jobs can write to terminal
psh$ echo "Background output" &
[1] 12353
Background output
[1]+ Done        echo "Background output"

# Prevent output interference
psh$ long_command > output.log 2>&1 &
[1] 12354
```

### Job Completion Notifications

```bash
# Completion shown before next prompt
psh$ sleep 5 &
[1] 12355
psh$ # Wait a bit and press Enter
[1]+ Done        sleep 5
psh$ 

# Exit status in notifications
psh$ true &
[1] 12356
psh$ false &
[2] 12357
psh$ 
[1]- Done        true
[2]+ Exit 1      false

# Multiple completions
psh$ sleep 2 & sleep 3 & sleep 4 &
[1] 12358
[2] 12359
[3] 12360
psh$ # Wait and press Enter
[1]   Done        sleep 2
[2]-  Done        sleep 3
[3]+  Done        sleep 4
```

## 15.3 The jobs Command

The `jobs` command displays information about active jobs in the current shell.

### Basic jobs Usage

```bash
# List all jobs
psh$ jobs
[1]   Running              sleep 300 &
[2]+  Stopped              vim file.txt
[3]-  Running              make -j4 &

# Job status indicators:
# +  Current job (most recent)
# -  Previous job
# (blank) Other jobs

# Job states:
# Running   - Actively executing
# Stopped   - Suspended (Ctrl-Z)
# Done      - Completed (shown once)
```

### Job Information

```bash
# Detailed job listing
psh$ sleep 100 &
[1] 12361
psh$ vim file.txt
^Z
[2]+ Stopped     vim file.txt
psh$ make &
[3] 12363
psh$ jobs
[1]   Running              sleep 100 &
[2]+  Stopped              vim file.txt
[3]-  Running              make &

# Job IDs are sequential
# Reused after jobs complete
# Current job (+) is most recent
# Previous job (-) is second most recent
```

### Using Job Information

```bash
# Count active jobs
psh$ jobs | wc -l
3

# Check for stopped jobs
psh$ if jobs | grep -q Stopped; then
>     echo "You have stopped jobs"
> fi
You have stopped jobs

# List only running jobs
psh$ jobs | grep Running
[1]   Running              sleep 100 &
[3]-  Running              make &

# Get job IDs
psh$ jobs | awk -F'[][]' '{print $2}'
1
2
3
```

## 15.4 Job Specifications

Job specifications (jobspecs) provide ways to refer to specific jobs.

### Job Specification Syntax

```bash
# Job specification formats:
%n        # Job number n
%+        # Current job
%%        # Also current job
%-        # Previous job
%string   # Job whose command starts with string
n         # Process ID n (not jobspec)

# Examples:
psh$ sleep 300 &
[1] 12364
psh$ vim file.txt &
[2] 12365
psh$ make -j4 &
[3] 12366

# Reference by job number
psh$ jobs %1
[1]   Running              sleep 300 &

# Reference current job
psh$ jobs %+
[3]+  Running              make -j4 &

# Reference by command prefix
psh$ jobs %vim
[2]-  Running              vim file.txt &
```

### Using Job Specifications

```bash
# Bring specific job to foreground
psh$ fg %1

# Send signal to job
psh$ kill -TERM %2

# Resume specific background job
psh$ bg %vim

# Multiple jobspecs (where supported)
psh$ kill -STOP %1 %2 %3

# Error handling
psh$ fg %99
psh: fg: job 99 not found
```

## 15.5 Foreground and Background Control

PSH provides commands to move jobs between foreground and background execution.

### The fg Command

```bash
# Bring job to foreground
psh$ sleep 300 &
[1] 12367
psh$ fg
sleep 300
# Now in foreground, Ctrl-C will terminate it

# Bring specific job to foreground
psh$ job1 &
[1] 12368
psh$ job2 &
[2] 12369
psh$ fg %1
job1

# Resume stopped job in foreground
psh$ vim file.txt
^Z
[1]+ Stopped     vim file.txt
psh$ fg
vim file.txt
# Vim resumes where it was stopped

# fg with no arguments uses current job
psh$ jobs
[1]+  Stopped              vim file.txt
[2]-  Running              make &
psh$ fg
vim file.txt
```

### The bg Command

```bash
# Resume stopped job in background
psh$ long_computation
^Z
[1]+ Stopped     long_computation
psh$ bg
[1]+ long_computation &

# Resume specific stopped job
psh$ vim file1.txt
^Z
[1]+ Stopped     vim file1.txt
psh$ vim file2.txt
^Z
[2]+ Stopped     vim file2.txt
psh$ bg %1
[1]- vim file1.txt &
# Note: vim in background will stop again if it needs terminal

# bg only works on stopped jobs
psh$ sleep 100 &
[1] 12370
psh$ bg %1
psh: bg: job 1 already in background

# Multiple jobs
psh$ bg %1 %2
[1]- job1 &
[2]+ job2 &
```

### Moving Jobs Between States

```bash
# Job state transitions
psh$ long_job
# Press Ctrl-Z
^Z
[1]+ Stopped     long_job
# Job is now stopped

psh$ bg
[1]+ long_job &
# Job now running in background

psh$ fg
long_job
# Job now in foreground

# Complete workflow
psh$ compile_project
# Realize it will take a while
^Z
[1]+ Stopped     compile_project
psh$ bg
[1]+ compile_project &
psh$ # Do other work
psh$ fg
compile_project
# Check on compilation
```

## 15.6 Process Suspension and Signals

Job control relies on signals to manage process states.

### Suspending Processes (Ctrl-Z)

```bash
# Suspend foreground process
psh$ sleep 100
^Z
[1]+ Stopped     sleep 100

# What happens:
1. Shell sends SIGTSTP to foreground process group
2. Processes stop execution
3. Shell regains terminal control
4. Job marked as stopped

# Stopped processes:
- Do not consume CPU
- Retain their state
- Can be resumed later
- Still consume memory
```

### Common Job Control Signals

```bash
# SIGTSTP (Terminal Stop)
- Sent by Ctrl-Z
- Can be caught/ignored by processes
- Default: stop process

# SIGCONT (Continue)
- Sent by fg/bg commands
- Resumes stopped processes
- Cannot be caught/ignored

# SIGINT (Interrupt)
- Sent by Ctrl-C
- Only affects foreground process group
- Default: terminate process

# SIGTTIN (Terminal Input)
- Sent when background job tries to read terminal
- Default: stop process

# SIGTTOU (Terminal Output)
- Sent when background job tries to write terminal
- Default: stop process (if configured)
```

### Signal Behavior Examples

```bash
# SIGINT only affects foreground
psh$ sleep 100 &
[1] 12371
psh$ sleep 200
^C
psh$ jobs
[1]+  Running              sleep 100 &
# Background job unaffected

# SIGTTIN stops background readers
psh$ read var &
[1] 12372
[1]+ Stopped (tty input)  read var

# Sending signals to jobs
psh$ sleep 300 &
[1] 12373
psh$ kill -STOP %1
[1]+ Stopped (signal)     sleep 300
psh$ kill -CONT %1
[1]+ sleep 300 &
```

## 15.7 Terminal Control

Understanding terminal control is key to effective job control usage.

### Terminal Ownership

```bash
# Only one process group owns terminal at a time
# Foreground process group:
- Receives keyboard input
- Receives keyboard signals (Ctrl-C, Ctrl-Z)
- Can read/write terminal freely

# Background process groups:
- Cannot read from terminal
- May be stopped when writing (configurable)
- Do not receive keyboard signals
```

### Terminal Modes

```bash
# Each job can have different terminal settings
psh$ vim file.txt
# Vim sets raw mode for terminal
^Z
[1]+ Stopped     vim file.txt
# Shell restores cooked mode

psh$ fg
# Vim's terminal settings restored

# Terminal settings preserved across suspend/resume
# Important for:
- Editors (vim, emacs)
- Interactive programs (less, man)
- Games and full-screen applications
```

### Background I/O Behavior

```bash
# Background reading always stops process
psh$ cat &
[1] 12374
[1]+ Stopped (tty input)  cat

# Background writing (depends on stty)
psh$ stty tostop    # Stop on output
psh$ echo "test" &
[1] 12375
[1]+ Stopped (tty output) echo "test"

psh$ stty -tostop   # Allow output (default)
psh$ echo "test" &
[1] 12376
test
[1]+ Done        echo "test"

# Best practice: redirect I/O for background jobs
psh$ process < input.txt > output.txt 2>&1 &
[1] 12377
```

## 15.8 Practical Job Control Patterns

### Long-Running Commands

```bash
# Start long command
psh$ make -j8
# Realize it will take time
^Z
[1]+ Stopped     make -j8
psh$ bg
[1]+ make -j8 &

# Check progress periodically
psh$ fg
make -j8
# See output
^Z
[1]+ Stopped     make -j8
psh$ bg
[1]+ make -j8 &

# Continue when done
psh$ # Press Enter to check for completion
[1]+ Done        make -j8
```

### Multiple Tasks

```bash
# Run multiple compilations
psh$ make project1 &
[1] 12378
psh$ make project2 &
[2] 12379
psh$ make project3 &
[3] 12380

# Monitor progress
psh$ jobs
[1]   Running              make project1 &
[2]-  Running              make project2 &
[3]+  Running              make project3 &

# Bring specific one to foreground
psh$ fg %2
make project2
```

### Editor Workflow

```bash
# Edit multiple files
psh$ vim file1.txt
# Make changes
^Z
[1]+ Stopped     vim file1.txt

psh$ vim file2.txt
# Make changes
^Z
[2]+ Stopped     vim file2.txt

# List suspended editors
psh$ jobs
[1]-  Stopped              vim file1.txt
[2]+  Stopped              vim file2.txt

# Return to specific file
psh$ fg %1
vim file1.txt
```

### Download Management

```bash
# Start downloads in background
psh$ wget https://example.com/file1.iso &
[1] 12381
psh$ wget https://example.com/file2.iso &
[2] 12382
psh$ curl -O https://example.com/file3.zip &
[3] 12383

# Check status
psh$ jobs
[1]   Running              wget https://example.com/file1.iso &
[2]-  Running              wget https://example.com/file2.iso &
[3]+  Running              curl -O https://example.com/file3.zip &

# Bring one to foreground to see progress
psh$ fg %1
wget https://example.com/file1.iso
# Watch progress bar
^Z
psh$ bg
```

### Server Process Management

```bash
# Start development servers
psh$ python3 -m http.server 8000 &
[1] 12384
Serving HTTP on 0.0.0.0 port 8000 ...

psh$ npm run dev &
[2] 12385

psh$ docker-compose up &
[3] 12386

# Stop all servers
psh$ jobs
[1]   Running              python3 -m http.server 8000 &
[2]-  Running              npm run dev &
[3]+  Running              docker-compose up &

psh$ kill %1 %2 %3
[1]   Terminated           python3 -m http.server 8000
[2]-  Terminated           npm run dev
[3]+  Terminated           docker-compose up
```

## 15.9 Job Control Best Practices

### Input/Output Management

```bash
# Always redirect I/O for background jobs
# Bad:
psh$ interactive_script &
[1] 12387
[1]+ Stopped (tty input)  interactive_script

# Good:
psh$ interactive_script < input.txt > output.txt 2>&1 &
[1] 12388

# Use nohup for persistent jobs (when available)
psh$ nohup long_running_process &
[1] 12389
```

### Process Organization

```bash
# Group related commands
psh$ (cd project1 && make clean && make) &
[1] 12390
psh$ (cd project2 && make clean && make) &
[2] 12391

# Use meaningful command names
psh$ sleep 3600 &  # Hard to identify
[1] 12392
psh$ sleep 3600 & # backup_timeout
[2] 12393

# Name jobs with functions
backup_data() {
    echo "Starting backup..."
    # Backup commands
}
psh$ backup_data &
[1] 12394
```

### Cleanup and Exit

```bash
# Check for stopped jobs before exit
psh$ exit
You have stopped jobs.

# List stopped jobs
psh$ jobs
[1]+  Stopped              vim file.txt
[2]-  Stopped              less logfile

# Options:
# 1. Resume and finish
psh$ fg %1
# Save and exit vim

# 2. Terminate jobs
psh$ kill %1 %2

# 3. Force exit (jobs will be terminated)
psh$ exit
```

### Debugging with Job Control

```bash
# Suspend misbehaving process
psh$ buggy_program
# Program hangs
^Z
[1]+ Stopped     buggy_program

# Examine state
psh$ ps -p %1
psh$ lsof -p %1

# Try to terminate gracefully
psh$ kill -TERM %1
psh$ jobs
[1]+ Terminated   buggy_program

# Force kill if needed
psh$ kill -KILL %1
```

## 15.10 Limitations and Considerations

### PSH Job Control Limitations

```bash
# Job control is available in interactive mode only
# fg/bg do not work in scripts

# Limited to current shell session
# Jobs don't transfer between terminals

# wait -n (wait for any single job) is not supported
# Use wait with specific PIDs or wait for all jobs

# disown, wait, jobs, fg, bg all work in interactive mode:
psh$ sleep 100 &
[1] 12345
psh$ disown %1    # Remove job from job table
psh$ wait %1      # Wait for specific job
```

### Script Mode Differences

```bash
#!/usr/bin/env psh
# Job control disabled in scripts

# This won't work in a script:
sleep 100 &
fg %1  # Error: no job control

# Scripts should use different patterns:
sleep 100 &
pid=$!
wait $pid
```

### Terminal Considerations

```bash
# SSH sessions
# Job control works normally
ssh remote "psh -i"

# Terminal multiplexers
# Work well with job control
# tmux/screen preserve jobs

# Non-terminal execution
# No job control available
psh < script.sh
echo "command" | psh
```

## Summary

Job control in PSH provides powerful process management capabilities:

1. **Job Basics**: Jobs are pipelines that can run in foreground or background
2. **Background Execution**: Use `&` to run commands without blocking the shell
3. **Job Listing**: `jobs` command shows all active jobs
4. **Job Specifications**: Reference jobs with %n, %+, %-, %string
5. **State Control**: `fg` and `bg` commands move jobs between states
6. **Process Suspension**: Ctrl-Z suspends foreground processes
7. **Signal Management**: Job control signals manage process states
8. **Terminal Control**: Foreground process group owns terminal
9. **Practical Patterns**: Workflows for common job control scenarios
10. **Best Practices**: I/O redirection, organization, and cleanup

Key concepts:
- Jobs allow multitasking in a single terminal
- Process groups organize related processes
- Terminal control determines I/O access
- Signals manage job state transitions
- Background jobs free the terminal for other work
- Stopped jobs can be resumed later
- Job specifications provide flexible job references

Job control transforms the shell from a simple command executor into a powerful process management environment, essential for efficient interactive terminal usage.

---

[Previous: Chapter 14 - Interactive Features](14_interactive_features.md) | [Next: Chapter 16 - Advanced Features](16_advanced_features.md)