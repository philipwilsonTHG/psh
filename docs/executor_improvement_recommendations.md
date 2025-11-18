# Executor, Signal Handling, and Process Group Management Improvements

**Document Version:** 1.0
**Date:** 2025-01-18
**Status:** Proposed Recommendations

## Executive Summary

This document outlines specific, actionable recommendations for improving PSH's executor architecture, signal handling, and process group management. The current implementation is already production-quality with correct POSIX semantics, but these improvements will enhance:

- **Reliability** under heavy system load
- **Debuggability** for process control issues
- **Observability** of signal and job control state
- **Maintainability** through centralized tracking

All recommendations are organized by priority with specific implementation guidance.

---

## High Priority Recommendations

### 1. Increase Process Group Synchronization Timeout

**File:** `psh/executor/pipeline.py:173`

**Issue:** Current 50ms timeout may be insufficient under heavy system load or slow schedulers.

**Current Code:**
```python
for attempt in range(50):  # Try for up to 50ms
    try:
        current_pgid = os.getpgrp()
        if current_pgid != os.getpid():
            break
    except OSError:
        pass
    time.sleep(0.001)  # Wait 1ms
```

**Recommended Implementation:**

```python
# At module level
MAX_PGID_SYNC_ATTEMPTS = 200  # 200ms default (configurable)
PGID_SYNC_INTERVAL = 0.001    # 1ms between attempts

# In child process:
for attempt in range(MAX_PGID_SYNC_ATTEMPTS):
    try:
        current_pgid = os.getpgrp()
        if current_pgid != os.getpid():
            if self.state.options.get('debug-exec'):
                print(f"DEBUG: Child {os.getpid()} joined pgid after {attempt}ms",
                      file=sys.stderr)
            break
    except OSError:
        pass
    time.sleep(PGID_SYNC_INTERVAL)
else:
    # Timeout occurred - log warning
    if self.state.options.get('debug-exec'):
        print(f"WARNING: Child {os.getpid()} failed to join pgid within "
              f"{MAX_PGID_SYNC_ATTEMPTS}ms", file=sys.stderr)
```

**Alternative - Signal-Based Synchronization:**

More robust but more complex:

```python
# Parent creates sync pipe before fork
sync_pipe_r, sync_pipe_w = os.pipe()

pid = os.fork()
if pid == 0:  # Child
    os.close(sync_pipe_w)
    # Wait for parent to signal completion
    try:
        os.read(sync_pipe_r, 1)
    except OSError:
        pass
    os.close(sync_pipe_r)
    # Parent has set our process group
else:  # Parent
    os.close(sync_pipe_r)
    # Set child's process group
    os.setpgid(pid, pgid)
    # Signal child it's safe to proceed
    try:
        os.write(sync_pipe_w, b'1')
    except OSError:
        pass
    os.close(sync_pipe_w)
```

**Benefits:**
- Handles slow schedulers and heavily loaded systems
- Provides visibility into timing issues via debug output
- Configurable for different deployment scenarios

**Testing:**
```bash
# Test under load:
$ stress-ng --cpu 8 --timeout 60s &
$ psh -c "seq 1 100 | xargs -P 10 -I {} echo pipeline {}"
```

---

### 2. Implement Signal Blocking During Critical Sections

**Files:** `psh/job_control.py:266-347`, `psh/expansion/command_sub.py`

**Issue:** SIGCHLD handler can race with `wait_for_job()`, requiring complex fallback logic.

**Create Signal Blocking Utility:**

**New File:** `psh/utils/signal_utils.py`

```python
"""Signal handling utilities."""
import signal
import contextlib
from typing import Set, Iterable

@contextlib.contextmanager
def block_signals(*signals_to_block: int):
    """Context manager to temporarily block signals.

    This is signal-async-safe and prevents race conditions between
    signal handlers and explicit wait() calls.

    Args:
        *signals_to_block: Signal numbers to block (e.g., signal.SIGCHLD)

    Example:
        with block_signals(signal.SIGCHLD):
            # SIGCHLD is blocked here
            pid, status = os.waitpid(...)
            job.update_process_status(pid, status)
        # SIGCHLD is unblocked and pending signals delivered

    Note:
        Requires Python 3.3+ for signal.pthread_sigmask()
    """
    if not signals_to_block:
        yield
        return

    try:
        # Block signals
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set(signals_to_block))
        try:
            yield
        finally:
            # Restore original mask
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
    except AttributeError:
        # pthread_sigmask not available on this platform
        # Fall back to no blocking (Windows, old Python)
        yield


@contextlib.contextmanager
def restore_default_signals(*signals_to_restore: int):
    """Context manager to temporarily restore default signal handlers.

    Useful in child processes that need default signal behavior.

    Args:
        *signals_to_restore: Signal numbers to reset

    Example:
        with restore_default_signals(signal.SIGINT, signal.SIGTSTP):
            # Signals have default handlers here
            os.execv(path, args)
    """
    if not signals_to_restore:
        yield
        return

    # Save current handlers
    saved_handlers = {}
    for sig in signals_to_restore:
        try:
            saved_handlers[sig] = signal.signal(sig, signal.SIG_DFL)
        except (OSError, ValueError):
            # Signal not valid on this platform
            pass

    try:
        yield
    finally:
        # Restore saved handlers
        for sig, handler in saved_handlers.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass
```

**Update wait_for_job:**

```python
from psh.utils.signal_utils import block_signals

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
            # Block SIGCHLD during wait to prevent race with signal handler
            with block_signals(signal.SIGCHLD):
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

                # Find which process this is and record exit status
                for i, proc in enumerate(job.processes):
                    if proc.pid == pid:
                        if collect_all_statuses:
                            while len(all_exit_statuses) <= i:
                                all_exit_statuses.append(0)
                            all_exit_statuses[i] = proc_exit_status

                        if i == len(job.processes) - 1:
                            exit_status = proc_exit_status
            # SIGCHLD unblocked here - pending signals delivered

        except OSError:
            break

    # Simplified fallback - no race condition possible
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

                if i == len(job.processes) - 1:
                    exit_status = proc_exit_status

    # Update job state
    old_state = job.state
    job.update_state()

    # Notify if needed
    if (self.shell_state and self.shell_state.options.get('notify', False) and
        old_state != JobState.DONE and job.state == JobState.DONE and
        not job.foreground and not job.notified):
        print(f"\n[{job.job_id}]+  Done                    {job.command}")
        job.notified = True

    if collect_all_statuses:
        return all_exit_statuses
    return exit_status
```

**Benefits:**
- Eliminates SIGCHLD/wait race condition
- Simpler logic (less fallback code needed)
- More predictable behavior
- Standard Unix practice

**Trade-offs:**
- Slightly delayed SIGCHLD notifications for background jobs (during wait)
- Requires Python 3.3+ for pthread_sigmask (graceful fallback provided)

---

### 3. Add TTY Detection and Graceful Degradation

**Files:** `psh/core/state.py`, `psh/executor/pipeline.py`, various

**Issue:** Many `try/except` blocks suppress terminal control errors, hiding configuration issues.

**Add Terminal Capability Detection:**

**Update:** `psh/core/state.py`

```python
@dataclass
class ShellState:
    # ... existing fields ...

    # Terminal information
    is_terminal: bool = False
    terminal_fd: Optional[int] = None
    supports_job_control: bool = False

    def __post_init__(self):
        # ... existing initialization ...
        self._detect_terminal_capabilities()

    def _detect_terminal_capabilities(self):
        """Detect if we have a controlling terminal with job control support.

        This determines whether we can use tcsetpgrp(), tcgetpgrp(), etc.
        Results are cached in state for efficient checks.
        """
        try:
            # Check if stdin is a TTY
            if os.isatty(0):
                self.is_terminal = True
                self.terminal_fd = 0

                # Check if we can actually do job control
                # Some TTY environments don't support it (e.g., emacs shell-mode)
                try:
                    current_pgid = os.tcgetpgrp(0)
                    self.supports_job_control = True

                    if self.options.get('debug-exec'):
                        print(f"DEBUG: Terminal detected, job control available (pgid={current_pgid})",
                              file=sys.stderr)
                except OSError as e:
                    # TTY but no job control available
                    self.supports_job_control = False
                    if self.options.get('debug-exec'):
                        print(f"DEBUG: Terminal detected but job control unavailable: {e}",
                              file=sys.stderr)
            else:
                self.is_terminal = False
                self.supports_job_control = False
                if self.options.get('debug-exec'):
                    print(f"DEBUG: Not running on a terminal (stdin is not a TTY)",
                          file=sys.stderr)
        except (OSError, AttributeError):
            # Platform doesn't support TTY detection
            self.is_terminal = False
            self.supports_job_control = False
```

**Update Terminal Control Calls:**

**In:** `psh/executor/pipeline.py`

Replace this pattern:
```python
try:
    os.tcsetpgrp(0, pgid)
except Exception as e:
    pass  # Ignore errors
```

With this:
```python
if self.state.supports_job_control:
    try:
        os.tcsetpgrp(self.state.terminal_fd, pgid)
    except OSError as e:
        if self.state.options.get('debug-exec'):
            print(f"DEBUG: Failed to transfer terminal control to pgid {pgid}: {e}",
                  file=sys.stderr)
        # Count failures for metrics
        if hasattr(self.state, 'process_metrics'):
            self.state.process_metrics.terminal_transfer_failures += 1
else:
    # No job control available - skip terminal transfer
    if self.state.options.get('debug-exec'):
        print(f"DEBUG: Skipping terminal control transfer (no job control support)",
              file=sys.stderr)
```

**Add Helper Methods:**

```python
# In psh/executor/pipeline.py or utils

def transfer_terminal_control(self, pgid: int) -> bool:
    """Transfer terminal control to process group.

    Args:
        pgid: Process group ID to give terminal control

    Returns:
        True if successful, False otherwise
    """
    if not self.state.supports_job_control:
        return False

    try:
        os.tcsetpgrp(self.state.terminal_fd, pgid)
        if self.state.options.get('debug-exec'):
            print(f"DEBUG: Transferred terminal control to pgid {pgid}",
                  file=sys.stderr)
        return True
    except OSError as e:
        if self.state.options.get('debug-exec'):
            print(f"DEBUG: Failed to transfer terminal control: {e}",
                  file=sys.stderr)
        if hasattr(self.state, 'process_metrics'):
            self.state.process_metrics.terminal_transfer_failures += 1
        return False

def restore_terminal_control(self) -> bool:
    """Restore terminal control to shell.

    Returns:
        True if successful, False otherwise
    """
    if not self.state.supports_job_control:
        return False

    shell_pgid = os.getpgrp()
    try:
        os.tcsetpgrp(self.state.terminal_fd, shell_pgid)
        self.state.foreground_pgid = None
        if self.state.options.get('debug-exec'):
            print(f"DEBUG: Restored terminal control to shell (pgid {shell_pgid})",
                  file=sys.stderr)
        return True
    except OSError as e:
        if self.state.options.get('debug-exec'):
            print(f"DEBUG: Failed to restore terminal control: {e}",
                  file=sys.stderr)
        return False
```

**Benefits:**
- Clear error messages when job control unavailable
- Tests can detect TTY absence and adjust expectations
- Better user feedback in non-TTY contexts (cron, CI/CD)
- Metrics on terminal control failures

**Testing:**
```bash
# Test without TTY
$ echo "echo hello" | psh

# Test with TTY
$ psh -c "echo hello"

# Test in emacs shell-mode (no job control)
$ emacs -nw -f shell
```

---

### 4. Centralize Signal Disposition Tracking

**Issue:** 40+ `signal.signal()` calls across 6 files with no central tracking.

**Create Signal Registry:**

**New File:** `psh/utils/signal_registry.py`

```python
"""Central registry for signal handler state tracking."""
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
import signal
import sys

@dataclass
class SignalDisposition:
    """Tracks signal handler state for a single signal."""
    signal_num: int
    signal_name: str
    current_handler: Any  # Can be callable, SIG_DFL, SIG_IGN
    original_handler: Any
    set_by: str  # Which component set it (for debugging)
    set_count: int = 0  # How many times this signal has been modified

    def __str__(self):
        handler_name = self._handler_name(self.current_handler)
        return f"{self.signal_name:12} -> {handler_name:30} (set by {self.set_by}, count={self.set_count})"

    @staticmethod
    def _handler_name(handler: Any) -> str:
        """Get human-readable name for handler."""
        if handler == signal.SIG_DFL:
            return "SIG_DFL"
        elif handler == signal.SIG_IGN:
            return "SIG_IGN"
        elif callable(handler):
            return getattr(handler, '__name__', repr(handler))
        else:
            return str(handler)

class SignalRegistry:
    """Central registry for signal handler state.

    This class provides visibility into which signals have been modified,
    who modified them, and their current disposition. Useful for debugging
    signal-related issues.

    Example:
        registry = SignalRegistry()
        registry.set_handler(signal.SIGINT, my_handler, "MyComponent")
        print(registry.report())
    """

    def __init__(self):
        self.dispositions: Dict[int, SignalDisposition] = {}
        self._enabled = True  # Can disable for performance

    def set_handler(self, sig: int, handler: Any, set_by: str = "unknown") -> Any:
        """Set a signal handler and track it.

        Args:
            sig: Signal number (e.g., signal.SIGINT)
            handler: Handler function, SIG_DFL, or SIG_IGN
            set_by: Name of component setting the handler

        Returns:
            Previous handler
        """
        if not self._enabled:
            return signal.signal(sig, handler)

        # Get signal name
        try:
            if hasattr(signal, 'Signals'):
                sig_name = signal.Signals(sig).name
            else:
                # Older Python versions
                sig_name = f"Signal{sig}"
        except ValueError:
            sig_name = f"Signal{sig}"

        # Get current handler before changing
        try:
            current = signal.signal(sig, handler)
        except (OSError, ValueError) as e:
            # Signal not valid on this platform
            return None

        if sig not in self.dispositions:
            # First time setting this signal
            self.dispositions[sig] = SignalDisposition(
                signal_num=sig,
                signal_name=sig_name,
                current_handler=handler,
                original_handler=current,
                set_by=set_by,
                set_count=1
            )
        else:
            # Update existing
            disp = self.dispositions[sig]
            disp.current_handler = handler
            disp.set_by = set_by
            disp.set_count += 1

        return current

    def get_disposition(self, sig: int) -> Optional[SignalDisposition]:
        """Get current signal disposition.

        Args:
            sig: Signal number

        Returns:
            SignalDisposition or None if signal not tracked
        """
        return self.dispositions.get(sig)

    def restore_original(self, sig: int) -> bool:
        """Restore signal to original handler.

        Args:
            sig: Signal number

        Returns:
            True if restored, False if not tracked
        """
        if sig in self.dispositions:
            disp = self.dispositions[sig]
            try:
                signal.signal(sig, disp.original_handler)
                disp.current_handler = disp.original_handler
                return True
            except (OSError, ValueError):
                return False
        return False

    def restore_all(self):
        """Restore all signals to their original handlers."""
        for sig in list(self.dispositions.keys()):
            self.restore_original(sig)

    def report(self, file=None) -> str:
        """Generate a report of all signal dispositions.

        Args:
            file: Optional file to write to (defaults to stderr)

        Returns:
            Report string
        """
        if file is None:
            file = sys.stderr

        lines = ["Signal Disposition Report:"]
        lines.append("-" * 70)

        if not self.dispositions:
            lines.append("  (no signals tracked)")
        else:
            for sig in sorted(self.dispositions.keys()):
                disp = self.dispositions[sig]
                lines.append(f"  {disp}")

        lines.append("-" * 70)
        report = "\n".join(lines)

        if file:
            print(report, file=file)

        return report

    def validate_interactive_mode(self) -> list[str]:
        """Validate signal dispositions for interactive shell mode.

        Returns:
            List of issues found (empty if all OK)
        """
        issues = []

        # In interactive mode, these should be ignored
        should_ignore = [signal.SIGTSTP, signal.SIGTTOU, signal.SIGTTIN]
        for sig in should_ignore:
            if sig in self.dispositions:
                disp = self.dispositions[sig]
                if disp.current_handler != signal.SIG_IGN:
                    issues.append(
                        f"{disp.signal_name} should be SIG_IGN in interactive mode, "
                        f"but is {SignalDisposition._handler_name(disp.current_handler)}"
                    )

        # SIGCHLD should have custom handler in interactive mode
        if signal.SIGCHLD in self.dispositions:
            disp = self.dispositions[signal.SIGCHLD]
            if disp.current_handler == signal.SIG_DFL:
                issues.append(
                    "SIGCHLD should have custom handler in interactive mode"
                )

        return issues
```

**Integration with ShellState:**

**Update:** `psh/core/state.py`

```python
from psh.utils.signal_registry import SignalRegistry

@dataclass
class ShellState:
    # ... existing fields ...

    # Signal tracking
    signal_registry: SignalRegistry = field(default_factory=SignalRegistry)
```

**Update Signal Manager:**

**Update:** `psh/interactive/signal_manager.py`

```python
def _setup_interactive_mode_handlers(self):
    """Set up full signal handling for interactive mode."""
    reg = self.state.signal_registry

    # Store original handlers for restoration
    self._original_handlers[signal.SIGINT] = reg.set_handler(
        signal.SIGINT, self._handle_signal_with_trap_check, "SignalManager"
    )
    self._original_handlers[signal.SIGTERM] = reg.set_handler(
        signal.SIGTERM, self._handle_signal_with_trap_check, "SignalManager"
    )
    self._original_handlers[signal.SIGHUP] = reg.set_handler(
        signal.SIGHUP, self._handle_signal_with_trap_check, "SignalManager"
    )
    self._original_handlers[signal.SIGQUIT] = reg.set_handler(
        signal.SIGQUIT, self._handle_signal_with_trap_check, "SignalManager"
    )
    self._original_handlers[signal.SIGTSTP] = reg.set_handler(
        signal.SIGTSTP, signal.SIG_IGN, "SignalManager"
    )
    self._original_handlers[signal.SIGTTOU] = reg.set_handler(
        signal.SIGTTOU, signal.SIG_IGN, "SignalManager"
    )
    self._original_handlers[signal.SIGTTIN] = reg.set_handler(
        signal.SIGTTIN, signal.SIG_IGN, "SignalManager"
    )
    self._original_handlers[signal.SIGCHLD] = reg.set_handler(
        signal.SIGCHLD, self._handle_sigchld, "SignalManager"
    )
    self._original_handlers[signal.SIGPIPE] = reg.set_handler(
        signal.SIGPIPE, signal.SIG_DFL, "SignalManager"
    )
```

**Add Debug Command:**

Create new builtin to show signal state:

**New File:** `psh/builtins/signals_builtin.py`

```python
"""Builtin for debugging signal state."""
from .base import Builtin, builtin

@builtin
class SignalsBuiltin(Builtin):
    """Show current signal dispositions (debugging)."""

    name = "signals"

    def execute(self, args: list[str], shell) -> int:
        """Execute the signals builtin.

        Usage:
            signals              # Show all signal dispositions
            signals --validate   # Validate signal state
        """
        if len(args) > 1 and args[1] == '--validate':
            issues = shell.state.signal_registry.validate_interactive_mode()
            if issues:
                self.error("Signal validation failed:", shell)
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            else:
                print("Signal validation passed: all signals properly configured")
                return 0
        else:
            shell.state.signal_registry.report()
            return 0
```

**Benefits:**
- Visibility into current signal configuration
- Debugging tool for signal-related issues
- Documentation of signal handling architecture
- Detect conflicting signal handlers
- Validation of signal state

**Usage:**
```bash
$ psh -c "builtin signals"
Signal Disposition Report:
----------------------------------------------------------------------
  SIGINT       -> _handle_signal_with_trap_check  (set by SignalManager, count=1)
  SIGTERM      -> _handle_signal_with_trap_check  (set by SignalManager, count=1)
  SIGTSTP      -> SIG_IGN                          (set by SignalManager, count=1)
  SIGCHLD      -> _handle_sigchld                  (set by SignalManager, count=1)
----------------------------------------------------------------------

$ psh -c "builtin signals --validate"
Signal validation passed: all signals properly configured
```

---

## Medium Priority Recommendations

### 5. Add Metrics Collection for Process Control

**Create Process Metrics System:**

**New File:** `psh/utils/process_metrics.py`

```python
"""Process control metrics collection."""
from dataclasses import dataclass, field
from typing import List
import sys

@dataclass
class ProcessMetrics:
    """Collect metrics about process management.

    This class tracks various process control operations to help
    diagnose performance issues and validate correct behavior.

    Metrics collected:
    - Number of fork() calls
    - Number of wait() calls
    - Number of SIGCHLD signals received
    - Process group synchronization times
    - Terminal control transfer failures
    """

    fork_count: int = 0
    wait_count: int = 0
    sigchld_count: int = 0
    pgid_sync_times: List[float] = field(default_factory=list)
    terminal_transfer_failures: int = 0
    terminal_transfer_successes: int = 0

    def record_fork(self):
        """Record a fork() call."""
        self.fork_count += 1

    def record_wait(self):
        """Record a wait() call."""
        self.wait_count += 1

    def record_sigchld(self):
        """Record a SIGCHLD signal."""
        self.sigchld_count += 1

    def record_pgid_sync_time(self, attempts: int, interval: float):
        """Record how long it took to sync process group.

        Args:
            attempts: Number of polling attempts
            interval: Time between attempts (seconds)
        """
        self.pgid_sync_times.append(attempts * interval)

    def record_terminal_transfer_success(self):
        """Record successful terminal control transfer."""
        self.terminal_transfer_successes += 1

    def record_terminal_transfer_failure(self):
        """Record failed terminal control transfer."""
        self.terminal_transfer_failures += 1

    def reset(self):
        """Reset all metrics to zero."""
        self.fork_count = 0
        self.wait_count = 0
        self.sigchld_count = 0
        self.pgid_sync_times.clear()
        self.terminal_transfer_failures = 0
        self.terminal_transfer_successes = 0

    def report(self, file=None) -> str:
        """Generate metrics report.

        Args:
            file: Optional file to write to (defaults to stdout)

        Returns:
            Report string
        """
        if file is None:
            file = sys.stdout

        # Calculate statistics
        avg_pgid = (sum(self.pgid_sync_times) / len(self.pgid_sync_times)
                    if self.pgid_sync_times else 0)
        max_pgid = max(self.pgid_sync_times) if self.pgid_sync_times else 0
        min_pgid = min(self.pgid_sync_times) if self.pgid_sync_times else 0

        total_terminal = (self.terminal_transfer_successes +
                         self.terminal_transfer_failures)
        terminal_success_rate = (100 * self.terminal_transfer_successes / total_terminal
                                if total_terminal > 0 else 0)

        report = f"""Process Control Metrics:
----------------------------------------------------------------------
Fork Operations:
  Total forks:            {self.fork_count}
  Total waits:            {self.wait_count}
  SIGCHLD signals:        {self.sigchld_count}

Process Group Synchronization:
  Sync operations:        {len(self.pgid_sync_times)}
  Average sync time:      {avg_pgid*1000:.2f}ms
  Min sync time:          {min_pgid*1000:.2f}ms
  Max sync time:          {max_pgid*1000:.2f}ms

Terminal Control:
  Successful transfers:   {self.terminal_transfer_successes}
  Failed transfers:       {self.terminal_transfer_failures}
  Success rate:           {terminal_success_rate:.1f}%
----------------------------------------------------------------------"""

        if file:
            print(report, file=file)

        return report

    def summary(self) -> str:
        """Get one-line summary of metrics."""
        return (f"forks={self.fork_count} waits={self.wait_count} "
                f"sigchld={self.sigchld_count} "
                f"terminal_fails={self.terminal_transfer_failures}")
```

**Integration:**

**Update:** `psh/core/state.py`

```python
from psh.utils.process_metrics import ProcessMetrics

@dataclass
class ShellState:
    # ... existing fields ...

    # Process control metrics
    process_metrics: ProcessMetrics = field(default_factory=ProcessMetrics)
```

**Add Instrumentation:**

**In:** `psh/executor/pipeline.py`

```python
# When forking:
pid = os.fork()
self.state.process_metrics.record_fork()

# In child process, after pgid sync:
for attempt in range(MAX_PGID_SYNC_ATTEMPTS):
    if current_pgid != os.getpid():
        self.state.process_metrics.record_pgid_sync_time(
            attempt, PGID_SYNC_INTERVAL
        )
        break

# When transferring terminal control:
if self.transfer_terminal_control(pgid):
    self.state.process_metrics.record_terminal_transfer_success()
else:
    self.state.process_metrics.record_terminal_transfer_failure()
```

**In:** `psh/job_control.py`

```python
def wait_for_job(self, job: Job, collect_all_statuses: bool = False) -> int:
    self.shell_state.process_metrics.record_wait()
    # ... rest of wait logic ...
```

**In:** `psh/interactive/signal_manager.py`

```python
def _handle_sigchld(self, signum, frame):
    self.state.process_metrics.record_sigchld()
    # ... rest of handler ...
```

**Add Builtin Command:**

**New File:** `psh/builtins/metrics_builtin.py`

```python
"""Builtin for showing process control metrics."""
from .base import Builtin, builtin

@builtin
class MetricsBuiltin(Builtin):
    """Show process control metrics."""

    name = "metrics"

    def execute(self, args: list[str], shell) -> int:
        """Execute the metrics builtin.

        Usage:
            metrics          # Show all metrics
            metrics --reset  # Reset metrics
        """
        if len(args) > 1 and args[1] == '--reset':
            shell.state.process_metrics.reset()
            print("Metrics reset")
            return 0
        else:
            shell.state.process_metrics.report()
            return 0
```

**Benefits:**
- Identify performance bottlenecks
- Validate correct behavior (forks == waits?)
- Detect terminal control issues
- Track SIGCHLD delivery
- Performance regression testing

**Usage:**
```bash
$ psh -c "seq 1 100 | grep 50; builtin metrics"
Process Control Metrics:
----------------------------------------------------------------------
Fork Operations:
  Total forks:            2
  Total waits:            2
  SIGCHLD signals:        2

Process Group Synchronization:
  Sync operations:        1
  Average sync time:      2.00ms
  Min sync time:          2.00ms
  Max sync time:          2.00ms
----------------------------------------------------------------------
```

---

### 6. Improve SIGCHLD Handler Robustness

**File:** `psh/interactive/signal_manager.py:97-126`

**Issue:** Signal handlers can be re-entered on some platforms.

**Make SIGCHLD Handler Re-entrant Safe:**

```python
def __init__(self, shell):
    super().__init__(shell)
    self._original_handlers: Dict[int, Callable] = {}
    self._interactive_mode = not shell.state.is_script_mode
    self._in_sigchld_handler = False  # Re-entrance guard

def _handle_sigchld(self, signum, frame):
    """Handle child process state changes (re-entrant safe version).

    Signal handlers can be interrupted and re-entered. This implementation
    protects against re-entrance to avoid corrupting job state.
    """
    # Guard against re-entrance
    if self._in_sigchld_handler:
        # Already handling SIGCHLD, will be called again after
        return

    self._in_sigchld_handler = True
    try:
        while True:
            try:
                wait_flags = os.WNOHANG | os.WUNTRACED
                pid, status = os.waitpid(-1, wait_flags)
                if pid == 0:
                    break

                # Record metrics
                if hasattr(self.state, 'process_metrics'):
                    self.state.process_metrics.record_sigchld()

                # Update job state
                job = self.job_manager.get_job_by_pid(pid)
                if job:
                    job.update_process_status(pid, status)
                    job.update_state()

                    # Handle stopped foreground jobs
                    if job.state == JobState.STOPPED and job.foreground:
                        job.notified = False
                        # Return terminal control to shell
                        if self.state.supports_job_control:
                            try:
                                os.tcsetpgrp(self.state.terminal_fd, os.getpgrp())
                            except OSError:
                                pass

            except OSError:
                # No more children
                break
    finally:
        self._in_sigchld_handler = False
```

**Alternative - Defer Work to Main Loop:**

More complex but strictly signal-async-safe:

```python
class SignalManager(InteractiveComponent):
    """Manages signal handling for the interactive shell."""

    def __init__(self, shell):
        super().__init__(shell)
        self._original_handlers: Dict[int, Callable] = {}
        self._interactive_mode = not shell.state.is_script_mode

        # Create self-pipe for signal notification
        # This is signal-async-safe
        self._sigchld_pipe_r, self._sigchld_pipe_w = os.pipe()
        # Make non-blocking
        import fcntl
        flags = fcntl.fcntl(self._sigchld_pipe_w, fcntl.F_GETFL)
        fcntl.fcntl(self._sigchld_pipe_w, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def _handle_sigchld(self, signum, frame):
        """Minimal signal handler - just notify main loop.

        This handler does minimal work (only signal-async-safe operations).
        The actual job reaping happens in handle_pending_sigchld().
        """
        try:
            # Write one byte to wake up main loop
            # This is signal-async-safe
            os.write(self._sigchld_pipe_w, b'C')
        except OSError:
            # Pipe full or other error - main loop will handle anyway
            pass

    def handle_pending_sigchld(self):
        """Process pending SIGCHLD notifications.

        This should be called from the main REPL loop periodically.
        It does the actual job reaping outside of signal handler context.
        """
        # Drain notification pipe
        try:
            while True:
                data = os.read(self._sigchld_pipe_r, 1024)
                if not data:
                    break
        except OSError:
            pass

        # Now do the actual child reaping
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG | os.WUNTRACED)
                if pid == 0:
                    break

                # Record metrics
                if hasattr(self.state, 'process_metrics'):
                    self.state.process_metrics.record_sigchld()

                # Update job state
                job = self.job_manager.get_job_by_pid(pid)
                if job:
                    job.update_process_status(pid, status)
                    job.update_state()

                    if job.state == JobState.STOPPED and job.foreground:
                        job.notified = False
                        if self.state.supports_job_control:
                            try:
                                os.tcsetpgrp(self.state.terminal_fd, os.getpgrp())
                            except OSError:
                                pass
            except OSError:
                break

    def get_sigchld_fd(self) -> int:
        """Get file descriptor for SIGCHLD notifications.

        This can be used with select() to wait for child events.
        """
        return self._sigchld_pipe_r
```

**Update REPL to call handler:**

```python
# In interactive loop:
while True:
    # Check for background job state changes
    self.signal_manager.handle_pending_sigchld()

    # Show job notifications
    self.job_manager.notify_completed_jobs()

    # Read next command
    line = input(self.prompt_manager.get_prompt())
    # ...
```

**Benefits:**
- Strictly signal-async-safe (only os.write in handler)
- No risk of deadlock or corruption
- Can integrate with select() for efficiency
- Standard Unix practice (self-pipe trick)

**Trade-offs:**
- More complex implementation
- Requires REPL integration

---

### 7. Add Process Group Validation Diagnostics

**Create Diagnostic Tooling:**

**New File:** `psh/utils/process_debug.py`

```python
"""Process control debugging and validation utilities."""
import os
import signal
import sys
from typing import List

def validate_process_group_state(shell_state) -> List[str]:
    """Validate current process group configuration.

    This checks that the shell is properly configured for job control
    and identifies common misconfigurations.

    Args:
        shell_state: Shell state object

    Returns:
        List of issues found (empty if all OK)
    """
    issues = []

    try:
        shell_pid = os.getpid()
        shell_pgid = os.getpgrp()

        # Shell should be its own process group leader
        if shell_pgid != shell_pid:
            issues.append(
                f"Shell is not process group leader: "
                f"pid={shell_pid}, pgid={shell_pgid}"
            )

        # In interactive mode with TTY, check terminal control
        if shell_state.is_terminal and shell_state.supports_job_control:
            try:
                terminal_pgid = os.tcgetpgrp(shell_state.terminal_fd)

                # When not running commands, shell should be foreground
                if not shell_state.in_pipeline:
                    if terminal_pgid != shell_pgid:
                        issues.append(
                            f"Shell not foreground when idle: "
                            f"shell_pgid={shell_pgid}, terminal_pgid={terminal_pgid}"
                        )
            except OSError as e:
                issues.append(f"Cannot get terminal process group: {e}")

        # Check signal dispositions for interactive mode
        if not shell_state.is_script_mode:
            for sig in [signal.SIGTSTP, signal.SIGTTOU, signal.SIGTTIN]:
                try:
                    handler = signal.getsignal(sig)
                    if handler != signal.SIG_IGN:
                        sig_name = signal.Signals(sig).name if hasattr(signal, 'Signals') else f"Signal{sig}"
                        handler_name = getattr(handler, '__name__', str(handler))
                        issues.append(
                            f"{sig_name} not ignored in interactive mode: {handler_name}"
                        )
                except (ValueError, OSError):
                    pass

    except Exception as e:
        issues.append(f"Validation error: {e}")

    return issues


def diagnose_job_control_issue(job) -> str:
    """Diagnose why job might not be working correctly.

    Args:
        job: Job object to diagnose

    Returns:
        Diagnostic report string
    """
    lines = [f"Job {job.job_id} Diagnostics:"]
    lines.append(f"  Command:       {job.command}")
    lines.append(f"  State:         {job.state}")
    lines.append(f"  PGID:          {job.pgid}")
    lines.append(f"  Foreground:    {job.foreground}")
    lines.append(f"  Notified:      {job.notified}")
    lines.append(f"  Processes:     {len(job.processes)}")

    for i, proc in enumerate(job.processes):
        lines.append(f"\n  Process {i+1}:")
        lines.append(f"    PID:         {proc.pid}")
        lines.append(f"    Running:     {proc.running}")
        lines.append(f"    Completed:   {proc.completed}")
        lines.append(f"    Status:      {proc.status}")

        # Check if process still exists
        try:
            os.kill(proc.pid, 0)  # Signal 0 = check existence
            lines.append(f"    Exists:      Yes")
        except OSError:
            lines.append(f"    Exists:      No (zombie or reaped)")

        # Check process group
        try:
            actual_pgid = os.getpgid(proc.pid)
            if actual_pgid != job.pgid:
                lines.append(f"    WARNING:     Process in wrong pgid {actual_pgid}")
            else:
                lines.append(f"    PGID OK:     {actual_pgid}")
        except OSError as e:
            lines.append(f"    PGID ERROR:  {e}")

    return "\n".join(lines)


def report_process_tree(pgid: int = None) -> str:
    """Report process tree for debugging.

    Args:
        pgid: Process group to report (None for all)

    Returns:
        Process tree report
    """
    lines = ["Process Tree:"]

    try:
        if pgid is None:
            pgid = os.getpgrp()

        # Use ps to get process tree
        import subprocess
        result = subprocess.run(
            ['ps', '-o', 'pid,ppid,pgid,stat,command', '-g', str(pgid)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            lines.append(result.stdout)
        else:
            lines.append(f"  ps command failed: {result.stderr}")
    except Exception as e:
        lines.append(f"  Error getting process tree: {e}")

    return "\n".join(lines)
```

**Add Builtin Commands:**

**New File:** `psh/builtins/debug_builtin.py`

```python
"""Debug builtins for process control diagnostics."""
from .base import Builtin, builtin
from psh.utils.process_debug import (
    validate_process_group_state,
    diagnose_job_control_issue,
    report_process_tree
)

@builtin
class ValidateBuiltin(Builtin):
    """Validate process group configuration."""

    name = "validate-pgid"

    def execute(self, args: list[str], shell) -> int:
        """Validate process group state."""
        issues = validate_process_group_state(shell.state)

        if issues:
            self.error("Process group validation failed:", shell)
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("Process group validation passed")
            return 0


@builtin
class JobDiagBuiltin(Builtin):
    """Diagnose job control issues."""

    name = "jobdiag"

    def execute(self, args: list[str], shell) -> int:
        """Diagnose a specific job.

        Usage:
            jobdiag %1       # Diagnose job 1
            jobdiag %+       # Diagnose current job
        """
        if len(args) < 2:
            self.error("usage: jobdiag <job-spec>", shell)
            return 1

        job_spec = args[1]
        job = shell.job_manager.get_job(job_spec)

        if not job:
            self.error(f"job not found: {job_spec}", shell)
            return 1

        report = diagnose_job_control_issue(job)
        print(report)
        return 0


@builtin
class ProcTreeBuiltin(Builtin):
    """Show process tree for debugging."""

    name = "proctree"

    def execute(self, args: list[str], shell) -> int:
        """Show process tree."""
        report = report_process_tree()
        print(report)
        return 0
```

**Benefits:**
- Quick diagnosis of job control problems
- Validate shell configuration
- Inspect process group state
- Debugging tool for development

**Usage:**
```bash
$ psh -c "builtin validate-pgid"
Process group validation passed

$ psh -c "sleep 10 & builtin jobdiag %1"
Job 1 Diagnostics:
  Command:       sleep 10
  State:         running
  PGID:          12345
  Foreground:    False
  Processes:     1

  Process 1:
    PID:         12345
    Running:     True
    Exists:      Yes
    PGID OK:     12345
```

---

## Low Priority Recommendations

### 8. Add Comprehensive Debug Logging

**Create Process Control Logger:**

**New File:** `psh/utils/debug_logger.py`

```python
"""Debug logging for process control operations."""
import sys
from enum import Enum
from typing import Optional

class DebugCategory(Enum):
    """Categories of debug output."""
    FORK = "fork"
    SIGNAL = "signal"
    PGID = "pgid"
    TERMINAL = "terminal"
    WAIT = "wait"
    JOB = "job"

class ProcessControlLogger:
    """Logger for process control debug messages.

    This provides categorized debug output that can be enabled
    selectively for troubleshooting specific issues.

    Example:
        logger = ProcessControlLogger(shell.state)
        logger.enable(DebugCategory.FORK)
        logger.log(DebugCategory.FORK, "Forking child process")
    """

    def __init__(self, state):
        self.state = state
        self.enabled_categories = set()
        self.output_file = sys.stderr

    def enable(self, category: DebugCategory):
        """Enable debug output for a category."""
        self.enabled_categories.add(category)

    def disable(self, category: DebugCategory):
        """Disable debug output for a category."""
        self.enabled_categories.discard(category)

    def enable_all(self):
        """Enable all debug categories."""
        self.enabled_categories = set(DebugCategory)

    def disable_all(self):
        """Disable all debug categories."""
        self.enabled_categories.clear()

    def is_enabled(self, category: DebugCategory) -> bool:
        """Check if category is enabled."""
        return (category in self.enabled_categories or
                self.state.options.get('debug-exec'))

    def log(self, category: DebugCategory, message: str,
            pid: Optional[int] = None):
        """Log a debug message.

        Args:
            category: Debug category
            message: Message to log
            pid: Optional PID to include in output
        """
        if not self.is_enabled(category):
            return

        prefix = f"[{category.value.upper()}]"
        if pid is not None:
            prefix += f" [PID {pid}]"

        print(f"{prefix} {message}", file=self.output_file)
```

**Integration:**

```python
# In ShellState:
from psh.utils.debug_logger import ProcessControlLogger

@dataclass
class ShellState:
    # ... existing fields ...

    # Debug logging
    debug_logger: Optional[ProcessControlLogger] = None

    def __post_init__(self):
        # ... existing initialization ...
        self.debug_logger = ProcessControlLogger(self)
```

**Usage Throughout Executor:**

```python
# In pipeline.py:
self.state.debug_logger.log(
    DebugCategory.FORK,
    f"Forking child {i+1}/{len(pipeline.commands)}",
    pid=os.getpid()
)

self.state.debug_logger.log(
    DebugCategory.PGID,
    f"Setting child {pid} to pgid {pgid}"
)

self.state.debug_logger.log(
    DebugCategory.TERMINAL,
    f"Transferring terminal control to pgid {pgid}"
)

# In job_control.py:
self.shell_state.debug_logger.log(
    DebugCategory.WAIT,
    f"Waiting for job {job.job_id} (pgid {job.pgid})"
)

self.shell_state.debug_logger.log(
    DebugCategory.JOB,
    f"Job {job.job_id} state changed: {old_state} -> {new_state}"
)

# In signal_manager.py:
self.state.debug_logger.log(
    DebugCategory.SIGNAL,
    f"Received SIGCHLD, reaping children"
)
```

**Shell Option:**

```bash
$ psh --debug-category=fork,pgid -c "echo hello | cat"
[FORK] [PID 12345] Forking child 1/2
[PGID] Setting child 12346 to pgid 12346
[FORK] [PID 12345] Forking child 2/2
[PGID] Setting child 12347 to pgid 12346
[TERMINAL] Transferring terminal control to pgid 12346
```

---

### 9. Add Safety Checks for Child Process Cleanup

**Ensure Children Always Exit:**

Create a standard pattern for all fork code:

```python
def safe_fork_and_exec(self, execute_fn):
    """Safely fork and execute a function, ensuring child always exits.

    This wrapper ensures that:
    1. Child process always exits with os._exit()
    2. Exceptions are caught and reported
    3. Signals are properly handled
    4. Exit codes are meaningful

    Args:
        execute_fn: Function to execute in child (should return exit code)

    Returns:
        PID of child process (in parent), does not return (in child)
    """
    pid = os.fork()

    if pid == 0:  # Child process
        exit_code = 127  # Default: command not found

        try:
            # Execute the provided function
            exit_code = execute_fn()

            # Ensure exit code is an integer
            if not isinstance(exit_code, int):
                exit_code = 0 if exit_code else 1

        except SystemExit as e:
            # Handle sys.exit() calls
            exit_code = e.code if isinstance(e.code, int) else 1

        except KeyboardInterrupt:
            # Ctrl-C in child
            exit_code = 130  # 128 + SIGINT

        except Exception as e:
            # Unexpected error
            print(f"psh: error: {e}", file=sys.stderr)
            import traceback
            if self.state.options.get('debug-exec'):
                traceback.print_exc()
            exit_code = 1

        finally:
            # Ensure we ALWAYS exit - no exceptions
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except:
                pass

            # Use os._exit() not sys.exit() to avoid Python cleanup
            os._exit(exit_code)

        # This should never be reached
        os._exit(127)

    else:  # Parent process
        return pid
```

**Usage:**

```python
# Instead of:
pid = os.fork()
if pid == 0:
    # setup...
    exit_code = execute_command()
    os._exit(exit_code)

# Use:
pid = self.safe_fork_and_exec(lambda: self.execute_command())
```

---

### 10. Document Signal Architecture

**Create Comprehensive Documentation:**

**New File:** `docs/signal_architecture.md`

```markdown
# Signal Handling Architecture

## Overview

PSH implements comprehensive signal handling to support:
- Interactive job control (Ctrl-Z, Ctrl-C, fg, bg)
- User-defined signal traps
- Proper process group management
- Background job notifications

## Signal Dispositions by Shell Mode

### Interactive Mode

| Signal   | Handler          | Purpose |
|----------|------------------|---------|
| SIGINT   | Custom           | Ctrl-C: Check traps, then interrupt |
| SIGTERM  | Custom           | Termination: Check traps, then terminate |
| SIGHUP   | Custom           | Hangup: Check traps, then exit |
| SIGQUIT  | Custom           | Quit: Check traps, then dump core |
| SIGTSTP  | SIG_IGN          | Ctrl-Z: Shell shouldn't suspend itself |
| SIGTTOU  | SIG_IGN          | Background write: Shell continues |
| SIGTTIN  | SIG_IGN          | Background read: Shell continues |
| SIGCHLD  | Custom           | Child state: Async job tracking |
| SIGPIPE  | SIG_DFL          | Broken pipe: Clean exit |

### Script Mode

| Signal   | Handler          | Purpose |
|----------|------------------|---------|
| SIGINT   | SIG_DFL          | Default interrupt behavior |
| SIGTERM  | SIG_DFL          | Default termination |
| SIGTSTP  | SIG_DFL          | Default stop behavior |
| SIGTTOU  | SIG_IGN          | Ignore background write |
| SIGTTIN  | SIG_IGN          | Ignore background read |
| SIGCHLD  | SIG_DFL          | Default child handling |
| SIGPIPE  | SIG_DFL          | Broken pipe = exit |

## Signal Handler Call Graphs

### SIGCHLD Handler

```
SIGCHLD received
  ↓
_handle_sigchld()
  ↓
  ├─→ os.waitpid(-1, WNOHANG|WUNTRACED)  [loop until no more]
  ├─→ job.update_process_status(pid, status)
  ├─→ job.update_state()
  └─→ if job stopped and foreground:
        └─→ os.tcsetpgrp(0, shell_pgid)  [return terminal to shell]
```

### SIGINT Handler (Interactive)

```
SIGINT received
  ↓
_handle_signal_with_trap_check(SIGINT)
  ↓
  ├─→ Check for user trap
  │   ├─→ If trap='': return (ignored)
  │   └─→ If trap set: execute_trap()
  └─→ No trap: _handle_sigint()
        └─→ print newline, let command handle it
```

## Race Condition Mitigation

### 1. SIGCHLD vs wait_for_job Race

**Problem:** SIGCHLD handler may reap child before explicit wait() call.

**Solution:**
- SIGCHLD handler stores status in `job.processes[i].status`
- `wait_for_job()` checks stored status if waitpid() returns ECHILD
- Optional: Block SIGCHLD during waitpid() (see Recommendation #2)

**Code Pattern:**
```python
# In SIGCHLD handler:
job.update_process_status(pid, status)

# In wait_for_job():
try:
    pid, status = os.waitpid(-job.pgid, os.WUNTRACED)
except OSError:
    # Already reaped - check stored status
    if proc.completed and proc.status is not None:
        status = proc.status
```

### 2. Process Group Creation Race

**Problem:** Parent and child both call setpgid(), order undefined.

**Solution:**
- Both parent and child attempt setpgid()
- Child polls for up to 200ms to detect parent's setpgid()
- Standard Unix practice (Stevens APUE §9.4)

**Code Pattern:**
```python
# Parent:
if i == 0:
    pgid = pid
os.setpgid(pid, pgid)

# Child:
if i == 0:
    os.setpgid(0, 0)  # Become leader
else:
    # Wait for parent to set our pgid
    for attempt in range(200):
        if os.getpgrp() != os.getpid():
            break  # Parent set our pgid
        time.sleep(0.001)
```

### 3. Terminal Control Transfer Race

**Problem:** Child may attempt terminal I/O before tcsetpgrp() called.

**Solution:**
- Child temporarily ignores SIGTTOU: `signal.signal(SIGTTOU, SIG_IGN)`
- Parent transfers terminal control immediately after fork
- Child restores SIGTTOU to SIG_DFL after terminal transfer

**Code Pattern:**
```python
# Child:
signal.signal(signal.SIGTTOU, SIG_IGN)  # Prevent suspension
# ... wait for terminal transfer ...
if is_foreground:
    signal.signal(signal.SIGTTOU, signal.SIG_DFL)  # Restore

# Parent:
os.tcsetpgrp(0, pgid)  # Transfer before wait
```

## Trap Integration

User-defined traps integrate with signal handlers via two-stage handling:

1. **First stage:** Signal caught by `_handle_signal_with_trap_check()`
2. **Check traps:** Look up signal in trap table
3. **Execute trap:** If found, run user's trap command
4. **Default behavior:** If no trap, use shell's default handling

**Example:**
```bash
$ trap 'echo "Caught INT"' INT
$ sleep 10
^C
Caught INT
```

## Signal-Async-Safe Operations

Signal handlers must only use async-signal-safe functions. PSH handlers use:

**Safe:**
- `os.waitpid()` - async-signal-safe
- `os.write()` - async-signal-safe
- `os.getpgrp()`, `os.tcsetpgrp()` - async-signal-safe

**Unsafe (avoided in handlers):**
- `print()` - not async-signal-safe (uses Python locks)
- `malloc()` - not async-signal-safe
- Most Python operations - not async-signal-safe

**Current limitation:** SIGCHLD handler does non-safe operations (job updates).
**Future improvement:** Use self-pipe trick to defer work to main loop.

## Debugging Signals

### View Current Signal Dispositions

```bash
$ psh -c "builtin signals"
Signal Disposition Report:
  SIGINT       -> _handle_signal_with_trap_check
  SIGTERM      -> _handle_signal_with_trap_check
  SIGTSTP      -> SIG_IGN
  ...
```

### Validate Signal Configuration

```bash
$ psh -c "builtin signals --validate"
Signal validation passed
```

### Enable Signal Debug Logging

```bash
$ psh --debug-exec -c "echo hello | cat"
[SIGNAL] Setting up interactive mode signal handlers
[SIGNAL] SIGINT -> custom handler
[SIGNAL] SIGCHLD -> custom handler
```

## References

- Stevens, W. Richard. *Advanced Programming in the UNIX Environment*, 3rd ed. Chapter 9 (Process Relationships) and Chapter 10 (Signals).
- POSIX.1-2017, Section 2.11 (Signals and Error Handling)
- Bash Reference Manual, Section 3.7.6 (Signals)
```

---

## Implementation Priority Summary

### Do Immediately (High Priority)
1. ✅ **Increase PGID sync timeout** to 200ms - Simple, low risk, high benefit
2. ✅ **Add TTY detection** - Improves error messages, helps testing
3. ✅ **Implement signal blocking** - Eliminates race condition

### Do Soon (Medium Priority)
4. ✅ **Centralize signal tracking** - Great for debugging, low risk
5. ✅ **Add process metrics** - Valuable diagnostics, non-invasive
6. ✅ **Improve SIGCHLD handler** - Choose simpler re-entrance guard first

### Nice to Have (Low Priority)
7. ✅ **Process group validation** - Useful debug tools
8. ✅ **Enhanced debug logging** - Better troubleshooting
9. ✅ **Documentation** - Essential for maintenance
10. ✅ **Child cleanup safety** - Defense in depth

## Testing Recommendations

After implementing each recommendation, test with:

```bash
# Basic functionality
$ psh -c "echo hello | cat"

# Under load
$ stress-ng --cpu 8 --timeout 60s &
$ psh -c "seq 1 100 | xargs -P 10 -I {} echo test {}"

# Job control
$ psh
psh$ sleep 10 &
psh$ jobs
psh$ fg %1
^Z
psh$ bg %1
psh$ jobs

# Without TTY
$ echo "echo hello" | psh
$ psh -c "echo hello" < /dev/null

# In restricted environments
$ docker run -it alpine sh -c "psh -c 'echo hello'"
```

## Conclusion

The current PSH implementation is already high quality. These recommendations primarily add:
- **Observability** - Metrics, logging, diagnostics
- **Debuggability** - Signal tracking, validation tools
- **Reliability** - Longer timeouts, signal blocking, graceful degradation

All recommendations are **backward compatible** and can be implemented incrementally.

---

**Document Status:** Draft for Review
**Next Steps:** Review with maintainers, prioritize implementation, create issues
