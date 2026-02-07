# Signal / Process Group / FD Review Findings

**Scope:** Signal handling, process group handling, and file descriptor redirection.
**Tests:** Not run.

## Findings (ordered by severity)

1. ~~**High — `>&-`, `<&-`, and `<&` are not implemented at runtime**~~ **RESOLVED in v0.125.0**
   - **Issue:** The parser emits close/dup redirect types (`>&-`, `<&-`, `<&`), but runtime redirection code only handles `>&` duplication. Close (`-`) and input dup are ignored.
   - **Fix:** Implemented `<&`, `>&-`, `<&-` runtime handling in all three redirection paths (`apply_redirections`, `setup_child_redirections`, `setup_builtin_redirections`). Also handles alternate close form (`>&` with `target='-'`).

2. ~~**High — Redirect process substitution leaks a live FD into exec'd child**~~ **RESOLVED in v0.125.0**
   - **Issue:** `IOManager.setup_child_redirections()` calls `handle_redirect_process_sub()` but ignores the returned `fd_to_close`. Because the parent FD is created with `FD_CLOEXEC` cleared, it survives `exec`, keeping the pipe open and delaying EOF.
   - **Fix:** `setup_child_redirections()` now closes `fd_to_close` after the redirect is applied.

3. ~~**Medium — `apply_permanent_redirections()` process-substitution check is wrong**~~ **RESOLVED in v0.125.0**
   - **Issue:** The check `target.endswith('')` always returns true. This treats any target starting with `<(` or `>(` as a process substitution even if it lacks a closing `)`.
   - **Fix:** Changed `target.endswith('')` to `target.endswith(')')`.

4. ~~**Medium — Process substitution for builtin redirections skips signal reset / pgid setup**~~ **RESOLVED in v0.124.0**
   - **Issue:** `IOManager.setup_builtin_redirections()` forks for process substitution and does **not** reset child signal handlers or set process groups (unlike `ProcessLauncher`).
   - **Fix:** `manager.py` now calls `apply_child_signal_policy()` from `psh/executor/child_policy.py` immediately after fork.

5. ~~**Low/Medium — Process substitution children only ignore SIGTTOU**~~ **RESOLVED in v0.124.0**
   - **Issue:** `process_sub.py` only sets `SIGTTOU=SIG_IGN`, leaving other signals as inherited.
   - **Fix:** `process_sub.py` now calls the unified `apply_child_signal_policy()` which performs full signal reset via `reset_child_signals()` plus appropriate SIGTTOU disposition.

## General Observations
- The centralized `ProcessLauncher` and `JobManager.transfer_terminal_control()` provide a solid, consistent base for job control and terminal handoff.
- Signal setup for process substitution children was unified in v0.124.0 (findings #4 and #5).
- All 5 findings now resolved: #4 and #5 in v0.124.0, #1, #2, and #3 in v0.125.0.
