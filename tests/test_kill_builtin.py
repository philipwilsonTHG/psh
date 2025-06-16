"""Tests for the kill builtin command."""

import os
import signal
import sys
from unittest.mock import patch, MagicMock, call
import pytest

from psh.builtins.kill_command import KillBuiltin, SIGNAL_NAMES, SIGNAL_NUMBERS
from psh.job_control import Job, Process


class TestKillBuiltin:
    """Test cases for kill builtin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.kill = KillBuiltin()
        self.mock_shell = MagicMock()
        self.mock_shell.job_manager = MagicMock()
    
    def test_kill_is_registered(self):
        """Test that kill builtin is properly registered."""
        assert self.kill.name == "kill"
        assert "send signals" in self.kill.description.lower()
    
    def test_synopsis_and_help(self):
        """Test synopsis and help text."""
        assert "kill" in self.kill.synopsis
        assert "-l" in self.kill.synopsis
        assert "signal" in self.kill.help.lower()
        assert "process" in self.kill.help.lower()
    
    def test_no_arguments_shows_usage(self, capsys):
        """Test that kill with no arguments shows usage."""
        result = self.kill.execute(["kill"], self.mock_shell)
        assert result == 2
        captured = capsys.readouterr()
        assert "Usage:" in captured.err
    
    def test_signal_parsing_by_name(self):
        """Test parsing signal names."""
        # Test standard signal names
        assert self.kill._parse_signal("TERM") == signal.SIGTERM
        assert self.kill._parse_signal("term") == signal.SIGTERM
        assert self.kill._parse_signal("KILL") == signal.SIGKILL
        assert self.kill._parse_signal("HUP") == signal.SIGHUP
        
        # Test with SIG prefix
        assert self.kill._parse_signal("SIGTERM") == signal.SIGTERM
        assert self.kill._parse_signal("sigkill") == signal.SIGKILL
    
    def test_signal_parsing_by_number(self):
        """Test parsing signal numbers."""
        assert self.kill._parse_signal("15") == 15
        assert self.kill._parse_signal("9") == 9
        assert self.kill._parse_signal("1") == 1
        assert self.kill._parse_signal("0") == 0
    
    def test_invalid_signal_parsing(self):
        """Test error handling for invalid signals."""
        with pytest.raises(ValueError, match="invalid signal name"):
            self.kill._parse_signal("INVALID")
        
        with pytest.raises(ValueError, match="invalid signal number"):
            self.kill._parse_signal("999")
        
        with pytest.raises(ValueError, match="invalid signal number"):
            self.kill._parse_signal("-5")
        
        with pytest.raises(ValueError, match="invalid signal specification"):
            self.kill._parse_signal("")
    
    def test_argument_parsing_signal_name(self):
        """Test parsing -signal_name format."""
        signal_num, targets, list_signals = self.kill._parse_args(["-TERM", "123"])
        assert signal_num == signal.SIGTERM
        assert targets == ["123"]
        assert not list_signals
        
        signal_num, targets, list_signals = self.kill._parse_args(["-9", "456"])
        assert signal_num == 9
        assert targets == ["456"]
        assert not list_signals
    
    def test_argument_parsing_s_option(self):
        """Test parsing -s signal_name format."""
        signal_num, targets, list_signals = self.kill._parse_args(["-s", "KILL", "789"])
        assert signal_num == signal.SIGKILL
        assert targets == ["789"]
        assert not list_signals
        
        signal_num, targets, list_signals = self.kill._parse_args(["-sINT", "101"])
        assert signal_num == signal.SIGINT
        assert targets == ["101"]
        assert not list_signals
    
    def test_argument_parsing_list_option(self):
        """Test parsing -l option."""
        signal_num, targets, list_signals = self.kill._parse_args(["-l"])
        assert list_signals
        assert targets == []
        
        signal_num, targets, list_signals = self.kill._parse_args(["-l", "143"])
        assert list_signals
        assert targets == ["143"]
    
    def test_argument_parsing_multiple_pids(self):
        """Test parsing multiple PIDs."""
        signal_num, targets, list_signals = self.kill._parse_args(["123", "456", "789"])
        assert signal_num == signal.SIGTERM  # Default
        assert targets == ["123", "456", "789"]
        assert not list_signals
    
    def test_argument_parsing_with_double_dash(self):
        """Test parsing with -- separator."""
        signal_num, targets, list_signals = self.kill._parse_args(["-TERM", "--", "123", "-456"])
        assert signal_num == signal.SIGTERM
        assert targets == ["123", "-456"]
        assert not list_signals
    
    def test_argument_parsing_missing_signal_after_s(self):
        """Test error when -s has no argument."""
        with pytest.raises(ValueError, match="option requires an argument"):
            self.kill._parse_args(["-s"])
    
    def test_resolve_targets_pids(self):
        """Test resolving regular PIDs."""
        pids = self.kill._resolve_targets(["123", "456"], self.mock_shell)
        assert pids == [123, 456]
    
    def test_resolve_targets_invalid_pid(self, capsys):
        """Test resolving invalid PIDs."""
        pids = self.kill._resolve_targets(["invalid", "123"], self.mock_shell)
        assert pids == [123]
        captured = capsys.readouterr()
        assert "invalid process id" in captured.err
    
    def test_resolve_targets_job_specs(self):
        """Test resolving job specifications."""
        # Mock job with processes
        mock_job = MagicMock()
        mock_process1 = MagicMock()
        mock_process1.pid = 100
        mock_process2 = MagicMock()
        mock_process2.pid = 101
        mock_job.processes = [mock_process1, mock_process2]
        
        self.mock_shell.job_manager.parse_job_spec.return_value = mock_job
        
        pids = self.kill._resolve_targets(["%1"], self.mock_shell)
        assert pids == [100, 101]
        self.mock_shell.job_manager.parse_job_spec.assert_called_with("%1")
    
    def test_resolve_targets_nonexistent_job(self, capsys):
        """Test resolving non-existent job."""
        self.mock_shell.job_manager.parse_job_spec.return_value = None
        
        pids = self.kill._resolve_targets(["%99"], self.mock_shell)
        assert pids == []
        captured = capsys.readouterr()
        assert "no such job" in captured.err
    
    @patch('os.kill')
    def test_send_signals_success(self, mock_kill):
        """Test successful signal sending."""
        result = self.kill._send_signals(signal.SIGTERM, [123, 456])
        assert result == 0
        mock_kill.assert_has_calls([
            call(123, signal.SIGTERM),
            call(456, signal.SIGTERM)
        ])
    
    @patch('os.kill')
    def test_send_signals_no_such_process(self, mock_kill, capsys):
        """Test signal sending to non-existent process."""
        mock_kill.side_effect = [None, ProcessLookupError()]
        
        result = self.kill._send_signals(signal.SIGTERM, [123, 456])
        assert result == 0  # At least one succeeded
        captured = capsys.readouterr()
        assert "No such process" in captured.err
    
    @patch('os.kill')
    def test_send_signals_permission_denied(self, mock_kill, capsys):
        """Test signal sending with permission denied."""
        mock_kill.side_effect = PermissionError()
        
        result = self.kill._send_signals(signal.SIGTERM, [123])
        assert result == 1  # All failed
        captured = capsys.readouterr()
        assert "Operation not permitted" in captured.err
    
    @patch('os.killpg')
    def test_send_signals_process_group(self, mock_killpg):
        """Test sending signals to process groups."""
        result = self.kill._send_signals(signal.SIGTERM, [-123])
        assert result == 0
        mock_killpg.assert_called_with(123, signal.SIGTERM)
    
    @patch('os.killpg')
    @patch('os.getpgrp')
    def test_send_signals_current_process_group(self, mock_getpgrp, mock_killpg):
        """Test sending signal to current process group (PID 0)."""
        mock_getpgrp.return_value = 500
        
        result = self.kill._send_signals(signal.SIGTERM, [0])
        assert result == 0
        mock_killpg.assert_called_with(500, signal.SIGTERM)
    
    def test_list_signals_all(self, capsys):
        """Test listing all signals."""
        result = self.kill._list_signals([])
        assert result == 0
        captured = capsys.readouterr()
        # Should contain some standard signals
        assert "SIGTERM" in captured.out or "TERM" in captured.out
        assert "SIGKILL" in captured.out or "KILL" in captured.out
    
    def test_list_signals_for_exit_status(self, capsys):
        """Test listing signal for specific exit status."""
        # Exit status 143 = 128 + 15 (SIGTERM)
        result = self.kill._list_signals(["143"])
        assert result == 0
        captured = capsys.readouterr()
        assert "SIGTERM" in captured.out or "TERM" in captured.out
    
    def test_list_signals_invalid_exit_status(self, capsys):
        """Test listing signal for invalid exit status."""
        result = self.kill._list_signals(["invalid"])
        assert result == 1
        captured = capsys.readouterr()
        assert "invalid exit status" in captured.err
    
    def test_list_signals_non_signal_exit(self, capsys):
        """Test listing for non-signal exit status."""
        result = self.kill._list_signals(["1"])
        assert result == 0
        captured = capsys.readouterr()
        assert "not from signal" in captured.out
    
    @patch('os.kill')
    def test_execute_basic_kill(self, mock_kill):
        """Test basic kill execution."""
        result = self.kill.execute(["kill", "123"], self.mock_shell)
        assert result == 0
        mock_kill.assert_called_with(123, signal.SIGTERM)
    
    @patch('os.kill')
    def test_execute_kill_with_signal(self, mock_kill):
        """Test kill execution with signal specification."""
        result = self.kill.execute(["kill", "-9", "123"], self.mock_shell)
        assert result == 0
        mock_kill.assert_called_with(123, 9)
    
    def test_execute_list_signals(self, capsys):
        """Test kill -l execution."""
        result = self.kill.execute(["kill", "-l"], self.mock_shell)
        assert result == 0
        captured = capsys.readouterr()
        assert len(captured.out) > 0
    
    @patch('os.kill')
    def test_execute_job_spec(self, mock_kill):
        """Test killing a job by job specification."""
        # Mock job with one process
        mock_job = MagicMock()
        mock_process = MagicMock()
        mock_process.pid = 200
        mock_job.processes = [mock_process]
        
        self.mock_shell.job_manager.parse_job_spec.return_value = mock_job
        
        result = self.kill.execute(["kill", "%1"], self.mock_shell)
        assert result == 0
        mock_kill.assert_called_with(200, signal.SIGTERM)
    
    def test_execute_no_process_specified(self, capsys):
        """Test error when no process is specified."""
        result = self.kill.execute(["kill", "-TERM"], self.mock_shell)
        assert result == 2
        captured = capsys.readouterr()
        assert "no process specified" in captured.err
    
    @patch('os.kill')
    def test_execute_exception_handling(self, mock_kill, capsys):
        """Test exception handling in execute."""
        # Make _parse_signal raise an exception
        with patch.object(self.kill, '_parse_signal', side_effect=ValueError("test error")):
            result = self.kill.execute(["kill", "-INVALID", "123"], self.mock_shell)
            assert result == 1
            captured = capsys.readouterr()
            assert "test error" in captured.err


class TestKillBuiltinIntegration:
    """Integration tests for kill builtin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.kill = KillBuiltin()
        self.mock_shell = MagicMock()
        self.mock_shell.job_manager = MagicMock()
    
    @patch('os.kill')
    def test_multiple_targets_mixed_success(self, mock_kill, capsys):
        """Test killing multiple targets with mixed success."""
        # First succeeds, second fails
        mock_kill.side_effect = [None, ProcessLookupError()]
        
        result = self.kill.execute(["kill", "123", "456"], self.mock_shell)
        assert result == 0  # At least one succeeded
        captured = capsys.readouterr()
        assert "No such process" in captured.err
    
    @patch('os.kill')
    def test_complex_argument_parsing(self, mock_kill):
        """Test complex argument combinations."""
        result = self.kill.execute(["kill", "-s", "KILL", "123", "456"], self.mock_shell)
        assert result == 0
        mock_kill.assert_has_calls([
            call(123, signal.SIGKILL),
            call(456, signal.SIGKILL)
        ])
    
    def test_signal_name_constants(self):
        """Test that signal name constants are properly defined."""
        # Test that important signals are mapped
        assert 'TERM' in SIGNAL_NAMES
        assert 'KILL' in SIGNAL_NAMES
        assert 'HUP' in SIGNAL_NAMES
        assert 'INT' in SIGNAL_NAMES
        
        # Test reverse mapping
        assert signal.SIGTERM in SIGNAL_NUMBERS
        assert signal.SIGKILL in SIGNAL_NUMBERS
        assert SIGNAL_NUMBERS[SIGNAL_NAMES['TERM']] == 'TERM'


class TestKillBuiltinEdgeCases:
    """Edge case tests for kill builtin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.kill = KillBuiltin()
        self.mock_shell = MagicMock()
    
    def test_signal_zero_test_existence(self):
        """Test signal 0 for testing process existence."""
        signal_num, targets, list_signals = self.kill._parse_args(["-0", "123"])
        assert signal_num == 0
        assert targets == ["123"]
    
    def test_negative_pid_process_group(self):
        """Test negative PID for process group signaling."""
        pids = self.kill._resolve_targets(["-123"], self.mock_shell)
        assert pids == [-123]
    
    def test_empty_job_processes(self):
        """Test job with no processes."""
        mock_job = MagicMock()
        mock_job.processes = []
        self.mock_shell.job_manager.parse_job_spec.return_value = mock_job
        
        pids = self.kill._resolve_targets(["%1"], self.mock_shell)
        assert pids == []
    
    def test_case_insensitive_signal_names(self):
        """Test case insensitive signal name parsing."""
        assert self.kill._parse_signal("term") == signal.SIGTERM
        assert self.kill._parse_signal("Term") == signal.SIGTERM
        assert self.kill._parse_signal("TERM") == signal.SIGTERM
        assert self.kill._parse_signal("tErM") == signal.SIGTERM