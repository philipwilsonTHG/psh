#!/usr/bin/env python3
"""
Test pipeline execution against bash for compatibility.
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os

# Add the tests/comparison directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bash_comparison_framework import bash_compare


class TestPipelines:
    """Test pipeline compatibility with bash."""
    
    def test_simple_pipeline(self):
        """Test simple two-command pipelines."""
        bash_compare.assert_shells_match("echo hello | cat")
        bash_compare.assert_shells_match("echo 'hello world' | cat")
        bash_compare.assert_shells_match("echo -e 'one\\ntwo\\nthree' | cat")
    
    def test_pipeline_word_count(self):
        """Test pipelines with word/line counting."""
        # Note: wc output format may vary, so we normalize
        bash_compare.assert_shells_match("echo 'one two three' | wc -w | tr -d ' '")
        bash_compare.assert_shells_match("printf 'a\\nb\\nc\\n' | wc -l | tr -d ' '")
    
    def test_pipeline_grep(self):
        """Test pipelines with grep."""
        bash_compare.assert_shells_match("echo -e 'apple\\nbanana\\napricot' | grep ^a")
        bash_compare.assert_shells_match("echo -e 'one\\ntwo\\nthree' | grep -v two")
    
    def test_pipeline_head_tail(self):
        """Test pipelines with head and tail."""
        bash_compare.assert_shells_match("echo -e '1\\n2\\n3\\n4\\n5' | head -3")
        bash_compare.assert_shells_match("echo -e '1\\n2\\n3\\n4\\n5' | tail -2")
    
    def test_multi_stage_pipeline(self):
        """Test pipelines with multiple stages."""
        bash_compare.assert_shells_match("echo -e 'apple\\nbanana\\napricot' | grep a | sort")
        bash_compare.assert_shells_match("echo -e '3\\n1\\n4\\n1\\n5' | sort | uniq")
    
    def test_pipeline_exit_status(self):
        """Test pipeline exit status propagation."""
        bash_compare.assert_shells_match("true | true | true; echo $?")
        bash_compare.assert_shells_match("true | false | true; echo $?")
        bash_compare.assert_shells_match("false | true | true; echo $?")
    
    def test_pipeline_with_builtins(self):
        """Test pipelines involving builtin commands."""
        bash_compare.assert_shells_match("echo hello | cat | cat")
        bash_compare.assert_shells_match("echo test | while read line; do echo \"Got: $line\"; done")
    
    @pytest.mark.xfail(reason="Variable scope in pipelines")

    
    def test_pipeline_with_variables(self):
        """Test pipelines with variable assignments."""
        bash_compare.assert_shells_match("x=hello; echo $x | cat")
        bash_compare.assert_shells_match("echo test | { read x; echo \"Read: $x\"; }")
    
    @pytest.mark.xfail(reason="Subshell variable isolation")

    
    def test_pipeline_subshell_isolation(self):
        """Test that pipeline commands run in subshells."""
        # Variables set in pipeline components don't affect parent
        bash_compare.assert_shells_match("x=1; echo test | { x=2; }; echo $x")
        bash_compare.assert_shells_match("x=1; true | x=2; echo $x")
    
    def test_empty_pipeline_components(self):
        """Test handling of empty pipeline components."""
        # These should be syntax errors in both shells
        bash_compare.expect_shells_differ("echo | ", 
            reason="Empty pipeline component", check_stderr=False)
        bash_compare.expect_shells_differ("| echo", 
            reason="Pipeline starting with |", check_stderr=False)
    
    def test_pipeline_with_redirections(self):
        """Test pipelines with I/O redirections."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content\n")
            temp_file = f.name
        
        try:
            # Redirect input to pipeline
            bash_compare.assert_shells_match(f"cat < {temp_file} | grep test")
            # Redirect output from pipeline
            bash_compare.assert_shells_match(f"echo hello | cat > /dev/null; echo done")
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.xfail(reason="Control structures in pipelines")

    
    def test_pipeline_control_structures(self):
        """Test control structures in pipelines."""
        bash_compare.assert_shells_match("echo -e '1\\n2\\n3' | while read n; do echo \"Number: $n\"; done")
        bash_compare.assert_shells_match("seq 1 3 | for n in $(cat); do echo \"Got $n\"; done")
        bash_compare.assert_shells_match("echo test | if grep -q test; then echo found; fi")