#!/usr/bin/env python3
"""Demo script to showcase job control features in psh."""

print("""
PSH Job Control Demo
===================

This demo shows the job control features implemented in psh:

1. Background Jobs (&)
   - Run commands in the background with &
   - Get job ID and process group ID notification

2. Job Listing (jobs)
   - List all active jobs
   - Shows job ID, state (Running/Stopped), and command

3. Job Suspension (Ctrl-Z)
   - Press Ctrl-Z to suspend a foreground job
   - Job moves to stopped state

4. Foreground Resume (fg)
   - Bring a stopped or background job to foreground
   - Use job specs: %1, %2, %+, %-, %string

5. Background Resume (bg)
   - Resume a stopped job in the background
   - Job continues execution without terminal control

6. Job Specifications
   - %n  : Job number n
   - %+  : Current job (most recent)
   - %-  : Previous job
   - %%  : Current job (same as %+)
   - %str: Job whose command starts with 'str'

Example Session:
```
psh$ sleep 30 &              # Start background job
[1] 12345                    # Job 1, PGID 12345

psh$ sleep 20 | grep x      # Start pipeline
^Z                          # Press Ctrl-Z to suspend
[2]+  Stopped     sleep 20 | grep x

psh$ jobs                    # List all jobs
[1]-  Running     sleep 30 &
[2]+  Stopped     sleep 20 | grep x

psh$ bg %2                   # Resume job 2 in background
[2]+ sleep 20 | grep x &

psh$ fg %1                   # Bring job 1 to foreground
# (waits for sleep to complete)

psh$ sleep 10
^Z
[3]+  Stopped     sleep 10

psh$ fg                      # fg with no args uses %+
# (resumes sleep 10)
```

Try it yourself:
""")

print("python3 -m psh")
print("\nThen try the commands shown above!")