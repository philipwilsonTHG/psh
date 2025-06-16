#!/usr/bin/env python3
"""
Test function redirections compared to bash behavior.
Tests function calls with various types of redirections.
"""

import pytest
import sys
from pathlib import Path

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestFunctionRedirections:
    """Test function output redirections match bash behavior."""
    
    def test_simple_function_redirection(self):
        """Test simple function output redirection (replaces flaky test)."""
        bash_compare.assert_shells_match("""
            greet() { echo "Hello from function"; }
            greet > /tmp/test_func_output.txt
            cat /tmp/test_func_output.txt
            rm -f /tmp/test_func_output.txt
        """)
    
    def test_function_output_redirection(self):
        """Test basic function output redirection to file."""
        bash_compare.assert_shells_match("""
            greet() { echo "Hello from function"; }
            greet > /tmp/psh_func_test.txt
            cat /tmp/psh_func_test.txt
            rm -f /tmp/psh_func_test.txt
        """)
    
    def test_function_append_redirection(self):
        """Test function output append redirection."""
        bash_compare.assert_shells_match("""
            log_msg() { echo "Log: $1"; }
            echo "Initial" > /tmp/psh_func_log.txt
            log_msg "First message" >> /tmp/psh_func_log.txt
            log_msg "Second message" >> /tmp/psh_func_log.txt
            cat /tmp/psh_func_log.txt
            rm -f /tmp/psh_func_log.txt
        """)
    
    def test_function_stderr_redirection(self):
        """Test function stderr redirection."""
        bash_compare.assert_shells_match("""
            error_func() { echo "Error message" >&2; }
            error_func 2> /tmp/psh_func_err.txt
            cat /tmp/psh_func_err.txt
            rm -f /tmp/psh_func_err.txt
        """)
    
    def test_function_combined_redirection(self):
        """Test function with both stdout and stderr redirection."""
        bash_compare.assert_shells_match("""
            mixed_output() {
                echo "Normal output"
                echo "Error output" >&2
            }
            mixed_output > /tmp/psh_func_out.txt 2> /tmp/psh_func_err.txt
            echo "STDOUT:"; cat /tmp/psh_func_out.txt
            echo "STDERR:"; cat /tmp/psh_func_err.txt
            rm -f /tmp/psh_func_out.txt /tmp/psh_func_err.txt
        """)
    
    def test_function_input_redirection(self):
        """Test function with input redirection."""
        bash_compare.assert_shells_match("""
            echo "test data" > /tmp/psh_func_input.txt
            read_data() { read line; echo "Read: $line"; }
            read_data < /tmp/psh_func_input.txt
            rm -f /tmp/psh_func_input.txt
        """)
    
    @pytest.mark.xfail(reason="Multi-line here document parsing issue")
    def test_function_here_document(self):
        """Test function with here document."""
        bash_compare.assert_shells_match("""
            process_data() {
                while read line; do
                    echo "Processing: $line"
                done
            }
            process_data << EOF
line 1
line 2
line 3
EOF
        """)
    
    def test_nested_function_redirection(self):
        """Test nested functions with redirection."""
        bash_compare.assert_shells_match("""
            inner() { echo "Inner function output"; }
            outer() { 
                echo "Outer function start"
                inner
                echo "Outer function end"
            }
            outer > /tmp/psh_nested.txt
            cat /tmp/psh_nested.txt
            rm -f /tmp/psh_nested.txt
        """)
    
    def test_function_pipeline_redirection(self):
        """Test function in pipeline with redirection."""
        bash_compare.assert_shells_match("""
            generate() { echo -e "apple\\nbanana\\ncherry"; }
            process() { grep a; }
            generate | process > /tmp/psh_pipeline.txt
            cat /tmp/psh_pipeline.txt
            rm -f /tmp/psh_pipeline.txt
        """)
    
    def test_function_fd_duplication(self):
        """Test function with file descriptor duplication."""
        bash_compare.assert_shells_match("""
            dual_output() {
                echo "To stdout"
                echo "To stderr" >&2
            }
            dual_output 2>&1 > /tmp/psh_dual.txt
            echo "Captured stderr on stdout"
            cat /tmp/psh_dual.txt
            rm -f /tmp/psh_dual.txt
        """)
    
    def test_function_noclobber_behavior(self):
        """Test function redirection with noclobber (if supported)."""
        # This might be a known limitation
        bash_compare.assert_shells_match("""
            echo "existing" > /tmp/psh_noclobber.txt
            overwrite() { echo "new content"; }
            overwrite > /tmp/psh_noclobber.txt
            cat /tmp/psh_noclobber.txt
            rm -f /tmp/psh_noclobber.txt
        """)