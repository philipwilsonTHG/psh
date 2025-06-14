#!/usr/bin/env python3
"""Test for regression in command substitution within variable expansion."""

import unittest
import sys
import os
import pytest

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell


class TestExpansionRegression(unittest.TestCase):
    """Test that command substitution works in variable expansion contexts."""
    
    def setUp(self):
        self.shell = Shell()
    
    def test_command_substitution_in_string_expansion(self):
        """Test that command substitution works inside double-quoted strings."""
        # This was the bug: _execute_command_substitution method not found
        exit_code = self.shell.run_command('VAR="$(echo test)"; echo "$VAR"')
        self.assertEqual(exit_code, 0)
        
        # Test in variable assignment
        self.shell.run_command('MSG="Current directory: $(pwd)"')
        self.assertEqual(self.shell.variables.get('MSG', '').startswith('Current directory:'), True)
    
    @pytest.mark.visitor_xfail(reason="Output capture doesn't work with forked processes")
    def test_command_substitution_in_for_loop(self):
        """Test the original failing case: command substitution in for loop."""
        # Create test files
        import tempfile
        import shutil
        
        tmpdir = tempfile.mkdtemp()
        try:
            # Create test files
            with open(os.path.join(tmpdir, 'file1.py'), 'w') as f:
                f.write('print("test")\n')
            with open(os.path.join(tmpdir, 'file2.txt'), 'w') as f:
                f.write('not python\n')
            
            # The original failing command
            cmd = f'''
            count=0
            for file in $(find {tmpdir} -type f -print | sort)
            do
                if [[ $file =~ "py$" ]]
                then
                    count=$((count + 1))
                fi
            done
            echo $count
            '''
            
            # Capture output
            saved_stdout = sys.stdout
            from io import StringIO
            sys.stdout = StringIO()
            
            try:
                exit_code = self.shell.run_command(cmd)
                output = sys.stdout.getvalue().strip()
            finally:
                sys.stdout = saved_stdout
            
            self.assertEqual(exit_code, 0)
            self.assertEqual(output, "1")  # Should find 1 .py file
            
        finally:
            shutil.rmtree(tmpdir)
    
    @pytest.mark.visitor_xfail(reason="Output capture doesn't work with forked processes")
    def test_dollar_paren_substitution_in_string(self):
        """Test $() command substitution in strings - the actual bug fix."""
        # This tests the actual bug that was fixed
        saved_stdout = sys.stdout
        from io import StringIO
        sys.stdout = StringIO()
        
        try:
            exit_code = self.shell.run_command('echo "$(echo works)"')
            output = sys.stdout.getvalue().strip()
        finally:
            sys.stdout = saved_stdout
        
        self.assertEqual(exit_code, 0)
        self.assertEqual(output, 'works')
    
    @pytest.mark.visitor_xfail(reason="Output capture doesn't work with forked processes")
    def test_multiple_substitutions(self):
        """Test multiple command substitutions in one string."""
        saved_stdout = sys.stdout
        from io import StringIO
        sys.stdout = StringIO()
        
        try:
            exit_code = self.shell.run_command('echo "First: $(echo one), Second: $(echo two)"')
            output = sys.stdout.getvalue().strip()
        finally:
            sys.stdout = saved_stdout
        
        self.assertEqual(exit_code, 0)
        self.assertEqual(output, 'First: one, Second: two')


if __name__ == '__main__':
    unittest.main()