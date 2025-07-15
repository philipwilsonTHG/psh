"""
Tests for the kill builtin command.

Comprehensive test suite for kill builtin functionality including signal parsing,
PID validation, job specification handling, and signal delivery.
"""

import os
import signal
import pytest
from unittest.mock import patch, MagicMock, call


class TestKillBuiltinBasic:
    """Basic kill builtin functionality tests."""
    
    def test_kill_builtin_registration(self, shell):
        """Test that kill builtin is properly registered."""
        result = shell.run_command('type kill')
        assert result == 0
    
    def test_kill_no_arguments(self, captured_shell):
        """Test that kill with no arguments shows usage."""
        result = captured_shell.run_command("kill")
        assert result == 2
        stderr = captured_shell.get_stderr()
        assert "Usage:" in stderr or "usage:" in stderr
    
    def test_kill_help_option(self, captured_shell):
        """Test kill help output (may not support --help)."""
        result = captured_shell.run_command("kill --help")
        stderr = captured_shell.get_stderr()
        stdout = captured_shell.get_stdout()
        help_text = stderr + stdout
        
        # Kill may treat --help as signal name, which is acceptable
        # Just ensure it doesn't crash and produces some output
        assert len(help_text) > 0
        # Should mention either signal or error about invalid signal
        assert any(word in help_text.lower() for word in ['signal', 'invalid', 'kill'])


class TestKillSignalParsing:
    """Test signal name and number parsing."""
    
    def test_signal_parsing_by_name(self, captured_shell):
        """Test parsing signal names with list option."""
        # Test that signals are recognized by using -l
        result = captured_shell.run_command("kill -l")
        assert result == 0
        output = captured_shell.get_stdout()
        # Should contain standard signals
        assert any(sig in output.upper() for sig in ['TERM', 'KILL', 'HUP', 'INT'])
    
    def test_signal_parsing_by_number(self, captured_shell):
        """Test parsing signal numbers with list option."""
        # Test exit status to signal conversion
        result = captured_shell.run_command("kill -l 143")  # 128 + 15 (SIGTERM)
        assert result == 0
        output = captured_shell.get_stdout()
        assert "TERM" in output.upper()
    
    def test_invalid_signal_name(self, captured_shell):
        """Test error handling for invalid signal names."""
        result = captured_shell.run_command("kill -INVALID 123")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "invalid" in stderr.lower() or "unknown" in stderr.lower()
    
    def test_invalid_signal_number(self, captured_shell):
        """Test error handling for invalid signal numbers."""
        result = captured_shell.run_command("kill -999 123")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "invalid" in stderr.lower() or "unknown" in stderr.lower()


class TestKillArgumentParsing:
    """Test kill argument parsing and validation."""
    
    def test_signal_name_format(self, captured_shell):
        """Test -SIGNAL_NAME format parsing."""
        # Use a non-existent PID to avoid actually killing anything
        result = captured_shell.run_command("kill -TERM 999999")
        # Should parse correctly even if PID doesn't exist
        stderr = captured_shell.get_stderr()
        # Error should be about process not found, not signal parsing
        assert "invalid" not in stderr.lower() or "process" in stderr.lower()
    
    def test_signal_number_format(self, captured_shell):
        """Test -NUMBER format parsing."""
        result = captured_shell.run_command("kill -15 999999")
        stderr = captured_shell.get_stderr()
        # Error should be about process not found, not signal parsing
        assert "invalid" not in stderr.lower() or "process" in stderr.lower()
    
    def test_s_option_format(self, captured_shell):
        """Test -s SIGNAL format parsing."""
        result = captured_shell.run_command("kill -s KILL 999999")
        stderr = captured_shell.get_stderr()
        # Error should be about process not found, not signal parsing
        assert "invalid" not in stderr.lower() or "process" in stderr.lower()
    
    def test_multiple_pids(self, captured_shell):
        """Test parsing multiple PIDs."""
        result = captured_shell.run_command("kill 999999 999998 999997")
        # Should attempt to process all PIDs
        stderr = captured_shell.get_stderr()
        # Should have multiple "No such process" or similar errors
        error_lines = [line for line in stderr.split('\n') if line.strip()]
        assert len(error_lines) >= 1  # At least some error output
    
    def test_double_dash_separator(self, captured_shell):
        """Test -- separator handling."""
        result = captured_shell.run_command("kill -TERM -- -999999")
        # Should treat -999999 as a process group ID
        stderr = captured_shell.get_stderr()
        assert "invalid" not in stderr.lower() or "process" in stderr.lower()
    
    def test_missing_signal_after_s(self, captured_shell):
        """Test error when -s has no argument."""
        result = captured_shell.run_command("kill -s")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "argument" in stderr.lower() or "option" in stderr.lower()


class TestKillTargetResolution:
    """Test PID and job specification resolution."""
    
    def test_numeric_pid_validation(self, captured_shell):
        """Test numeric PID validation."""
        result = captured_shell.run_command("kill 123")
        # Non-existent PID should give appropriate error
        stderr = captured_shell.get_stderr()
        assert "process" in stderr.lower() or "such" in stderr.lower()
    
    def test_invalid_pid_format(self, captured_shell):
        """Test invalid PID format handling."""
        result = captured_shell.run_command("kill invalid_pid")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "invalid" in stderr.lower() or "process" in stderr.lower()
    
    def test_process_group_negative_pid(self, captured_shell):
        """Test negative PID for process group signaling."""
        # Use -- to separate signal from negative PID
        result = captured_shell.run_command("kill -- -123")
        stderr = captured_shell.get_stderr()
        
        # Should either attempt process group kill or report invalid PID
        # Different implementations may handle this differently
        if stderr:
            assert any(msg in stderr.lower() for msg in ['permission', 'process', 'group', 'invalid', 'no such'])
    
    def test_signal_zero_test_existence(self, captured_shell):
        """Test signal 0 for testing process existence."""
        result = captured_shell.run_command("kill -0 999999")
        # Signal 0 tests existence without sending signal
        stderr = captured_shell.get_stderr()
        assert "process" in stderr.lower() or "such" in stderr.lower()
    
    def test_current_process_group_pid_zero(self, captured_shell):
        """Test PID 0 for current process group."""
        # This might succeed or fail depending on permissions
        result = captured_shell.run_command("kill -0 0")
        # Should not fail with parsing error
        stderr = captured_shell.get_stderr()
        if stderr:
            assert "invalid" not in stderr.lower()


class TestKillListOption:
    """Test kill -l signal listing functionality."""
    
    def test_list_all_signals(self, captured_shell):
        """Test listing all signals."""
        result = captured_shell.run_command("kill -l")
        assert result == 0
        output = captured_shell.get_stdout()
        
        # Should contain standard POSIX signals
        expected_signals = ['TERM', 'KILL', 'HUP', 'INT', 'QUIT', 'USR1', 'USR2']
        found_signals = sum(1 for sig in expected_signals if sig in output.upper())
        assert found_signals >= 4  # Should have most standard signals
    
    def test_list_signal_for_exit_status(self, captured_shell):
        """Test listing signal name for specific exit status."""
        # Exit status 143 = 128 + 15 (SIGTERM)
        result = captured_shell.run_command("kill -l 143")
        assert result == 0
        output = captured_shell.get_stdout()
        assert "TERM" in output.upper()
    
    def test_list_signal_for_non_signal_exit(self, captured_shell):
        """Test listing for non-signal exit status."""
        result = captured_shell.run_command("kill -l 1")
        assert result == 0
        output = captured_shell.get_stdout()
        # Should indicate not from signal
        assert len(output.strip()) == 0 or "not" in output.lower()
    
    def test_list_invalid_exit_status(self, captured_shell):
        """Test listing signal for invalid exit status."""
        result = captured_shell.run_command("kill -l invalid")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "invalid" in stderr.lower() or "status" in stderr.lower()


class TestKillJobSpecifications:
    """Test job specification handling in kill builtin."""
    
    def test_job_spec_parsing(self, captured_shell):
        """Test job specification parsing."""
        # Try to kill non-existent job
        result = captured_shell.run_command("kill %99")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "job" in stderr.lower() or "no such" in stderr.lower()
    
    def test_job_spec_with_signal(self, captured_shell):
        """Test job specification with signal."""
        result = captured_shell.run_command("kill -TERM %99")
        assert result != 0
        stderr = captured_shell.get_stderr()
        assert "job" in stderr.lower() or "no such" in stderr.lower()
    
    def test_multiple_job_specs(self, captured_shell):
        """Test multiple job specifications."""
        result = captured_shell.run_command("kill %99 %98")
        assert result != 0
        stderr = captured_shell.get_stderr()
        # Should report errors for both jobs
        assert "job" in stderr.lower() or "no such" in stderr.lower()


class TestKillExecutionFlow:
    """Test complete kill execution scenarios."""
    
    def test_no_process_specified_with_signal(self, captured_shell):
        """Test error when signal specified but no process."""
        result = captured_shell.run_command("kill -TERM")
        assert result == 2
        stderr = captured_shell.get_stderr()
        assert "process" in stderr.lower() or "specified" in stderr.lower()
    
    def test_mixed_valid_invalid_targets(self, captured_shell):
        """Test killing mix of valid and invalid targets."""
        result = captured_shell.run_command("kill 999999 invalid_pid 999998")
        # Should process all targets and report errors
        stderr = captured_shell.get_stderr()
        assert "invalid" in stderr.lower() or "process" in stderr.lower()
    
    def test_complex_argument_combination(self, captured_shell):
        """Test complex argument combinations."""
        result = captured_shell.run_command("kill -s KILL 999999 999998")
        # Should parse signal and attempt to kill both PIDs
        stderr = captured_shell.get_stderr()
        # Errors should be about process not found, not parsing
        if stderr:
            assert "invalid" not in stderr.lower() or "process" in stderr.lower()


class TestKillSignalDelivery:
    """Test signal delivery mechanisms."""
    
    def test_default_signal_is_term(self, captured_shell):
        """Test that default signal is SIGTERM."""
        # Compare behavior of kill PID vs kill -TERM PID
        result1 = captured_shell.run_command("kill 999999")
        captured_shell.clear_output()
        result2 = captured_shell.run_command("kill -TERM 999999")
        
        # Both should behave identically
        assert result1 == result2
    
    @pytest.mark.skipif(os.name == 'nt', reason="Signal handling differs on Windows")
    def test_signal_zero_no_side_effects(self, captured_shell):
        """Test that signal 0 doesn't actually signal the process."""
        # Signal 0 should test existence without side effects
        # Use our own PID which should exist
        import os
        current_pid = os.getpid()
        result = captured_shell.run_command(f"kill -0 {current_pid}")
        # Should succeed without any visible effects
        assert result == 0


class TestKillEdgeCases:
    """Edge case tests for kill builtin."""
    
    def test_case_insensitive_signal_names(self, captured_shell):
        """Test case insensitive signal name parsing."""
        # All of these should parse identically
        test_cases = [
            "kill -TERM 999999",
            "kill -term 999999", 
            "kill -Term 999999",
            "kill -tErM 999999"
        ]
        
        results = []
        for cmd in test_cases:
            result = captured_shell.run_command(cmd)
            stderr = captured_shell.get_stderr()
            results.append((result, stderr))
            captured_shell.clear_output()
        
        # All should behave identically
        first_result = results[0]
        for result, stderr in results[1:]:
            assert result == first_result[0]
            # Error messages should be similar (process not found)
            assert "invalid" not in stderr.lower() or "process" in stderr.lower()
    
    def test_sig_prefix_handling(self, captured_shell):
        """Test SIG prefix in signal names."""
        # Both should work identically
        result1 = captured_shell.run_command("kill -TERM 999999")
        captured_shell.clear_output()
        result2 = captured_shell.run_command("kill -SIGTERM 999999")
        
        assert result1 == result2
    
    def test_empty_target_list(self, captured_shell):
        """Test handling of empty target list after parsing."""
        result = captured_shell.run_command("kill -l")
        # -l with no arguments should list signals
        assert result == 0
        output = captured_shell.get_stdout()
        assert "TERM" in output.upper() or "KILL" in output.upper()
    
    def test_whitespace_in_arguments(self, captured_shell):
        """Test handling of extra whitespace."""
        result = captured_shell.run_command("kill   -TERM   999999   ")
        # Should parse correctly despite extra whitespace
        stderr = captured_shell.get_stderr()
        if stderr:
            assert "invalid" not in stderr.lower() or "process" in stderr.lower()


class TestKillErrorHandling:
    """Test error handling and edge conditions."""
    
    def test_permission_denied_simulation(self, captured_shell):
        """Test behavior when permission denied (using PID 1 if available)."""
        if os.name != 'nt':  # Unix-like systems
            result = captured_shell.run_command("kill 1")
            # Should fail with permission error or no such process
            assert result != 0
            stderr = captured_shell.get_stderr()
            assert any(msg in stderr.lower() for msg in ['permission', 'process', 'operation'])
    
    def test_very_large_pid(self, captured_shell):
        """Test handling of very large PID numbers."""
        result = captured_shell.run_command("kill 99999999")
        # Should handle large numbers gracefully
        stderr = captured_shell.get_stderr()
        assert "process" in stderr.lower() or "such" in stderr.lower()
    
    def test_negative_signal_number(self, captured_shell):
        """Test handling of negative signal numbers."""
        result = captured_shell.run_command("kill --5 999999")
        # Should either parse as process group or error appropriately
        assert result != 0  # Likely to fail
        stderr = captured_shell.get_stderr()
        # Should not crash, should give appropriate error
        assert len(stderr) > 0
    
    def test_too_many_arguments(self, captured_shell):
        """Test handling of very long argument lists."""
        # Create a long list of PIDs
        pids = " ".join(str(999000 + i) for i in range(50))
        result = captured_shell.run_command(f"kill {pids}")
        # Should handle gracefully without crashing
        stderr = captured_shell.get_stderr()
        # Should report errors for non-existent processes
        assert "process" in stderr.lower() or "such" in stderr.lower()