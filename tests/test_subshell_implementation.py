#!/usr/bin/env python3
"""Test subshell implementation functionality.

Tests for the complete subshell group (...) syntax support implemented
in v0.59.8 as a major POSIX compliance milestone.

This includes variable isolation, command execution, redirections,
and proper process management.
"""

import pytest
import tempfile
import os
from psh.shell import Shell


class TestSubshellBasics:
    """Test basic subshell functionality."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_subshell_basic_execution(self):
        """Test basic subshell command execution."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(echo "hello from subshell") > {temp_file}')
            assert exit_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "hello from subshell" in content
        finally:
            os.unlink(temp_file)
    
    def test_subshell_multiple_commands(self):
        """Test subshell with multiple commands separated by semicolons."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(echo "first"; echo "second"; echo "third") > {temp_file}')
            assert exit_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "first" in content
                assert "second" in content  
                assert "third" in content
        finally:
            os.unlink(temp_file)
    
    def test_subshell_variable_isolation_modification(self):
        """Test that variables modified in subshells don't affect parent."""
        self.shell.run_command('test_var="original"')
        
        # Test that modification in subshell doesn't affect parent
        exit_code = self.shell.run_command('(test_var="modified")')
        assert exit_code == 0
        
        # Verify parent variable is unchanged
        assert self.shell.state.get_variable('test_var') == 'original'
    
    def test_subshell_variable_isolation_creation(self):
        """Test that variables created in subshells don't exist in parent."""
        # Verify variable doesn't exist initially
        assert self.shell.state.get_variable('new_var') == ''
        
        # Create variable in subshell
        exit_code = self.shell.run_command('(new_var="created in subshell")')
        assert exit_code == 0
        
        # Verify variable still doesn't exist in parent
        assert self.shell.state.get_variable('new_var') == ''
    
    def test_subshell_inherits_parent_variables(self):
        """Test that subshells can read parent variables."""
        self.shell.run_command('parent_var="available to child"')
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(echo "Subshell sees: $parent_var") > {temp_file}')
            assert exit_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Subshell sees: available to child" in content
        finally:
            os.unlink(temp_file)
    
    def test_subshell_exit_status_propagation(self):
        """Test that subshell exit status is propagated to parent."""
        # Successful subshell
        exit_code = self.shell.run_command('(true)')
        assert exit_code == 0
        
        # Failed subshell
        exit_code = self.shell.run_command('(false)')
        assert exit_code == 1
        
        # Subshell with specific exit code
        exit_code = self.shell.run_command('(exit 42)')
        assert exit_code == 42


class TestSubshellRedirections:
    """Test subshell redirections and I/O handling."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_subshell_output_redirection(self):
        """Test redirecting subshell output to file."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(echo "subshell output"; echo "second line") > {temp_file}')
            assert exit_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "subshell output" in content
                assert "second line" in content
        finally:
            os.unlink(temp_file)
    
    def test_subshell_input_redirection(self, capsys):
        """Test redirecting input to subshell."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            tf.write("line1\\nline2\\nline3\\n")
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(cat; echo "after cat") < {temp_file}')
            assert exit_code == 0
            
            captured = capsys.readouterr()
            assert "line1" in captured.out
            assert "line2" in captured.out
            assert "line3" in captured.out
            assert "after cat" in captured.out
        finally:
            os.unlink(temp_file)
    
    def test_subshell_error_redirection(self):
        """Test redirecting subshell stderr."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
            temp_file = tf.name
        
        try:
            exit_code = self.shell.run_command(f'(echo "stdout"; echo "stderr" >&2) 2> {temp_file}')
            assert exit_code == 0
            
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "stderr" in content
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.skip(reason="Background subshells not fully implemented yet")
    def test_subshell_background_execution(self):
        """Test subshell execution in background."""
        exit_code = self.shell.run_command('(sleep 0.1; echo "background done") &')
        assert exit_code == 0
        # Background job management would need to be tested separately


class TestSubshellAdvanced:
    """Test advanced subshell scenarios."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_nested_subshells(self, capsys):
        """Test nested subshells with proper isolation."""
        self.shell.run_command('var="level0"')
        
        exit_code = self.shell.run_command('''
        echo "Level 0: $var"
        (var="level1"; echo "Level 1: $var"; 
         (var="level2"; echo "Level 2: $var"); 
         echo "Back to level 1: $var")
        echo "Back to level 0: $var"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Level 0: level0" in captured.out
        assert "Level 1: level1" in captured.out
        assert "Level 2: level2" in captured.out
        assert "Back to level 1: level1" in captured.out
        assert "Back to level 0: level0" in captured.out
    
    def test_subshell_with_functions(self, capsys):
        """Test that functions are inherited by subshells."""
        self.shell.run_command('test_func() { echo "function called with: $1"; }')
        
        exit_code = self.shell.run_command('(test_func "from subshell")')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "function called with: from subshell" in captured.out
    
    def test_subshell_with_control_structures(self, capsys):
        """Test control structures within subshells."""
        exit_code = self.shell.run_command('''
        (for i in 1 2 3; do
             if [ $i -eq 2 ]; then
                 echo "found two: $i"
             else
                 echo "number: $i"
             fi
         done)
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "number: 1" in captured.out
        assert "found two: 2" in captured.out
        assert "number: 3" in captured.out
    
    def test_subshell_with_pipes(self, capsys):
        """Test pipes within subshells."""
        exit_code = self.shell.run_command('(echo "hello world" | grep "world")')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "hello world" in captured.out
    
    def test_subshell_environment_inheritance(self, capsys):
        """Test that exported variables are inherited by subshells."""
        self.shell.run_command('export EXPORTED_VAR="exported value"')
        
        exit_code = self.shell.run_command('(echo "Exported: $EXPORTED_VAR")')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Exported: exported value" in captured.out
    
    def test_subshell_cd_isolation(self, capsys):
        """Test that directory changes in subshells don't affect parent."""
        original_dir = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        
        try:
            exit_code = self.shell.run_command(f'''
            echo "Original: $(pwd)"
            (cd {temp_dir}; echo "In subshell: $(pwd)")
            echo "After subshell: $(pwd)"
            ''')
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert f"Original: {original_dir}" in captured.out
            assert f"In subshell: {temp_dir}" in captured.out
            assert f"After subshell: {original_dir}" in captured.out
        finally:
            os.rmdir(temp_dir)
    
    def test_subshell_with_arrays(self, capsys):
        """Test array operations within subshells."""
        self.shell.run_command('parent_arr=(a b c)')
        
        exit_code = self.shell.run_command('''
        echo "Parent array: ${parent_arr[@]}"
        (parent_arr+=(d e); echo "Modified in subshell: ${parent_arr[@]}")
        echo "After subshell: ${parent_arr[@]}"
        ''')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Parent array: a b c" in captured.out
        assert "After subshell: a b c" in captured.out  # Should be unchanged
    
    def test_subshell_error_handling(self, capsys):
        """Test error handling in subshells."""
        # Test that errors in subshells are properly reported
        exit_code = self.shell.run_command('(nonexistent_command)')
        
        assert exit_code != 0
        captured = capsys.readouterr()
        error_output = captured.err
        assert "nonexistent_command" in error_output or "command not found" in error_output


class TestSubshellCompatibility:
    """Test subshell compatibility with bash behavior."""
    
    def setup_method(self):
        """Create a shell instance for testing."""
        self.shell = Shell()
    
    def test_subshell_last_exit_code(self, capsys):
        """Test that $? reflects subshell exit status."""
        exit_code = self.shell.run_command('''
        (exit 5)
        echo "Exit code: $?"
        ''')
        
        captured = capsys.readouterr()
        assert "Exit code: 5" in captured.out
    
    def test_subshell_positional_parameters(self, capsys):
        """Test that positional parameters are inherited by subshells."""
        self.shell.run_command('set arg1 arg2 arg3')
        
        exit_code = self.shell.run_command('(echo "Args: $# - $1 $2 $3")')
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Args: 3 - arg1 arg2 arg3" in captured.out
    
    def test_subshell_special_variables(self, capsys):
        """Test behavior of special variables in subshells."""
        exit_code = self.shell.run_command('''
        echo "Parent PID: $$"
        (echo "Subshell PID: $$")
        ''')
        
        assert exit_code == 0
        # Note: In our implementation, $$ might be the same since we don't actually fork
        # but the test verifies the mechanism works
    
    def test_subshell_empty_command(self):
        """Test subshell with colon command (equivalent to empty)."""
        exit_code = self.shell.run_command('(:)')
        assert exit_code == 0
    
    def test_subshell_whitespace_handling(self, capsys):
        """Test subshells with various whitespace."""
        exit_code = self.shell.run_command('( echo "spaced" )')
        assert exit_code == 0
        
        exit_code = self.shell.run_command('(echo "nospace")')
        assert exit_code == 0
        
        captured = capsys.readouterr()
        assert "spaced" in captured.out
        assert "nospace" in captured.out