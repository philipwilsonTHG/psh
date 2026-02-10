"""Tests for SignalRegistry functionality."""
import signal

from psh.utils.signal_utils import SignalRegistry, get_signal_registry, set_signal_registry


class TestSignalRegistry:
    """Tests for the SignalRegistry class."""

    def test_registry_creation(self):
        """Test that registry can be created."""
        registry = SignalRegistry()
        assert registry is not None
        assert len(registry.get_all_handlers()) == 0

    def test_register_handler(self):
        """Test registering a signal handler."""
        registry = SignalRegistry()

        def handler(sig, frame):
            pass

        # Register handler
        registry.register(signal.SIGUSR1, handler, "test")

        # Verify it was registered
        record = registry.get_handler(signal.SIGUSR1)
        assert record is not None
        assert record.signal_num == signal.SIGUSR1
        # Signal name should be "Signal-N" where N is the signal number
        assert record.signal_name == f"Signal-{signal.SIGUSR1}"
        assert record.handler == handler
        assert record.component == "test"

    def test_register_sig_dfl(self):
        """Test registering SIG_DFL."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        record = registry.get_handler(signal.SIGUSR1)
        assert record is not None
        assert record.handler == signal.SIG_DFL

    def test_register_sig_ign(self):
        """Test registering SIG_IGN."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_IGN, "test")

        record = registry.get_handler(signal.SIGUSR1)
        assert record is not None
        assert record.handler == signal.SIG_IGN

    def test_get_all_handlers(self):
        """Test getting all registered handlers."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test1")
        registry.register(signal.SIGUSR2, signal.SIG_IGN, "test2")

        handlers = registry.get_all_handlers()
        assert len(handlers) == 2
        assert signal.SIGUSR1 in handlers
        assert signal.SIGUSR2 in handlers

    def test_handler_history(self):
        """Test that handler changes are tracked in history."""
        registry = SignalRegistry()

        def handler1(sig, frame):
            pass

        def handler2(sig, frame):
            pass

        # Register multiple handlers
        registry.register(signal.SIGUSR1, handler1, "test1")
        registry.register(signal.SIGUSR1, handler2, "test2")
        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test3")

        # Check history
        history = registry.get_history(signal.SIGUSR1)
        assert len(history) == 3
        assert history[0].handler == handler1
        assert history[0].component == "test1"
        assert history[1].handler == handler2
        assert history[1].component == "test2"
        assert history[2].handler == signal.SIG_DFL
        assert history[2].component == "test3"

        # Current should be the last one
        current = registry.get_handler(signal.SIGUSR1)
        assert current.handler == signal.SIG_DFL

    def test_validate_no_issues(self):
        """Test validation with no issues."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        issues = registry.validate()
        assert len(issues) == 0

    def test_validate_many_changes(self):
        """Test validation detects many changes."""
        registry = SignalRegistry()

        # Register the same signal 6 times
        for i in range(6):
            registry.register(signal.SIGUSR1, signal.SIG_DFL, f"test{i}")

        issues = registry.validate()
        assert len(issues) > 0
        # Should mention the signal that has many changes
        assert f"Signal-{signal.SIGUSR1}" in issues[0]
        assert "6 times" in issues[0]

    def test_report_empty(self):
        """Test report with no handlers."""
        registry = SignalRegistry()

        report = registry.report()
        assert "No signal handlers registered" in report

    def test_report_with_handlers(self):
        """Test report with handlers."""
        registry = SignalRegistry()

        def handler(sig, frame):
            pass

        registry.register(signal.SIGUSR1, handler, "TestComponent")

        report = registry.report()
        assert "Signal Handler Registry Report" in report
        assert "TestComponent" in report
        assert "handler()" in report

    def test_report_verbose(self):
        """Test verbose report includes history."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test1")
        registry.register(signal.SIGUSR1, signal.SIG_IGN, "test2")

        report = registry.report(verbose=True)
        assert "Signal Handler History" in report
        assert "test1" in report
        assert "test2" in report

    def test_format_handler_function(self):
        """Test handler formatting for functions."""
        registry = SignalRegistry()

        def my_handler(sig, frame):
            pass

        registry.register(signal.SIGUSR1, my_handler, "test")

        record = registry.get_handler(signal.SIGUSR1)
        formatted = registry._format_handler(record.handler)
        assert "my_handler()" in formatted

    def test_format_handler_sig_dfl(self):
        """Test handler formatting for SIG_DFL."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        record = registry.get_handler(signal.SIGUSR1)
        formatted = registry._format_handler(record.handler)
        assert "SIG_DFL" in formatted
        assert "default" in formatted

    def test_format_handler_sig_ign(self):
        """Test handler formatting for SIG_IGN."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_IGN, "test")

        record = registry.get_handler(signal.SIGUSR1)
        formatted = registry._format_handler(record.handler)
        assert "SIG_IGN" in formatted
        assert "ignore" in formatted

    def test_clear(self):
        """Test clearing the registry."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")
        assert len(registry.get_all_handlers()) == 1

        registry.clear()
        assert len(registry.get_all_handlers()) == 0
        assert len(registry.get_history()) == 0

    def test_enable_disable(self):
        """Test enabling/disabling the registry."""
        registry = SignalRegistry()

        # Disable registry
        registry.disable()
        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        # Should not be tracked when disabled
        assert len(registry.get_all_handlers()) == 0

        # Re-enable
        registry.enable()
        registry.register(signal.SIGUSR2, signal.SIG_DFL, "test")

        # Should be tracked now
        assert len(registry.get_all_handlers()) == 1


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_signal_registry_creates(self):
        """Test that get_signal_registry creates registry."""
        # Clear global
        set_signal_registry(None)

        # Get should create
        registry = get_signal_registry(create=True)
        assert registry is not None

    def test_get_signal_registry_no_create(self):
        """Test get_signal_registry with create=False."""
        # Clear global
        set_signal_registry(None)

        # Get without create should return None
        registry = get_signal_registry(create=False)
        assert registry is None

    def test_set_signal_registry(self):
        """Test setting the global registry."""
        custom_registry = SignalRegistry()

        set_signal_registry(custom_registry)

        retrieved = get_signal_registry(create=False)
        assert retrieved is custom_registry

    def test_global_registry_persistence(self):
        """Test that global registry persists across calls."""
        set_signal_registry(None)

        # First call creates
        registry1 = get_signal_registry(create=True)

        # Second call returns same instance
        registry2 = get_signal_registry(create=True)

        assert registry1 is registry2


class TestSignalNames:
    """Tests for signal name mapping."""

    def test_known_signal_names(self):
        """Test that known signals have proper names."""
        registry = SignalRegistry()

        # Test some known signals
        assert registry.SIGNAL_NAMES[signal.SIGINT] == "SIGINT"
        assert registry.SIGNAL_NAMES[signal.SIGTERM] == "SIGTERM"
        assert registry.SIGNAL_NAMES[signal.SIGCHLD] == "SIGCHLD"

    def test_unknown_signal_name(self):
        """Test that unknown signals get generic names."""
        registry = SignalRegistry()

        # Register SIGUSR1 (not in known signals)
        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        record = registry.get_handler(signal.SIGUSR1)
        # Should have generic name like "Signal-10"
        assert record.signal_name.startswith("Signal-")


class TestStackCapture:
    """Tests for stack trace capture."""

    def test_capture_stack_disabled_by_default(self):
        """Test that stack capture is disabled by default."""
        registry = SignalRegistry()

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        record = registry.get_handler(signal.SIGUSR1)
        assert record.call_stack is None

    def test_capture_stack_enabled(self):
        """Test stack capture when enabled."""
        registry = SignalRegistry(capture_stack=True)

        registry.register(signal.SIGUSR1, signal.SIG_DFL, "test")

        record = registry.get_handler(signal.SIGUSR1)
        assert record.call_stack is not None
        # Stack should contain Python file references
        assert ".py" in record.call_stack
        # Should contain multiple frames
        assert "File" in record.call_stack
