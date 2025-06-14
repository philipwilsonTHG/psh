# Visitor Executor Terminal Control Fix

## Problem
When using the visitor executor, terminal-based programs like `emacs` were being immediately stopped and placed in the background instead of running in the foreground. This happened because the visitor executor was not giving terminal control to foreground processes.

## Root Cause
The visitor executor was missing the critical `tcsetpgrp()` calls that transfer terminal control to the foreground process group. Without terminal control, when programs like emacs try to read from or write to the terminal, they receive SIGTTIN or SIGTTOU signals, causing them to be stopped.

## Solution
Added terminal control management to the visitor executor in two places:

### 1. Single Command Execution (`_execute_external`)
```python
# Save current terminal foreground process group
try:
    original_pgid = os.tcgetpgrp(0)
except:
    original_pgid = None

# ... fork and execute ...

if not background:
    # Give terminal control to the foreground process
    if original_pgid is not None:
        self.state.foreground_pgid = pid
        try:
            os.tcsetpgrp(0, pid)
        except:
            pass
    
    # Wait for job...
    
    # Restore terminal control to shell
    if original_pgid is not None:
        try:
            os.tcsetpgrp(0, original_pgid)
        except:
            pass
```

### 2. Pipeline Execution (`_execute_pipeline`)
Similar terminal control transfer for pipeline process groups.

## Additional Fixes
- Fixed incorrect attribute access: `job.pid` → `job.pgid`
- Removed duplicate background job notification printing

## Testing
Created comprehensive tests to verify:
1. Basic foreground process execution
2. Background job handling
3. Terminal control with PTY
4. Job control operations (suspend/resume)

## Result
Terminal-based programs like `emacs`, `vi`, `nano` now work correctly with the visitor executor, matching the behavior of the legacy executor.