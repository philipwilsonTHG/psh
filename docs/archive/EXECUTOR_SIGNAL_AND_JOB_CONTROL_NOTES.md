# Executor Signal & Job-Control Review

This note captures current observations and improvement ideas for
pipeline/process execution in PSH.  It complements the details already
documented in `ARCHITECTURE.md` by focusing on signal disposition and
process-group management in the executor package.

## Current Behavior (Code References)

- `psh/executor/pipeline.py:160-205` – pipeline children set their own
  process groups, temporarily ignore `SIGTTOU`, and reset the rest of the
  interactive signals before running visitor logic.
- `psh/executor/strategies.py:150-449` – background builtins and external
  commands reset the same signals and cooperate with `JobManager` when
  transferring terminal control.
- `psh/executor/subshell.py:115-199` – subshells fork new shell instances
  after `setpgid(0,0)` and rely on the parent to hand terminal ownership
  back once the job completes.
- `psh/job_control.py:95-320` – `JobManager` keeps track of current and
  previous jobs, handles `waitpid(-pgid, WUNTRACED)`, and restores tty
  modes when the foreground job changes.

## Recommended Improvements

1. **Centralize Child Signal Reset Logic**  
   Multiple fork paths duplicate the same `signal.signal(..., SIG_DFL)`
   boilerplate. A shared helper (e.g., `shell.signal_manager.reset_child_signals()`)
   would lower the risk of future divergence and make it easy to adjust
   the handled set (`SIGQUIT`, traps, etc.) in one place.

2. **Improve Process-Group Synchronization**  
   Non-leader pipeline children spin for up to 50 ms waiting for the
   parent to assign them to the shared PG (`psh/executor/pipeline.py:169-190`).
   Replacing the busy-loop with a handshake (pipe/sem) or pre-fork
   `setpgid` strategy would make the behavior deterministic and avoid
   wasting slices on slow systems.

3. **Surface `tcsetpgrp` Failures When Debugging**  
   TTY ownership transfers already sit in `try/except`, but failures yield
   silent fallbacks even with `debug-exec` enabled. Logging a warning (or
   memoizing a “no controlling tty” flag) would help developers
   understand why Ctrl‑C is ignored in certain environments.

4. **Unify Foreground Cleanup**  
   Some code paths clear `state.foreground_pgid` and call
   `job_manager.set_foreground_job(None)` while others rely on implicit
   side effects. Providing a helper like `job_manager.restore_shell_foreground()`
   would ensure terminal modes and bookkeeping are reset no matter which
   executor module spawned the job.

5. **Consider a Dedicated SIGCHLD Strategy**  
   `JobManager.wait_for_job` polls synchronously; asynchronous background
   notifications depend on whoever else reaps children. Installing (or
   documenting) a `SIGCHLD` handler that records statuses for background
   jobs would allow the shell to update job states even while waiting for
   user input.

These changes are incremental and do not alter external behavior, but
they would reduce maintenance overhead and make PSH’s job-control story
clearer for future contributors.
