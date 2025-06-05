"""Tests for arithmetic command syntax ((expression))"""
import unittest
import subprocess
import sys
import os

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestArithmeticCommand(unittest.TestCase):
    """Test arithmetic command functionality."""
    
    def run_psh_command(self, cmd):
        """Helper to run psh command and capture output."""
        result = subprocess.run(
            ["python3", "-m", "psh", "-c", cmd],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return result.stdout, result.stderr, result.returncode
    
    def test_basic_evaluation(self):
        """Test basic arithmetic command evaluation."""
        # Non-zero result should return 0
        stdout, stderr, rc = self.run_psh_command('((5 > 3)); echo $?')
        self.assertEqual(stdout, "0\n")
        self.assertEqual(rc, 0)
        
        # Zero result should return 1
        stdout, stderr, rc = self.run_psh_command('((0)); echo $?')
        self.assertEqual(stdout, "1\n")
        self.assertEqual(rc, 0)
    
    def test_variable_assignment(self):
        """Test variable assignments in arithmetic."""
        stdout, stderr, rc = self.run_psh_command('((x = 5)); echo $x')
        self.assertEqual(stdout, "5\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('((x = 2 * 3)); echo $x')
        self.assertEqual(stdout, "6\n")
        self.assertEqual(rc, 0)
    
    def test_compound_assignments(self):
        """Test +=, -=, etc."""
        stdout, stderr, rc = self.run_psh_command('x=5; ((x += 3)); echo $x')
        self.assertEqual(stdout, "8\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('x=10; ((x -= 3)); echo $x')
        self.assertEqual(stdout, "7\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('x=4; ((x *= 2)); echo $x')
        self.assertEqual(stdout, "8\n")
        self.assertEqual(rc, 0)
    
    def test_increment_decrement(self):
        """Test increment and decrement operators."""
        # Post-increment
        stdout, stderr, rc = self.run_psh_command('x=5; ((x++)); echo $x')
        self.assertEqual(stdout, "6\n")
        self.assertEqual(rc, 0)
        
        # Pre-increment
        stdout, stderr, rc = self.run_psh_command('x=5; ((++x)); echo $x')
        self.assertEqual(stdout, "6\n")
        self.assertEqual(rc, 0)
        
        # Post-decrement
        stdout, stderr, rc = self.run_psh_command('x=5; ((x--)); echo $x')
        self.assertEqual(stdout, "4\n")
        self.assertEqual(rc, 0)
        
        # Pre-decrement
        stdout, stderr, rc = self.run_psh_command('x=5; ((--x)); echo $x')
        self.assertEqual(stdout, "4\n")
        self.assertEqual(rc, 0)
    
    def test_in_conditionals(self):
        """Test in if/while conditions."""
        # In if statement
        stdout, stderr, rc = self.run_psh_command('x=10; if ((x > 5)); then echo "big"; fi')
        self.assertEqual(stdout, "big\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('x=2; if ((x > 5)); then echo "big"; else echo "small"; fi')
        self.assertEqual(stdout, "small\n")
        self.assertEqual(rc, 0)
        
        # In while loop
        stdout, stderr, rc = self.run_psh_command('i=0; while ((i < 3)); do echo $i; ((i++)); done')
        self.assertEqual(stdout, "0\n1\n2\n")
        self.assertEqual(rc, 0)
    
    def test_multiple_expressions(self):
        """Test comma operator."""
        stdout, stderr, rc = self.run_psh_command('((a=1, b=2, c=a+b)); echo "$a $b $c"')
        self.assertEqual(stdout, "1 2 3\n")
        self.assertEqual(rc, 0)
    
    def test_comparison_operators(self):
        """Test various comparison operators."""
        # Less than
        stdout, stderr, rc = self.run_psh_command('if ((3 < 5)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
        
        # Greater than  
        stdout, stderr, rc = self.run_psh_command('if ((5 > 3)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
        
        # Equal
        stdout, stderr, rc = self.run_psh_command('if ((5 == 5)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
        
        # Not equal
        stdout, stderr, rc = self.run_psh_command('if ((5 != 3)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
    
    def test_logical_operators(self):
        """Test && and || operators."""
        stdout, stderr, rc = self.run_psh_command('if ((5 > 3 && 2 < 4)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('if ((5 < 3 || 2 < 4)); then echo "true"; fi')
        self.assertEqual(stdout, "true\n")
        self.assertEqual(rc, 0)
    
    def test_ternary_operator(self):
        """Test ternary operator."""
        stdout, stderr, rc = self.run_psh_command('((x = 5 > 3 ? 10 : 20)); echo $x')
        self.assertEqual(stdout, "10\n")
        self.assertEqual(rc, 0)
        
        stdout, stderr, rc = self.run_psh_command('((x = 2 > 3 ? 10 : 20)); echo $x')
        self.assertEqual(stdout, "20\n")
        self.assertEqual(rc, 0)
    
    def test_error_handling(self):
        """Test error cases."""
        # Division by zero
        stdout, stderr, rc = self.run_psh_command('((5 / 0)); echo "should not print"')
        self.assertIn("Division by zero", stderr)
        self.assertEqual(stdout, "should not print\n")
        self.assertEqual(rc, 0)
        
        # Invalid syntax
        stdout, stderr, rc = self.run_psh_command('((5 +)); echo "should not print"')
        self.assertIn("psh:", stderr)
        self.assertEqual(stdout, "should not print\n")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()