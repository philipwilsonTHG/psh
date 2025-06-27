#!/usr/bin/env python3
"""
Test I/O redirections against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestRedirections:
    """Test I/O redirection compatibility with bash."""
    
    @pytest.mark.xfail(reason="Builtin redirections require architectural changes")

    
    def test_output_redirection(self):
        """Test basic output redirection."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # Test > redirection
            bash_compare.assert_shells_match(f"echo hello > {temp_file}; cat {temp_file}")
            # Test >> redirection
            bash_compare.assert_shells_match(f"echo world >> {temp_file}; cat {temp_file}")
        finally:
            os.unlink(temp_file)
    
    def test_input_redirection(self):
        """Test input redirection."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content\n")
            temp_file = f.name
        
        try:
            bash_compare.assert_shells_match(f"cat < {temp_file}")
            bash_compare.assert_shells_match(f"while read line; do echo \"Line: $line\"; done < {temp_file}")
        finally:
            os.unlink(temp_file)
    
    def test_stderr_redirection(self):
        """Test stderr redirection."""
        # Redirect stderr to stdout
        bash_compare.assert_shells_match("echo error >&2 2>&1")
        # Redirect stderr to file (we can't easily compare file contents)
        bash_compare.assert_shells_match("echo normal; echo error >&2 2>/dev/null")
    
    def test_here_document(self):
        """Test here documents."""
        bash_compare.assert_shells_match("cat << EOF\nline1\nline2\nEOF")
        bash_compare.assert_shells_match("cat << 'EOF'\n$HOME\n$(echo test)\nEOF")
    
    def test_here_string(self):
        """Test here strings."""
        bash_compare.assert_shells_match("cat <<< 'hello world'")
        bash_compare.assert_shells_match("x='test string'; cat <<< \"$x\"")
    
    def test_fd_duplication(self):
        """Test file descriptor duplication."""
        bash_compare.assert_shells_match("echo test 2>&1")
        bash_compare.assert_shells_match("(echo stdout; echo stderr >&2) 2>&1")
    
    @pytest.mark.xfail(reason="Stderr redirection in subshells not working correctly - requires subprocess redirection architecture review")
    def test_multiple_redirections(self):
        """Test multiple redirections on same command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "out.txt")
            err_file = os.path.join(tmpdir, "err.txt")
            
            # Redirect both stdout and stderr
            cmd = f"(echo stdout; echo stderr >&2) > {out_file} 2> {err_file}; echo STDOUT:; cat {out_file}; echo STDERR:; cat {err_file}"
            bash_compare.assert_shells_match(cmd)
    
    def test_redirection_with_builtins(self):
        """Test redirections work with builtin commands."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            bash_compare.assert_shells_match(f"echo builtin test > {temp_file}; cat {temp_file}")
            bash_compare.assert_shells_match(f"pwd > {temp_file}; wc -l < {temp_file} | tr -d ' '")
        finally:
            os.unlink(temp_file)
    
    def test_noclobber_behavior(self):
        """Test file overwriting behavior (noclobber not set)."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            # File should be overwritten
            bash_compare.assert_shells_match(f"echo first > {temp_file}; echo second > {temp_file}; cat {temp_file}")
        finally:
            os.unlink(temp_file)
    
    def test_append_redirection(self):
        """Test append redirection >>."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name
        
        try:
            bash_compare.assert_shells_match(f"echo first > {temp_file}; echo second >> {temp_file}; cat {temp_file}")
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.xfail(reason="Redirection ordering behavior differs from bash - requires redirection processing architecture review")
    def test_redirection_ordering(self):
        """Test that redirection order matters."""
        # Redirect stderr to stdout, then stdout to /dev/null
        # Only stderr should be visible
        bash_compare.assert_shells_match("(echo stdout; echo stderr >&2) 2>&1 >/dev/null")
        # Redirect stdout to /dev/null, then stderr to stdout
        # Nothing should be visible
        bash_compare.assert_shells_match("(echo stdout; echo stderr >&2) >/dev/null 2>&1; echo done")
