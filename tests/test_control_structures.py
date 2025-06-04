import unittest
import sys
import os
import tempfile
import stat
import time
from io import StringIO

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.ast_nodes import IfStatement, CommandList


class TestControlStructures(unittest.TestCase):
    def setUp(self):
        self.shell = Shell()
        # Redirect stdout for testing
        self.saved_stdout = sys.stdout
        self.test_output = StringIO()
        sys.stdout = self.test_output

    def tearDown(self):
        sys.stdout = self.saved_stdout

    def get_output(self):
        return self.test_output.getvalue()

    def test_tokenize_if_keywords(self):
        """Test that if/then/else/fi keywords are tokenized correctly."""
        tokens = tokenize("if then else fi")
        token_types = [token.type.name for token in tokens[:-1]]  # Exclude EOF
        self.assertEqual(token_types, ['IF', 'THEN', 'ELSE', 'FI'])

    def test_parse_simple_if_statement(self):
        """Test parsing a simple if statement."""
        tokens = tokenize("if true; then echo hello; fi")
        ast = parse(tokens)
        
        # Should return a TopLevel containing one IfStatement
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], IfStatement)
        
        if_stmt = ast.items[0]
        self.assertIsInstance(if_stmt.condition, CommandList)
        self.assertIsInstance(if_stmt.then_part, CommandList)
        self.assertIsNone(if_stmt.else_part)

    def test_parse_if_else_statement(self):
        """Test parsing an if/else statement."""
        tokens = tokenize("if false; then echo then; else echo else; fi")
        ast = parse(tokens)
        
        if_stmt = ast.items[0]
        self.assertIsInstance(if_stmt.condition, CommandList)
        self.assertIsInstance(if_stmt.then_part, CommandList)
        self.assertIsInstance(if_stmt.else_part, CommandList)

    def test_execute_if_true(self):
        """Test executing if statement with true condition."""
        result = self.shell.run_command("if true; then echo success; fi")
        self.assertEqual(result, 0)
        self.assertIn("success", self.get_output())

    def test_execute_if_false(self):
        """Test executing if statement with false condition."""
        result = self.shell.run_command("if false; then echo should_not_see; fi")
        self.assertEqual(result, 0)
        self.assertEqual(self.get_output().strip(), "")

    def test_execute_if_else_true(self):
        """Test executing if/else with true condition."""
        result = self.shell.run_command("if true; then echo then_part; else echo else_part; fi")
        self.assertEqual(result, 0)
        self.assertIn("then_part", self.get_output())
        self.assertNotIn("else_part", self.get_output())

    def test_execute_if_else_false(self):
        """Test executing if/else with false condition."""
        result = self.shell.run_command("if false; then echo then_part; else echo else_part; fi")
        self.assertEqual(result, 0)
        self.assertNotIn("then_part", self.get_output())
        self.assertIn("else_part", self.get_output())

    def test_test_command_basic(self):
        """Test basic test command functionality."""
        # test with no arguments returns false
        result = self.shell.run_command("test")
        self.assertEqual(result, 1)
        
        # test with non-empty string returns true
        result = self.shell.run_command("test hello")
        self.assertEqual(result, 0)
        
        # test with empty string returns false
        result = self.shell.run_command("test ''")
        self.assertEqual(result, 1)

    def test_test_command_string_operators(self):
        """Test test command with string operators."""
        # -z (string is empty)
        result = self.shell.run_command("test -z ''")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test -z hello")
        self.assertEqual(result, 1)
        
        # -n (string is non-empty)
        result = self.shell.run_command("test -n hello")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test -n ''")
        self.assertEqual(result, 1)
        
        # = (string equality)
        result = self.shell.run_command("test hello = hello")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test hello = world")
        self.assertEqual(result, 1)
        
        # != (string inequality)
        result = self.shell.run_command("test hello != world")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test hello != hello")
        self.assertEqual(result, 1)

    def test_test_command_numeric_operators(self):
        """Test test command with numeric operators."""
        # -eq (equal)
        result = self.shell.run_command("test 5 -eq 5")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test 5 -eq 3")
        self.assertEqual(result, 1)
        
        # -ne (not equal)
        result = self.shell.run_command("test 5 -ne 3")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test 5 -ne 5")
        self.assertEqual(result, 1)
        
        # -lt (less than)
        result = self.shell.run_command("test 3 -lt 5")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test 5 -lt 3")
        self.assertEqual(result, 1)
        
        # -gt (greater than)
        result = self.shell.run_command("test 5 -gt 3")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("test 3 -gt 5")
        self.assertEqual(result, 1)

    def test_test_command_file_operators(self):
        """Test test command with file operators."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(b"test content")
        
        try:
            # -f (file exists and is regular file)
            result = self.shell.run_command(f"test -f {tmp_name}")
            self.assertEqual(result, 0)
            
            result = self.shell.run_command("test -f /nonexistent/file")
            self.assertEqual(result, 1)
            
            # -e (file exists)
            result = self.shell.run_command(f"test -e {tmp_name}")
            self.assertEqual(result, 0)
            
            result = self.shell.run_command("test -e /nonexistent/file")
            self.assertEqual(result, 1)
            
        finally:
            os.unlink(tmp_name)

    def test_bracket_command(self):
        """Test [ command (alias for test)."""
        result = self.shell.run_command("[ hello = hello ]")
        self.assertEqual(result, 0)
        
        result = self.shell.run_command("[ hello = world ]")
        self.assertEqual(result, 1)
        
        # Missing closing bracket should return syntax error
        result = self.shell.run_command("[ hello = hello")
        self.assertEqual(result, 2)

    def test_if_with_test_command(self):
        """Test if statement using test command for condition."""
        result = self.shell.run_command("if test hello = hello; then echo match; fi")
        self.assertEqual(result, 0)
        self.assertIn("match", self.get_output())

    def test_if_with_bracket_command(self):
        """Test if statement using [ command for condition."""
        result = self.shell.run_command("if [ hello = hello ]; then echo bracket_match; fi")
        self.assertEqual(result, 0)
        self.assertIn("bracket_match", self.get_output())

    def test_if_with_command_exit_status(self):
        """Test if statement using command exit status."""
        # Create a temporary script that exits with status 0
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp:
            tmp.write("#!/bin/bash\nexit 0\n")
            tmp_name = tmp.name
        
        try:
            os.chmod(tmp_name, 0o755)
            result = self.shell.run_command(f"if {tmp_name}; then echo zero_exit; fi")
            self.assertEqual(result, 0)
            self.assertIn("zero_exit", self.get_output())
        finally:
            os.unlink(tmp_name)

    def test_multiline_if_statement(self):
        """Test if statement with newlines."""
        # This tests that our parser handles multiline if statements
        tokens = tokenize("""if true
then
    echo success
fi""")
        ast = parse(tokens)
        self.assertIsInstance(ast.items[0], IfStatement)

    def test_nested_commands_in_if(self):
        """Test if statement with complex commands."""
        result = self.shell.run_command("if echo testing && true; then echo nested_success; fi")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("testing", output)
        self.assertIn("nested_success", output)

    def test_if_exit_status_propagation(self):
        """Test that if statement returns correct exit status."""
        # If condition false and no else, should return 0
        result = self.shell.run_command("if false; then echo no; fi")
        self.assertEqual(result, 0)
        
        # If condition true, return exit status of then part
        result = self.shell.run_command("if true; then false; fi")
        self.assertEqual(result, 1)
        
        # If condition false with else, return exit status of else part
        result = self.shell.run_command("if false; then true; else false; fi")
        self.assertEqual(result, 1)

    def test_enhanced_file_test_operators(self):
        """Test the new file test operators added to psh."""
        # Create test files and directories
        with tempfile.TemporaryDirectory() as tmpdir:
            # Regular file with content
            regular_file = os.path.join(tmpdir, "regular.txt")
            with open(regular_file, "w") as f:
                f.write("test content")
            
            # Empty file
            empty_file = os.path.join(tmpdir, "empty.txt")
            with open(empty_file, "w") as f:
                pass
            
            # Directory
            test_dir = os.path.join(tmpdir, "testdir")
            os.mkdir(test_dir)
            
            # Symbolic link
            link_file = os.path.join(tmpdir, "link.txt")
            os.symlink(regular_file, link_file)
            
            # Test -s (non-empty file)
            result = self.shell.run_command(f"test -s {regular_file}")
            self.assertEqual(result, 0, "Regular file with content should pass -s test")
            
            result = self.shell.run_command(f"test -s {empty_file}")
            self.assertEqual(result, 1, "Empty file should fail -s test")
            
            # Test -L and -h (symbolic link)
            result = self.shell.run_command(f"test -L {link_file}")
            self.assertEqual(result, 0, "Symbolic link should pass -L test")
            
            result = self.shell.run_command(f"test -h {link_file}")
            self.assertEqual(result, 0, "Symbolic link should pass -h test")
            
            result = self.shell.run_command(f"test -L {regular_file}")
            self.assertEqual(result, 1, "Regular file should fail -L test")

    def test_file_permission_operators(self):
        """Test file permission and ownership operators."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "perm_test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            
            # Test -O (owned by effective UID)
            result = self.shell.run_command(f"test -O {test_file}")
            self.assertEqual(result, 0, "File should be owned by current user")
            
            # Test -G (owned by effective GID) 
            result = self.shell.run_command(f"test -G {test_file}")
            self.assertEqual(result, 0, "File should be owned by current group")

    def test_file_comparison_operators(self):
        """Test file comparison operators (-nt, -ot, -ef)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")
            link1 = os.path.join(tmpdir, "link1.txt")
            
            # Create file1
            with open(file1, "w") as f:
                f.write("first")
            
            # Wait a bit to ensure different timestamps
            time.sleep(0.1)
            
            # Create file2 (newer)
            with open(file2, "w") as f:
                f.write("second")
            
            # Create hard link to file1
            os.link(file1, link1)
            
            # Test -nt (newer than)
            result = self.shell.run_command(f"test {file2} -nt {file1}")
            self.assertEqual(result, 0, "file2 should be newer than file1")
            
            result = self.shell.run_command(f"test {file1} -nt {file2}")
            self.assertEqual(result, 1, "file1 should not be newer than file2")
            
            # Test -ot (older than)
            result = self.shell.run_command(f"test {file1} -ot {file2}")
            self.assertEqual(result, 0, "file1 should be older than file2")
            
            result = self.shell.run_command(f"test {file2} -ot {file1}")
            self.assertEqual(result, 1, "file2 should not be older than file1")
            
            # Test -ef (same file)
            result = self.shell.run_command(f"test {file1} -ef {link1}")
            self.assertEqual(result, 0, "file1 and link1 should be the same file")
            
            result = self.shell.run_command(f"test {file1} -ef {file2}")
            self.assertEqual(result, 1, "file1 and file2 should not be the same file")

    def test_special_device_operators(self):
        """Test special device file operators."""
        # Test -t (terminal) with stdin/stdout/stderr
        result = self.shell.run_command("test -t 0")
        # Result depends on whether stdin is a terminal, but should not error
        self.assertIn(result, [0, 1], "test -t 0 should return 0 or 1")
        
        result = self.shell.run_command("test -t 1")
        # Result depends on whether stdout is a terminal, but should not error
        self.assertIn(result, [0, 1], "test -t 1 should return 0 or 1")
        
        # Test with invalid file descriptor
        result = self.shell.run_command("test -t 999")
        self.assertEqual(result, 1, "Invalid file descriptor should fail -t test")
        
        # Test with non-numeric argument
        result = self.shell.run_command("test -t abc")
        self.assertEqual(result, 1, "Non-numeric fd should fail -t test")

    def test_modification_time_operator(self):
        """Test -N (modified since last read) operator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "mtime_test.txt")
            with open(test_file, "w") as f:
                f.write("initial content")
            
            # Read the file to set access time
            with open(test_file, "r") as f:
                f.read()
            
            # Small delay
            time.sleep(0.1)
            
            # Modify the file
            with open(test_file, "a") as f:
                f.write("\nmodified")
            
            # Test -N (should be true since we modified after reading)
            result = self.shell.run_command(f"test -N {test_file}")
            self.assertEqual(result, 0, "File should have been modified since last read")

    def test_error_handling_for_new_operators(self):
        """Test error handling for new file test operators."""
        # Test with non-existent file
        result = self.shell.run_command("test -s /nonexistent/file")
        self.assertEqual(result, 1, "Non-existent file should fail -s test")
        
        result = self.shell.run_command("test -L /nonexistent/file")
        self.assertEqual(result, 1, "Non-existent file should fail -L test")
        
        result = self.shell.run_command("test -O /nonexistent/file")
        self.assertEqual(result, 1, "Non-existent file should fail -O test")
        
        # Test file comparison with non-existent files
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        
        try:
            result = self.shell.run_command(f"test {tmp_name} -nt /nonexistent/file")
            self.assertEqual(result, 1, "Comparison with non-existent file should fail")
            
            result = self.shell.run_command(f"test /nonexistent/file -ef {tmp_name}")
            self.assertEqual(result, 1, "Comparison with non-existent file should fail")
        finally:
            os.unlink(tmp_name)


if __name__ == '__main__':
    unittest.main()