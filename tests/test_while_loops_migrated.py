"""Tests for while loops with support for both legacy and unified types."""
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
from psh.parser import parse as parse_legacy
from psh.parser_refactored import parse as parse_refactored
from psh.ast_nodes import WhileStatement, WhileLoop, StatementList, TopLevel, CommandList, ExecutionContext
from tests.helpers.unified_types_helper import parse_with_unified_types, both_type_modes
import pytest


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

    def test_parse_simple_while_statement_legacy(self):
        """Test parsing a simple while statement with legacy types."""
        tokens = tokenize("while true; do echo hello; done")
        ast = parse_legacy(tokens)
        
        # Should return a TopLevel containing one WhileStatement
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], WhileStatement)
        
        while_stmt = ast.items[0]
        self.assertIsInstance(while_stmt.condition, CommandList)
        self.assertIsInstance(while_stmt.body, CommandList)

    def test_parse_simple_while_statement_unified(self):
        """Test parsing a simple while statement with unified types."""
        tokens = tokenize("while true; do echo hello; done")
        ast = parse_refactored(tokens, use_unified_types=True)
        
        # Should return a TopLevel containing one WhileLoop
        self.assertEqual(len(ast.items), 1)
        self.assertIsInstance(ast.items[0], WhileLoop)
        
        while_loop = ast.items[0]
        self.assertIsInstance(while_loop.condition, StatementList)
        self.assertIsInstance(while_loop.body, StatementList)
        self.assertEqual(while_loop.execution_context, ExecutionContext.STATEMENT)

    def test_execute_while_false_condition(self):
        """Test that while loop with false condition doesn't execute body."""
        self.shell.run_command("while false; do echo should_not_print; done")
        self.assertEqual(self.get_output(), "")
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_execute_while_true_with_break(self):
        """Test while true loop with break statement."""
        self.shell.run_command("i=0; while true; do echo $i; i=$((i+1)); if [ $i -eq 3 ]; then break; fi; done")
        self.assertEqual(self.get_output().strip(), "0\n1\n2")
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_execute_while_with_test_condition(self):
        """Test while loop with test condition."""
        self.shell.run_command("i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done")
        self.assertEqual(self.get_output().strip(), "0\n1\n2")
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_execute_while_with_continue(self):
        """Test while loop with continue statement."""
        self.shell.run_command("i=0; while [ $i -lt 5 ]; do i=$((i+1)); if [ $i -eq 3 ]; then continue; fi; echo $i; done")
        # Should skip 3
        self.assertEqual(self.get_output().strip(), "1\n2\n4\n5")
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_execute_nested_while_loops(self):
        """Test nested while loops."""
        self.shell.run_command("""
i=0
while [ $i -lt 2 ]; do
    j=0
    while [ $j -lt 2 ]; do
        echo "$i,$j"
        j=$((j+1))
    done
    i=$((i+1))
done
""")
        expected = "0,0\n0,1\n1,0\n1,1"
        self.assertEqual(self.get_output().strip(), expected)
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_while_loop_preserves_exit_status(self):
        """Test that while loop preserves exit status of last command."""
        # Exit status should be from last executed command in body
        self.shell.run_command("i=0; while [ $i -lt 2 ]; do false; i=$((i+1)); done")
        self.assertEqual(self.shell.last_exit_code, 1)
        
        # If condition becomes false, exit status should be 0
        self.shell.run_command("i=0; while [ $i -lt 0 ]; do false; done")
        self.assertEqual(self.shell.last_exit_code, 0)

    def test_while_loop_with_multiple_commands(self):
        """Test while loop with multiple commands in body."""
        self.shell.run_command("""
count=3
while [ $count -gt 0 ]; do
    echo "Count: $count"
    count=$((count-1))
    echo "Remaining: $count"
done
echo "Done!"
""")
        expected = """Count: 3
Remaining: 2
Count: 2
Remaining: 1
Count: 1
Remaining: 0
Done!"""
        self.assertEqual(self.get_output().strip(), expected)

    def test_while_read_pattern(self):
        """Test the common while read pattern."""
        # Create a temp file with test data
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_file = f.name
        
        try:
            self.shell.run_command(f"""
while read line; do
    echo "Read: $line"
done < {temp_file}
""")
            expected = "Read: line1\nRead: line2\nRead: line3"
            self.assertEqual(self.get_output().strip(), expected)
        finally:
            os.unlink(temp_file)

    def test_while_loop_with_io_redirection(self):
        """Test while loop with I/O redirections."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            self.shell.run_command(f"""
i=0
while [ $i -lt 3 ]; do
    echo "Line $i"
    i=$((i+1))
done > {temp_file}
""")
            # Output should go to file, not stdout
            self.assertEqual(self.get_output(), "")
            
            # Check file contents
            with open(temp_file, 'r') as f:
                contents = f.read()
            self.assertEqual(contents.strip(), "Line 0\nLine 1\nLine 2")
        finally:
            os.unlink(temp_file)

    def test_while_loop_variable_scope(self):
        """Test that variables modified in while loop persist."""
        self.shell.run_command("""
x=0
while [ $x -lt 3 ]; do
    x=$((x+1))
    y=$x
done
echo "x=$x y=$y"
""")
        self.assertEqual(self.get_output().strip(), "x=3 y=3")

    def test_while_command_substitution(self):
        """Test while loop condition using command substitution."""
        self.shell.run_command("""
while [ "$(echo yes)" = "yes" ]; do
    echo "Condition true"
    break
done
""")
        self.assertEqual(self.get_output().strip(), "Condition true")

    def test_while_with_arithmetic_condition(self):
        """Test while loop with arithmetic condition."""
        self.shell.run_command("""
i=5
while ((i > 0)); do
    echo $i
    ((i--))
done
""")
        self.assertEqual(self.get_output().strip(), "5\n4\n3\n2\n1")

    def test_while_read_timeout_behavior(self):
        """Test while read with timeout behaves correctly."""
        # This tests that the read timeout (exit code 142) doesn't break the while loop incorrectly
        self.shell.run_command("""
echo "test" | while read -t 1 line; do
    echo "Read: $line"
done
echo "Exit: $?"
""")
        self.assertEqual(self.get_output().strip(), "Read: test\nExit: 0")

    def test_parse_while_in_pipeline_unified(self):
        """Test parsing while loop in pipeline with unified types."""
        code = "echo hello | while read line; do echo $line; done"
        ast = parse_with_unified_types(code, use_unified=True)
        
        # Should parse as CommandList with pipeline
        pipeline = ast.statements[0].pipelines[0]
        self.assertEqual(len(pipeline.commands), 2)
        
        # Second command should be WhileLoop with PIPELINE context
        while_loop = pipeline.commands[1]
        self.assertIsInstance(while_loop, WhileLoop)
        self.assertEqual(while_loop.execution_context, ExecutionContext.PIPELINE)

    def test_break_outside_loop_error(self):
        """Test that break outside of loop produces error."""
        self.shell.run_command("break")
        output = self.get_output()
        # Shell should print error to stderr, but we can check exit code
        self.assertEqual(self.shell.last_exit_code, 1)

    def test_continue_outside_loop_error(self):
        """Test that continue outside of loop produces error."""
        self.shell.run_command("continue")
        # Shell should print error to stderr, but we can check exit code
        self.assertEqual(self.shell.last_exit_code, 1)

    def test_while_with_multiline_condition(self):
        """Test while loop with multi-line condition."""
        self.shell.run_command("""
while [ 1 -eq 1 ] &&
      [ 2 -eq 2 ]; do
    echo "Both conditions true"
    break
done
""")
        self.assertEqual(self.get_output().strip(), "Both conditions true")


class TestWhileLoopsParametrized:
    """Parametrized tests that run with both legacy and unified types."""
    
    @pytest.mark.parametrize("use_unified", [False, True], ids=["legacy", "unified"])
    def test_while_loop_parsing_both_modes(self, use_unified):
        """Test parsing while loops in both modes."""
        code = "while true; do echo test; done"
        ast = parse_with_unified_types(code, use_unified=use_unified)
        
        # Check correct type based on mode
        if use_unified:
            assert isinstance(ast.items[0], WhileLoop)
            assert ast.items[0].execution_context == ExecutionContext.STATEMENT
        else:
            assert isinstance(ast.items[0], WhileStatement)


if __name__ == '__main__':
    unittest.main()