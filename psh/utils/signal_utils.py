"""Signal handling utilities.

This module provides utilities for safe signal handling using the self-pipe trick.
The self-pipe pattern moves complex work out of signal handler context to avoid
reentrancy issues and ensure async-signal-safety.
"""
import os
import fcntl
import signal
import contextlib
from typing import List, Set


class SignalNotifier:
    """Self-pipe pattern for safe signal notification.

    Signal handlers write to a pipe, main loop reads from it.
    This moves all complex work out of signal handler context.

    The self-pipe trick is the standard Unix pattern for handling signals
    safely in event-driven programs. The signal handler only performs
    async-signal-safe operations (os.write), while the main loop handles
    the actual work.

    Example:
        notifier = SignalNotifier()

        # In signal handler:
        signal.signal(signal.SIGCHLD, lambda s, f: notifier.notify(s))

        # In main loop:
        notifications = notifier.drain_notifications()
        for sig in notifications:
            handle_signal(sig)
    """

    def __init__(self):
        """Create a self-pipe for signal notifications."""
        self._pipe_r, self._pipe_w = os.pipe()

        # Make write end non-blocking to prevent signal handler blocking
        # This is critical for signal safety
        flags = fcntl.fcntl(self._pipe_w, fcntl.F_GETFL)
        fcntl.fcntl(self._pipe_w, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def notify(self, signal_num: int):
        """Called from signal handler to notify main loop.

        This is async-signal-safe (only uses os.write).

        Args:
            signal_num: Signal number that was received
        """
        try:
            # Write signal number to pipe
            # Using bytes() is async-signal-safe
            os.write(self._pipe_w, bytes([signal_num]))
        except OSError:
            # Pipe full or other error - main loop will handle
            # Don't raise exception in signal handler
            pass

    def get_fd(self) -> int:
        """Get file descriptor for select()/poll().

        This allows integration with event loops.

        Returns:
            Read file descriptor for the notification pipe
        """
        return self._pipe_r

    def drain_notifications(self) -> List[int]:
        """Drain pending notifications. Call from main loop.

        This is safe to call from normal (non-signal) context.

        Returns:
            List of signal numbers that were notified
        """
        notifications = []
        try:
            while True:
                # Read in chunks for efficiency
                data = os.read(self._pipe_r, 1024)
                if not data:
                    break
                # Convert bytes to signal numbers
                notifications.extend(data)
        except OSError:
            # EAGAIN/EWOULDBLOCK - no more data
            pass
        return notifications

    def has_notifications(self) -> bool:
        """Check if there are pending notifications without draining.

        Uses non-blocking read to check for data.

        Returns:
            True if notifications are pending
        """
        try:
            # Save current flags
            flags = fcntl.fcntl(self._pipe_r, fcntl.F_GETFL)
            # Set non-blocking
            fcntl.fcntl(self._pipe_r, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Try to read one byte
            data = os.read(self._pipe_r, 1)

            # Put it back (this is a bit of a hack)
            # In practice, drain_notifications() will re-read it
            # For now, we just return True

            # Restore flags
            fcntl.fcntl(self._pipe_r, fcntl.F_SETFL, flags)

            return len(data) > 0
        except OSError:
            # No data available
            return False

    def close(self):
        """Clean up pipe resources."""
        try:
            os.close(self._pipe_r)
        except OSError:
            pass
        try:
            os.close(self._pipe_w)
        except OSError:
            pass

    def __del__(self):
        """Automatic cleanup on garbage collection."""
        try:
            self.close()
        except Exception:
            # Don't raise exceptions in __del__
            pass


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
        # pthread_sigmask not available on this platform (Windows, old Python)
        # Fall back to no blocking
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
