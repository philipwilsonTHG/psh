# Executor Improvement Recommendations

This document outlines three recommendations for improving the reliability and maintainability of the `psh` executor, specifically concerning process group management and signal handling.

### 1. Unify Process Creation and Job Control Logic

**Observation:**
There is significant code duplication for process and job management. The logic for forking a process, creating a process group (`os.setpgid`), managing terminal control (`os.tcsetpgrp`), and creating a `Job` object is repeated with slight variations in:
*   `psh/executor/pipeline.py` (for commands in a pipeline)
*   `psh/executor/strategies.py` (in `ExternalExecutionStrategy` for single foreground/background commands)
*   `psh/executor/strategies.py` (in `BuiltinExecutionStrategy` for running builtins in the background)

**Recommendation:**
Refactor this duplicated logic into a single, unified "process launcher" or "job launcher" component, likely within the `JobManager` or a new, dedicated module. This component would be the sole authority for forking new processes and setting up their execution context (process group, signals, terminal control).

**Benefits:**
*   **Maintainability:** Bug fixes or enhancements to process management (like improving race condition handling) would only need to be made in one place.
*   **Consistency:** Guarantees that all commands, whether in a pipeline or standalone, are subject to the exact same job control and signal handling rules.
*   **Simplicity:** The `PipelineExecutor` and `ExternalExecutionStrategy` would become simpler, delegating the low-level process management details to the new component.

### 2. Improve `SIGCHLD` Handler Signal Safety

**Observation:**
The `_handle_sigchld` method in `psh/interactive/signal_manager.py` performs several actions directly within the signal handler context, including looping, calling `os.waitpid`, and updating job objects. While this often works, running complex Python code inside a signal handler is not guaranteed to be safe and can lead to reentrancy bugs or deadlocks.

**Recommendation:**
Implement the "self-pipe trick" for safer signal handling.
1.  On startup, create a pipe using `os.pipe()`.
2.  The `_handle_sigchld` signal handler's only job would be to write a single byte to the write-end of this pipe (a non-blocking, async-signal-safe operation).
3.  The shell's main interactive loop would use `select()` or a similar mechanism to monitor the read-end of the pipe for new data.
4.  When data is detected, the main loop would then call the full job-reaping logic (the code currently in `_handle_sigchld`) safely outside of the signal handler context.

**Benefits:**
*   **Reliability:** This is the canonical pattern for safe signal handling in complex applications. It moves all non-trivial work out of the signal handler, avoiding potential interpreter state corruption or deadlocks.
*   **Robustness:** Makes the shell more resilient to subtle bugs that are notoriously difficult to debug.

### 3. Eliminate Race Condition in Process Group Setup

**Observation:**
In `psh/executor/pipeline.py`, a child process in a pipeline uses a `time.sleep()` loop to wait for its parent to add it to the correct process group. This is a classic race condition fix that is not guaranteed to be reliable, especially on heavily loaded systems.

**Recommendation:**
Replace the `time.sleep()` loop with a more deterministic synchronization mechanism, such as a pipe.
1.  Before forking the children of a pipeline, the parent creates a single pipe.
2.  After each `fork()`, the parent closes the read-end of the pipe and the child closes the write-end.
3.  In the child process, after forking but before calling `execvpe`, it blocks on a `os.read()` from the pipe.
4.  In the parent process, after it has successfully placed all children into the new process group using `os.setpgid()`, it closes the write-end of the pipe.
5.  Closing the write-end sends an EOF to the read-end, which unblocks all the waiting child processes simultaneously, now certain they are in the correct process group.

**Benefits:**
*   **Atomicity & Reliability:** This approach is atomic and removes the guesswork of `time.sleep()`. It guarantees that no child process proceeds until the parent has fully configured the process group, eliminating the race condition entirely.
*   **Efficiency:** Avoids the unnecessary polling and context switching of the `sleep` loop.
