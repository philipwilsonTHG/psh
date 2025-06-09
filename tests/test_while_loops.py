import unittest
import sys
import os
import tempfile
import time
from io import StringIO

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.ast_nodes import WhileStatement, StatementList, TopLevel, CommandList


class TestWhileLoops(unittest.TestCase):
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

    def test_tokenize_while_keywords(self):
        """Test that while/do/done keywords are tokenized correctly."""
        tokens = tokenize("while do done")
        token_types = [token.type.name for token in tokens[:-1]]  # Exclude EOF
        self.assertEqual(token_types, ['WHILE', 'DO', 'DONE'])

    def test_parse_simple_while_statement(self):
        """Test parsing a simple while statement."""
        tokens = tokenize("while true; do echo hello; done")
        ast = parse(tokens)
        
        # Should return a TopLevel containing one WhileStatement
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], WhileStatement)
        
        while_stmt = ast.items[0]
        self.assertIsInstance(while_stmt.condition, CommandList)
        self.assertIsInstance(while_stmt.body, CommandList)

    def test_execute_while_false_condition(self):
        """Test executing while statement with false condition (should not run body)."""
        result = self.shell.run_command("while false; do echo should_not_see; done")
        self.assertEqual(result, 0)
        self.assertEqual(self.get_output().strip(), "")

    def test_execute_while_with_file_test(self):
        """Test while loop with file existence condition."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        
        try:
            # File exists, so loop should run once then exit when file is removed
            result = self.shell.run_command(f"while [ -f {tmp_name} ]; do echo found; rm {tmp_name}; done")
            self.assertEqual(result, 0)
            self.assertIn("found", self.get_output())
            # Verify file was actually removed
            self.assertFalse(os.path.exists(tmp_name))
        finally:
            # Clean up in case test failed
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_while_with_test_command(self):
        """Test while statement using test command for condition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "counter")
            
            # Create initial file
            with open(test_file, "w") as f:
                f.write("start")
            
            # Loop while file exists, then remove it
            result = self.shell.run_command(f"while [ -e {test_file} ]; do echo loop_body; rm {test_file}; done")
            self.assertEqual(result, 0)
            self.assertIn("loop_body", self.get_output())

    def test_while_with_bracket_command(self):
        """Test while statement using [ command for condition."""
        # Test string comparison that's initially true, then becomes false
        result = self.shell.run_command("X=hello; while [ \"$X\" = \"hello\" ]; do echo matched; X=goodbye; done")
        self.assertEqual(result, 0)
        self.assertIn("matched", self.get_output())

    def test_while_with_complex_condition(self):
        """Test while statement with complex condition using && and ||."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1")
            file2 = os.path.join(tmpdir, "file2")
            
            # Create both files
            with open(file1, "w") as f:
                f.write("1")
            with open(file2, "w") as f:
                f.write("2")
            
            # Loop while both files exist, remove one each iteration
            result = self.shell.run_command(f"while [ -f {file1} ] && [ -f {file2} ]; do echo both_exist; rm {file1}; done")
            self.assertEqual(result, 0)
            self.assertIn("both_exist", self.get_output())

    def test_while_body_with_multiple_commands(self):
        """Test while loop with multiple commands in the body."""
        result = self.shell.run_command("X=start; while [ \"$X\" = \"start\" ]; do echo first; echo second; X=end; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("first", output)
        self.assertIn("second", output)

    def test_while_with_pipeline_in_condition(self):
        """Test while statement with pipeline in condition."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("test line\n")
            tmp_name = tmp.name
        
        try:
            # Loop while file has content
            result = self.shell.run_command(f"while cat {tmp_name} | grep -q test; do echo found_content; echo > {tmp_name}; done")
            self.assertEqual(result, 0)
            self.assertIn("found_content", self.get_output())
        finally:
            os.unlink(tmp_name)

    def test_while_with_pipeline_in_body(self):
        """Test while statement with pipeline in body."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        
        try:
            result = self.shell.run_command(f"while [ -f {tmp_name} ]; do echo hello | cat > /dev/null; rm {tmp_name}; done")
            self.assertEqual(result, 0)
            # Should execute once (file exists initially, then gets removed)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_while_exit_status_propagation(self):
        """Test that while statement returns correct exit status."""
        # While with false condition should return 0 (loop executed successfully, just 0 iterations)
        result = self.shell.run_command("while false; do echo no; done")
        self.assertEqual(result, 0)
        
        # While that executes and last command in body succeeds
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        
        try:
            result = self.shell.run_command(f"while [ -f {tmp_name} ]; do true; rm {tmp_name}; done")
            self.assertEqual(result, 0)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_while_with_variable_modification(self):
        """Test while loop that modifies variables."""
        # Test with string variable
        result = self.shell.run_command("STATUS=running; while [ \"$STATUS\" = \"running\" ]; do echo active; STATUS=stopped; done; echo \"$STATUS\"")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("active", output)
        self.assertIn("stopped", output)

    def test_multiline_while_statement(self):
        """Test while statement with newlines."""
        # This tests that our parser handles multiline while statements
        tokens = tokenize("""while true
do
    echo success
done""")
        ast = parse(tokens)
        # Parser returns TopLevel for multiline input
        self.assertIsInstance(ast, TopLevel)
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], WhileStatement)

    def test_nested_commands_in_while(self):
        """Test while statement with complex commands."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_name = tmp.name
        
        try:
            result = self.shell.run_command(f"while echo testing && [ -f {tmp_name} ]; do echo in_loop; rm {tmp_name}; done")
            self.assertEqual(result, 0)
            output = self.get_output()
            self.assertIn("testing", output)
            self.assertIn("in_loop", output)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_while_with_redirections(self):
        """Test while statement with I/O redirections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.txt")
            output_file = os.path.join(tmpdir, "output.txt")
            
            # Create input file
            with open(input_file, "w") as f:
                f.write("line1\nline2\n")
            
            # While loop with redirection
            result = self.shell.run_command(f"while [ -s {input_file} ]; do head -n 1 {input_file} >> {output_file}; tail -n +2 {input_file} > {input_file}.tmp && mv {input_file}.tmp {input_file}; done")
            self.assertEqual(result, 0)
            
            # Check output file was created and has content
            self.assertTrue(os.path.exists(output_file))
            with open(output_file, "r") as f:
                content = f.read()
                self.assertIn("line1", content)
                self.assertIn("line2", content)

    def test_while_syntax_errors(self):
        """Test while statement syntax error handling."""
        # Missing 'do'
        with self.assertRaises(Exception):
            tokens = tokenize("while true; done")
            parse(tokens)
        
        # Missing 'done'  
        with self.assertRaises(Exception):
            tokens = tokenize("while true; do echo hello")
            parse(tokens)
        
        # Missing condition
        with self.assertRaises(Exception):
            tokens = tokenize("while; do echo hello; done")
            parse(tokens)

    def test_while_with_empty_body(self):
        """Test while statement with empty body."""
        result = self.shell.run_command("while false; do true; done")
        self.assertEqual(result, 0)
        self.assertEqual(self.get_output().strip(), "")


if __name__ == '__main__':
    unittest.main()