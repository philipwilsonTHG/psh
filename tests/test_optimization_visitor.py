"""
Tests for the OptimizationVisitor.

This module tests AST optimization functionality.
"""

import pytest
from psh.state_machine_lexer import tokenize
from psh.parser import parse
from psh.visitor.optimization_visitor import OptimizationVisitor
from psh.visitor.formatter_visitor import FormatterVisitor
from psh.ast_nodes import Pipeline, SimpleCommand, StatementList


class TestOptimizationVisitor:
    """Test AST optimization functionality."""
    
    def parse_command(self, command):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return parse(tokens)
    
    def optimize_and_format(self, command):
        """Parse, optimize, and format back to string."""
        ast = self.parse_command(command)
        optimizer = OptimizationVisitor()
        optimized = optimizer.visit(ast)
        formatter = FormatterVisitor()
        return formatter.visit(optimized).strip()
    
    def test_remove_trailing_cat(self):
        """Test removal of unnecessary cat at end of pipeline."""
        original = "echo hello | cat"
        optimized = self.optimize_and_format(original)
        assert optimized == "echo hello"
    
    def test_remove_leading_cat(self):
        """Test removal of cat at beginning of pipeline."""
        original = "cat | grep test"
        optimized = self.optimize_and_format(original)
        assert optimized == "grep test"
    
    def test_keep_cat_with_args(self):
        """Test that cat with arguments is not removed."""
        original = "echo hello | cat -n"
        optimized = self.optimize_and_format(original)
        assert optimized == "echo hello | cat -n"
    
    def test_keep_cat_with_redirect(self):
        """Test that cat with redirections is not removed."""
        original = "cat < file.txt | grep test"
        optimized = self.optimize_and_format(original)
        assert optimized == "cat <file.txt | grep test"  # Formatter doesn't add space
    
    def test_optimize_if_true(self):
        """Test optimization of if true statements."""
        original = "if true; then echo yes; fi"
        optimized = self.optimize_and_format(original)
        assert optimized == "echo yes"
    
    def test_optimize_if_false_with_else(self):
        """Test optimization of if false with else."""
        original = "if false; then echo no; else echo yes; fi"
        optimized = self.optimize_and_format(original)
        assert optimized == "echo yes"
    
    def test_optimize_if_false_no_else(self):
        """Test optimization of if false with no else."""
        original = "if false; then echo no; fi"
        optimized = self.optimize_and_format(original)
        # Empty statement list gets removed
        assert optimized == ""
    
    def test_optimize_while_false(self):
        """Test optimization of while false loops."""
        original = "while false; do echo never; done"
        optimized = self.optimize_and_format(original)
        assert optimized == ""
    
    def test_keep_while_true(self):
        """Test that while true is not optimized away."""
        original = "while true; do echo forever; done"
        optimized = self.optimize_and_format(original)
        # Formatter uses different style
        assert optimized == "while\n  true\ndo\n  echo forever\ndone"
    
    def test_complex_pipeline_optimization(self):
        """Test optimization in complex pipelines."""
        original = "cat | grep test | cat | sort | cat"
        optimized = self.optimize_and_format(original)
        assert optimized == "grep test | sort"
    
    def test_optimization_stats(self):
        """Test that optimization stats are tracked."""
        ast = self.parse_command("echo hello | cat")
        optimizer = OptimizationVisitor()
        optimizer.visit(ast)
        stats = optimizer.get_optimization_stats()
        assert stats['optimizations_applied'] == 1
    
    def test_nested_optimization(self):
        """Test optimization in nested structures."""
        original = """
        if true; then
            echo test | cat
        fi
        """
        optimized = self.optimize_and_format(original)
        assert optimized == "echo test"
    
    def test_elif_optimization(self):
        """Test optimization with elif chains."""
        original = """
        if false; then
            echo no
        elif true; then
            echo yes
        else
            echo never
        fi
        """
        optimized = self.optimize_and_format(original)
        assert optimized == "echo yes"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])