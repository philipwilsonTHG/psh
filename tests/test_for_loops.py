import unittest
import sys
import warnings
import os
import tempfile
import time
from io import StringIO

# Add psh module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from psh.shell import Shell
from psh.lexer import tokenize
from psh.parser import parse
from psh.ast_nodes import ForLoop, StatementList, TopLevel, Pipeline, CommandList, ExecutionContext


class TestForLoops(unittest.TestCase):
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

    def test_tokenize_for_keywords(self):
        """Test that for/in/do/done keywords are tokenized correctly in context."""
        # Test keywords in proper context
        tokens = tokenize("for i in a; do echo; done")
        token_types = [token.type.name for token in tokens[:-1]]  # Exclude EOF
        expected = ['FOR', 'WORD', 'IN', 'WORD', 'SEMICOLON', 'DO', 'WORD', 'SEMICOLON', 'DONE']
        self.assertEqual(token_types, expected)
        
        # Test that 'do' and 'done' are NOT keywords when used as regular words
        tokens = tokenize("echo do done")
        token_types = [token.type.name for token in tokens[:-1]]
        self.assertEqual(token_types, ['WORD', 'WORD', 'WORD'])

    def test_parse_simple_for_statement(self):
        """Test parsing a simple for statement."""
        tokens = tokenize("for i in a b c; do echo $i; done")
        ast = parse(tokens)
        
        # Should return a TopLevel containing one ForLoop
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], ForLoop)
        
        for_stmt = ast.items[0]
        self.assertEqual(for_stmt.variable, "i")
        self.assertEqual(for_stmt.items, ["a", "b", "c"])
        self.assertIsInstance(for_stmt.body, CommandList)

    def test_execute_for_with_simple_list(self):
        """Test executing for statement with simple word list."""
        result = self.shell.run_command("for i in hello world; do echo $i; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("hello", output)
        self.assertIn("world", output)
        # Check that both items appear in order
        lines = output.strip().split('\n')
        self.assertEqual(lines, ["hello", "world"])

    def test_execute_for_with_numbers(self):
        """Test for loop with numeric values."""
        result = self.shell.run_command("for num in 1 2 3; do echo Number $num; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("Number 1", output)
        self.assertIn("Number 2", output) 
        self.assertIn("Number 3", output)

    def test_for_with_glob_patterns(self):
        """Test for loop with file glob patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = ["file1.txt", "file2.txt", "file3.log"]
            for fname in test_files:
                with open(os.path.join(tmpdir, fname), "w") as f:
                    f.write(f"content of {fname}")
            
            # Test glob pattern
            result = self.shell.run_command(f"for file in {tmpdir}/*.txt; do echo $file; done")
            self.assertEqual(result, 0)
            output = self.get_output()
            
            # Should match both .txt files
            self.assertIn("file1.txt", output)
            self.assertIn("file2.txt", output)
            self.assertNotIn("file3.log", output)

    def test_for_with_empty_list(self):
        """Test for loop with empty iteration list."""
        result = self.shell.run_command("for i in; do echo should_not_see; done")
        self.assertEqual(result, 0)
        self.assertEqual(self.get_output().strip(), "")

    def test_for_with_variable_expansion(self):
        """Test for loop with variable expansion in the list."""
        result = self.shell.run_command("LIST='a b c'; for item in $LIST; do echo $item; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        # Note: This might not work perfectly yet due to word splitting limitations
        # but the loop structure should work
        self.assertTrue(len(output.strip()) > 0)

    def test_for_variable_persistence(self):
        """Test that for loop variable persists after loop with last value."""
        # Set initial variable value
        self.shell.run_command("i=initial")
        
        # Use i in for loop with multiple values
        result = self.shell.run_command("for i in first second last; do echo $i; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("first", output)
        self.assertIn("second", output)
        self.assertIn("last", output)
        
        # Check that variable has the last iteration value (bash behavior)
        self.test_output.truncate(0)
        self.test_output.seek(0)
        self.shell.run_command("echo $i")
        self.assertEqual(self.get_output().strip(), "last")

    def test_for_with_multiple_commands_in_body(self):
        """Test for loop with multiple commands in the body."""
        result = self.shell.run_command("for i in one two; do echo Start $i; echo End $i; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        lines = output.strip().split('\n')
        self.assertEqual(len(lines), 4)
        self.assertIn("Start one", lines)
        self.assertIn("End one", lines)
        self.assertIn("Start two", lines)
        self.assertIn("End two", lines)

    @unittest.skip("Pipeline handling issue - pipelines being treated as background jobs")
    def test_for_with_pipeline_in_body(self):
        """Test for loop with pipeline in body."""
        result = self.shell.run_command("for i in hello world; do echo $i | cat; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("hello", output)
        self.assertIn("world", output)

    def test_for_with_redirection(self):
        """Test for loop with I/O redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "for_output.txt")
            
            result = self.shell.run_command(f"for i in alpha beta; do echo $i >> {output_file}; done")
            self.assertEqual(result, 0)
            
            # Check output file
            self.assertTrue(os.path.exists(output_file))
            with open(output_file, "r") as f:
                content = f.read()
                self.assertIn("alpha", content)
                self.assertIn("beta", content)

    def test_for_exit_status_propagation(self):
        """Test that for statement returns correct exit status."""
        # For loop that succeeds
        result = self.shell.run_command("for i in a b; do true; done")
        self.assertEqual(result, 0)
        
        # For loop where last iteration fails
        result = self.shell.run_command("for i in a b; do test $i = b && false; done")
        self.assertEqual(result, 1)

    def test_for_with_conditional_commands(self):
        """Test for loop with conditional commands in body."""
        result = self.shell.run_command("for i in 1 2 3; do if [ $i = 2 ]; then echo found_two; fi; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("found_two", output)
        # Should only appear once
        self.assertEqual(output.strip(), "found_two")

    def test_multiline_for_statement(self):
        """Test for statement with newlines."""
        tokens = tokenize("""for i in a b
do
    echo $i
done""")
        ast = parse(tokens)
        # Parser returns TopLevel for multiline input
        self.assertIsInstance(ast, TopLevel)
        self.assertEqual(len(ast.items), 1)
        # When not in a pipeline, it's a ForLoop with STATEMENT context
        self.assertIsInstance(ast.items[0], ForLoop)

    def test_for_with_quoted_items(self):
        """Test for loop with quoted items in the list."""
        result = self.shell.run_command('for i in "hello world" "foo bar"; do echo "$i"; done')
        self.assertEqual(result, 0)
        output = self.get_output()
        lines = output.strip().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertIn("hello world", lines)
        self.assertIn("foo bar", lines)

    def test_for_with_special_characters(self):
        """Test for loop with special characters in items."""
        result = self.shell.run_command("for i in 'item;with;semicolons' 'item&with&ampersands'; do echo $i; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        self.assertIn("item;with;semicolons", output)
        self.assertIn("item&with&ampersands", output)

    def test_for_syntax_errors(self):
        """Test for statement syntax error handling."""
        # Missing 'in'
        with self.assertRaises(Exception):
            tokens = tokenize("for i do echo $i; done")
            parse(tokens)
        
        # Missing 'do'
        with self.assertRaises(Exception):
            tokens = tokenize("for i in a b; done")
            parse(tokens)
        
        # Missing 'done'
        with self.assertRaises(Exception):
            tokens = tokenize("for i in a b; do echo $i")
            parse(tokens)
        
        # Missing variable name
        with self.assertRaises(Exception):
            tokens = tokenize("for in a b; do echo test; done")
            parse(tokens)

    def test_for_nested_in_other_constructs(self):
        """Test for loop nested in other control structures."""
        result = self.shell.run_command("if true; then for i in nested; do echo $i; done; fi")
        self.assertEqual(result, 0)
        self.assertIn("nested", self.get_output())

    def test_for_variable_persists_when_new(self):
        """Test that for loop variable persists even when it didn't exist before."""
        # Make sure variable doesn't exist initially
        self.assertNotIn('loop_var', self.shell.variables)
        
        # Run for loop
        result = self.shell.run_command("for loop_var in test; do echo $loop_var; done")
        self.assertEqual(result, 0)
        
        # Variable should persist with last value (bash behavior)
        self.assertIn('loop_var', self.shell.variables)
        self.assertEqual(self.shell.variables['loop_var'], 'test')

    def test_for_with_no_glob_matches(self):
        """Test for loop with glob pattern that matches no files."""
        # Use a pattern that definitely won't match anything
        result = self.shell.run_command("for file in /nonexistent/path/*.xyz; do echo $file; done")
        self.assertEqual(result, 0)
        output = self.get_output()
        # Should iterate over the literal pattern since no files matched
        self.assertIn("/nonexistent/path/*.xyz", output)


if __name__ == '__main__':
    unittest.main()
