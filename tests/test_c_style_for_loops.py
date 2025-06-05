"""Tests for C-style for loops: for ((init; condition; update))"""
import unittest
import subprocess
import sys
import os

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestCStyleForLoops(unittest.TestCase):
    """Test C-style for loop functionality."""
    
    def run_psh_command(self, cmd):
        """Helper to run psh command and capture output."""
        result = subprocess.run(
            ["python3", "-m", "psh", "-c", cmd],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_basic_counter(self):
        """Test basic C-style for loop with counter."""
        stdout, stderr, rc = self.run_psh_command('for ((i=0; i<5; i++)); do echo $i; done')
        self.assertEqual(stdout, "0\n1\n2\n3\n4\n")
        self.assertEqual(rc, 0)
    
    def test_increment_by_two(self):
        """Test C-style for loop with increment by 2."""
        stdout, stderr, rc = self.run_psh_command('for ((i=0; i<10; i+=2)); do echo $i; done')
        self.assertEqual(stdout, "0\n2\n4\n6\n8\n")
        self.assertEqual(rc, 0)
    
    def test_decrement(self):
        """Test C-style for loop with decrement."""
        stdout, stderr, rc = self.run_psh_command('for ((i=5; i>0; i--)); do echo $i; done')
        self.assertEqual(stdout, "5\n4\n3\n2\n1\n")
        self.assertEqual(rc, 0)
    
    def test_multiplication_update(self):
        """Test C-style for loop with multiplication in update."""
        stdout, stderr, rc = self.run_psh_command('for ((i=1; i<=100; i*=2)); do echo $i; done')
        self.assertEqual(stdout, "1\n2\n4\n8\n16\n32\n64\n")
        self.assertEqual(rc, 0)
    
    def test_empty_init(self):
        """Test C-style for loop with empty initialization."""
        stdout, stderr, rc = self.run_psh_command('i=0; for ((; i<3; i++)); do echo $i; done')
        self.assertEqual(stdout, "0\n1\n2\n")
        self.assertEqual(rc, 0)
    
    def test_empty_condition(self):
        """Test C-style for loop with empty condition (infinite loop with break)."""
        cmd = '''
for ((i=0; ; i++)); do 
    echo $i
    if ((i >= 3)); then break; fi
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0\n1\n2\n3\n")
        self.assertEqual(rc, 0)
    
    def test_empty_update(self):
        """Test C-style for loop with empty update."""
        cmd = '''
for ((i=0; i<3; )); do 
    echo $i
    ((i++))
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0\n1\n2\n")
        self.assertEqual(rc, 0)
    
    def test_all_empty(self):
        """Test C-style for loop with all sections empty."""
        cmd = '''
i=0
for ((;;)); do 
    echo $i
    ((i++))
    if ((i >= 3)); then break; fi
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0\n1\n2\n")
        self.assertEqual(rc, 0)
    
    def test_multiple_variables(self):
        """Test C-style for loop with multiple variables."""
        stdout, stderr, rc = self.run_psh_command(
            'for ((i=0, j=10; i<5; i++, j--)); do echo "$i $j"; done'
        )
        self.assertEqual(stdout, "0 10\n1 9\n2 8\n3 7\n4 6\n")
        self.assertEqual(rc, 0)
    
    def test_with_existing_variable(self):
        """Test C-style for loop using existing variables."""
        cmd = '''
start=5
end=8
for ((i=start; i<=end; i++)); do 
    echo $i
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "5\n6\n7\n8\n")
        self.assertEqual(rc, 0)
    
    def test_nested_c_style_for(self):
        """Test nested C-style for loops."""
        cmd = '''
for ((i=0; i<3; i++)); do 
    for ((j=0; j<2; j++)); do 
        echo "$i,$j"
    done
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0,0\n0,1\n1,0\n1,1\n2,0\n2,1\n")
        self.assertEqual(rc, 0)
    
    def test_break_in_c_style_for(self):
        """Test break statement in C-style for loop."""
        cmd = '''
for ((i=0; i<10; i++)); do 
    if ((i == 5)); then break; fi
    echo $i
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0\n1\n2\n3\n4\n")
        self.assertEqual(rc, 0)
    
    def test_continue_in_c_style_for(self):
        """Test continue statement in C-style for loop."""
        cmd = '''
for ((i=0; i<5; i++)); do 
    if ((i == 2)); then continue; fi
    echo $i
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "0\n1\n3\n4\n")
        self.assertEqual(rc, 0)
    
    def test_c_style_with_redirection(self):
        """Test C-style for loop with I/O redirection."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            tmpfile = f.name
        
        try:
            cmd = f'for ((i=0; i<3; i++)); do echo $i; done > {tmpfile}'
            stdout, stderr, rc = self.run_psh_command(cmd)
            self.assertEqual(rc, 0)
            
            # Read the file
            stdout, stderr, rc = self.run_psh_command(f'cat {tmpfile}')
            self.assertEqual(stdout, "0\n1\n2\n")
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
    
    def test_c_style_in_function(self):
        """Test C-style for loop inside a function."""
        cmd = '''
count_to() {
    local n=$1
    for ((i=1; i<=n; i++)); do
        echo $i
    done
}
count_to 3
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "1\n2\n3\n")
        self.assertEqual(rc, 0)
    
    def test_c_style_with_arithmetic_expressions(self):
        """Test C-style for loop with complex arithmetic expressions."""
        cmd = '''
x=2
for ((i=x*2; i<x*5; i+=x)); do
    echo $i
done
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "4\n6\n8\n")
        self.assertEqual(rc, 0)
    
    def test_variable_preservation(self):
        """Test that loop variable is preserved after loop."""
        cmd = '''
for ((i=0; i<3; i++)); do
    :
done
echo $i
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        self.assertEqual(stdout, "3\n")
        self.assertEqual(rc, 0)
    
    def test_c_style_without_do(self):
        """Test C-style for loop without optional 'do' keyword."""
        stdout, stderr, rc = self.run_psh_command('for ((i=0; i<3; i++)) echo $i; done')
        self.assertEqual(stdout, "0\n1\n2\n")
        self.assertEqual(rc, 0)
    
    def test_comparison_operators(self):
        """Test various comparison operators in condition."""
        # Less than or equal
        stdout, stderr, rc = self.run_psh_command('for ((i=1; i<=3; i++)); do echo $i; done')
        self.assertEqual(stdout, "1\n2\n3\n")
        
        # Greater than
        stdout, stderr, rc = self.run_psh_command('for ((i=3; i>0; i--)); do echo $i; done')
        self.assertEqual(stdout, "3\n2\n1\n")
        
        # Not equal
        stdout, stderr, rc = self.run_psh_command('for ((i=0; i!=3; i++)); do echo $i; done')
        self.assertEqual(stdout, "0\n1\n2\n")


class TestCStyleForEdgeCases(unittest.TestCase):
    """Test edge cases and error handling for C-style for loops."""
    
    def run_psh_command(self, cmd):
        """Helper to run psh command and capture output."""
        result = subprocess.run(
            ["python3", "-m", "psh", "-c", cmd],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_syntax_error_missing_paren(self):
        """Test syntax error when closing parenthesis is missing."""
        stdout, stderr, rc = self.run_psh_command('for ((i=0; i<5; i++); do echo $i; done')
        self.assertNotEqual(rc, 0)
        self.assertTrue("Expected" in stderr or "Parse error" in stderr)
    
    def test_division_by_zero(self):
        """Test arithmetic error handling in condition."""
        cmd = '''
for ((i=0; i<5/0; i++)); do 
    echo "should not print"
done
echo "after loop"
'''
        stdout, stderr, rc = self.run_psh_command(cmd)
        # The loop should exit with an error when evaluating 5/0
        self.assertIn("after loop", stdout)


if __name__ == "__main__":
    unittest.main()