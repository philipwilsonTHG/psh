#!/usr/bin/env python3
"""Basic integration tests for parser combinator features.

This module provides a simplified set of tests that verify what the
parser combinator actually supports, without assuming features that
aren't implemented.
"""

import pytest
from psh.lexer import tokenize
from psh.parser.combinators.parser import ParserCombinatorShellParser
from psh.ast_nodes import (
    SimpleCommand, Pipeline, CommandList, Redirect, AndOrList,
    IfConditional, WhileLoop, ForLoop, CaseConditional, FunctionDef
)


class TestParserCombinatorBasics:
    """Basic tests for parser combinator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ParserCombinatorShellParser()
    
    def parse(self, command: str):
        """Helper to parse a command string."""
        tokens = tokenize(command)
        return self.parser.parse(tokens)
    
    def parse_no_exception(self, command: str) -> bool:
        """Parse and return whether it succeeded."""
        try:
            self.parse(command)
            return True
        except Exception:
            return False


class TestBasicRedirection(TestParserCombinatorBasics):
    """Test basic I/O redirection support."""
    
    def test_output_redirect(self):
        """Test: echo hello > file.txt"""
        ast = self.parse("echo hello > file.txt")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == "echo"
        assert cmd.args[1] == "hello"
        
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == '>'
        assert cmd.redirects[0].target == "file.txt"
    
    def test_input_redirect(self):
        """Test: cat < file.txt"""
        ast = self.parse("cat < file.txt")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 1
        assert cmd.args[0] == "cat"
        
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == '<'
        assert cmd.redirects[0].target == "file.txt"
    
    def test_append_redirect(self):
        """Test: echo data >> log.txt"""
        ast = self.parse("echo data >> log.txt")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == '>>'
        assert cmd.redirects[0].target == "log.txt"


class TestBasicPipelines(TestParserCombinatorBasics):
    """Test pipeline support."""
    
    def test_simple_pipeline(self):
        """Test: ls | grep txt"""
        ast = self.parse("ls | grep txt")
        pipeline = ast.statements[0].pipelines[0]
        
        assert isinstance(pipeline, Pipeline)
        assert len(pipeline.commands) == 2
        
        assert pipeline.commands[0].args == ["ls"]
        assert pipeline.commands[1].args == ["grep", "txt"]
    
    def test_three_stage_pipeline(self):
        """Test: cat file | sort | uniq"""
        ast = self.parse("cat file | sort | uniq")
        pipeline = ast.statements[0].pipelines[0]
        
        assert len(pipeline.commands) == 3
        assert pipeline.commands[0].args == ["cat", "file"]
        assert pipeline.commands[1].args == ["sort"]
        assert pipeline.commands[2].args == ["uniq"]


class TestControlStructures(TestParserCombinatorBasics):
    """Test control structure support."""
    
    def test_if_statement(self):
        """Test: if true; then echo yes; fi"""
        ast = self.parse("if true; then echo yes; fi")
        # With unwrapping fix, if statement is directly in statements
        if_stmt = ast.statements[0]
        assert isinstance(if_stmt, IfConditional)
        # Condition
        assert if_stmt.condition.statements[0].pipelines[0].commands[0].args == ["true"]
        # Then block
        assert if_stmt.then_part.statements[0].pipelines[0].commands[0].args == ["echo", "yes"]
    
    def test_while_loop(self):
        """Test: while test -f lock; do sleep 1; done"""
        ast = self.parse("while test -f lock; do sleep 1; done")
        # With unwrapping fix, while loop is directly in statements
        while_loop = ast.statements[0]
        assert isinstance(while_loop, WhileLoop)
        # Condition
        cond_cmd = while_loop.condition.statements[0].pipelines[0].commands[0]
        assert cond_cmd.args == ["test", "-f", "lock"]
        # Body
        body_cmd = while_loop.body.statements[0].pipelines[0].commands[0]
        assert body_cmd.args == ["sleep", "1"]
    
    def test_for_loop(self):
        """Test: for i in a b c; do echo $i; done"""
        ast = self.parse("for i in a b c; do echo $i; done")
        # With unwrapping fix, for loop is directly in statements
        for_loop = ast.statements[0]
        assert isinstance(for_loop, ForLoop)
        assert for_loop.variable == "i"
        assert for_loop.items == ["a", "b", "c"]
        # Body
        body_cmd = for_loop.body.statements[0].pipelines[0].commands[0]
        assert body_cmd.args == ["echo", "$i"]
    
    def test_case_statement(self):
        """Test: case $x in a) echo A;; b) echo B;; esac"""
        ast = self.parse("case $x in a) echo A;; b) echo B;; esac")
        # With unwrapping fix, case statement is directly in statements
        case_stmt = ast.statements[0]
        assert isinstance(case_stmt, CaseConditional)
        assert case_stmt.expr == "$x"
        assert len(case_stmt.items) == 2
        
        # First case
        assert case_stmt.items[0].patterns[0].pattern == "a"
        assert case_stmt.items[0].commands.statements[0].pipelines[0].commands[0].args == ["echo", "A"]
        
        # Second case
        assert case_stmt.items[1].patterns[0].pattern == "b"
        assert case_stmt.items[1].commands.statements[0].pipelines[0].commands[0].args == ["echo", "B"]


class TestFunctions(TestParserCombinatorBasics):
    """Test function definition support."""
    
    def test_simple_function(self):
        """Test: foo() { echo hello; }"""
        ast = self.parse("foo() { echo hello; }")
        func = ast.statements[0]
        
        assert isinstance(func, FunctionDef)
        assert func.name == "foo"
        # Body
        body_cmd = func.body.statements[0].pipelines[0].commands[0]
        assert body_cmd.args == ["echo", "hello"]
    
    def test_function_with_multiple_commands(self):
        """Test: bar() { echo start; sleep 1; echo done; }"""
        ast = self.parse("bar() { echo start; sleep 1; echo done; }")
        func = ast.statements[0]
        
        assert isinstance(func, FunctionDef)
        assert func.name == "bar"
        assert len(func.body.statements) == 3


class TestAndOrLists(TestParserCombinatorBasics):
    """Test && and || operators."""
    
    def test_and_operator(self):
        """Test: cmd1 && cmd2"""
        ast = self.parse("cmd1 && cmd2")
        and_or = ast.statements[0]
        
        assert isinstance(and_or, AndOrList)
        assert len(and_or.pipelines) == 2
        assert and_or.operators == ["&&"]
        
        assert and_or.pipelines[0].commands[0].args == ["cmd1"]
        assert and_or.pipelines[1].commands[0].args == ["cmd2"]
    
    def test_or_operator(self):
        """Test: cmd1 || cmd2"""
        ast = self.parse("cmd1 || cmd2")
        and_or = ast.statements[0]
        
        assert isinstance(and_or, AndOrList)
        assert len(and_or.pipelines) == 2
        assert and_or.operators == ["||"]
    
    def test_mixed_and_or(self):
        """Test: cmd1 && cmd2 || cmd3"""
        ast = self.parse("cmd1 && cmd2 || cmd3")
        and_or = ast.statements[0]
        
        assert len(and_or.pipelines) == 3
        assert and_or.operators == ["&&", "||"]


class TestVariableHandling(TestParserCombinatorBasics):
    """Test how variables and assignments are handled."""
    
    def test_simple_assignment_parsing(self):
        """Test: VAR=value"""
        ast = self.parse("VAR=value")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        # Parser treats this as a command with one arg
        assert len(cmd.args) == 1
        assert cmd.args[0] == "VAR=value"
    
    def test_assignment_with_command(self):
        """Test: VAR=value command"""
        ast = self.parse("VAR=value command")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        # Parser treats these as two args
        assert len(cmd.args) == 2
        assert cmd.args[0] == "VAR=value"
        assert cmd.args[1] == "command"
    
    def test_export_command(self):
        """Test: export VAR=value"""
        ast = self.parse("export VAR=value")
        cmd = ast.statements[0].pipelines[0].commands[0]
        
        assert len(cmd.args) == 2
        assert cmd.args[0] == "export"
        assert cmd.args[1] == "VAR=value"


class TestUnsupportedFeatures(TestParserCombinatorBasics):
    """Document what features are NOT supported."""
    
    def test_heredoc_now_supported(self):
        """Test that heredocs are now supported."""
        result = self.parse("cat << EOF")
        cmd = result.statements[0].pipelines[0].commands[0]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "<<"
        assert cmd.redirects[0].target == "EOF"
    
    def test_background_job_supported(self):
        """Test that background jobs are now supported."""
        result = self.parse("command &")
        cmd = result.statements[0].pipelines[0].commands[0]
        assert cmd.background is True
    
    def test_subshell_now_supported(self):
        """Test that subshells are now supported (Phase 2 complete)."""
        assert self.parse_no_exception("(echo hello)")
        # Test that parsing actually works and produces correct AST
        ast = self.parse("(echo hello)")
        from psh.ast_nodes import SubshellGroup
        # With unwrapping fix, subshell is directly in statements
        subshell = ast.statements[0]
        assert isinstance(subshell, SubshellGroup)
    
    def test_brace_group_now_supported(self):
        """Test that brace groups are now supported (Phase 2 complete)."""
        assert self.parse_no_exception("{ echo hello; }")
        # Test that parsing actually works and produces correct AST
        ast = self.parse("{ echo hello; }")
        from psh.ast_nodes import BraceGroup
        # With unwrapping fix, brace group is directly in statements
        brace_group = ast.statements[0]
        assert isinstance(brace_group, BraceGroup)
    
    def test_arithmetic_command_now_supported(self):
        """Test that arithmetic commands are now supported."""
        # First check that parsing succeeds
        assert self.parse_no_exception("((x = 5))")
        
        # Then get the actual AST to verify structure
        ast = self.parse("((x = 5))")
        from psh.ast_nodes import ArithmeticEvaluation
        # With unwrapping fix, arithmetic command is directly in statements
        arith_cmd = ast.statements[0]
        assert isinstance(arith_cmd, ArithmeticEvaluation)
        assert arith_cmd.expression == "x = 5"
    
    def test_array_initialization_now_supported(self):
        """Test that array initialization is now supported (Phase 5 complete)."""
        assert self.parse_no_exception("arr=(1 2 3)")
        
        # Verify the AST structure
        ast = self.parse("arr=(1 2 3)")
        from psh.ast_nodes import ArrayInitialization
        array_init = ast.statements[0].pipelines[0]
        assert isinstance(array_init, ArrayInitialization)
        assert array_init.name == "arr"
        assert array_init.elements == ["1", "2", "3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])