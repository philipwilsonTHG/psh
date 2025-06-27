import pytest
import tempfile
import os
from psh.shell import Shell
from psh.lexer import tokenize
from psh.token_types import TokenType
from psh.parser import parse


class TestConditionalExecution:
    def setup_method(self):
        self.shell = Shell()
    def test_tokenize_and_and(self):
        """Test tokenization of && operator"""
        tokens = tokenize("true && echo hello")
        assert len(tokens) == 5  # true, &&, echo, hello, EOF
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "true"
        assert tokens[1].type == TokenType.AND_AND
        assert tokens[1].value == "&&"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "echo"
    
    def test_tokenize_or_or(self):
        """Test tokenization of || operator"""
        tokens = tokenize("false || echo fallback")
        assert len(tokens) == 5  # false, ||, echo, fallback, EOF
        assert tokens[0].type == TokenType.WORD
        assert tokens[0].value == "false"
        assert tokens[1].type == TokenType.OR_OR
        assert tokens[1].value == "||"
        assert tokens[2].type == TokenType.WORD
        assert tokens[2].value == "echo"
    
    def test_parse_and_or_list(self):
        """Test parsing of && and || operators"""
        tokens = tokenize("cmd1 && cmd2 || cmd3")
        ast = parse(tokens)
        
        assert len(ast.and_or_lists) == 1
        and_or_list = ast.and_or_lists[0]
        assert len(and_or_list.pipelines) == 3
        assert len(and_or_list.operators) == 2
        assert and_or_list.operators[0] == "&&"
        assert and_or_list.operators[1] == "||"
    
    def test_and_success_execution(self):
        """Test && executes second command when first succeeds"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
        
        try:
            # Should create the file because true succeeds
            exit_code = self.shell.run_command(f"true && echo success > {test_file}")
            assert exit_code == 0
            
            with open(test_file, 'r') as f:
                content = f.read()
            assert content.strip() == "success"
        finally:
            os.unlink(test_file)
    
    def test_and_failure_short_circuit(self):
        """Test && doesn't execute second command when first fails"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
            os.unlink(test_file)  # Delete it so we can check if it's created
        
        # Should not create the file because false fails
        exit_code = self.shell.run_command(f"false && echo should_not_appear > {test_file}")
        assert exit_code == 1
        assert not os.path.exists(test_file)
    
    def test_or_failure_execution(self):
        """Test || executes second command when first fails"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
        
        try:
            # Should create the file because false fails
            exit_code = self.shell.run_command(f"false || echo fallback > {test_file}")
            assert exit_code == 0
            
            with open(test_file, 'r') as f:
                content = f.read()
            assert content.strip() == "fallback"
        finally:
            os.unlink(test_file)
    
    def test_or_success_short_circuit(self):
        """Test || doesn't execute second command when first succeeds"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
            os.unlink(test_file)  # Delete it so we can check if it's created
        
        # Should not create the file because true succeeds
        exit_code = self.shell.run_command(f"true || echo should_not_appear > {test_file}")
        assert exit_code == 0
        assert not os.path.exists(test_file)
    
    def test_complex_chain(self):
        """Test complex chain of && and || operators"""
        # This should execute: false fails, so || runs echo, which succeeds, so && runs the final echo
        exit_code = self.shell.run_command("false || echo middle && echo final")
        assert exit_code == 0
    
    def test_exit_status_propagation(self):
        """Test that exit status is properly propagated through && and ||"""
        # true && false should return 1 (false's exit code)
        exit_code = self.shell.run_command("true && false")
        assert exit_code == 1
        assert self.shell.last_exit_code == 1
        
        # false || true should return 0 (true's exit code)
        exit_code = self.shell.run_command("false || true")
        assert exit_code == 0
        assert self.shell.last_exit_code == 0
        
        # false && true should return 1 (false's exit code, true not executed)
        exit_code = self.shell.run_command("false && true")
        assert exit_code == 1
        assert self.shell.last_exit_code == 1
    
    def test_with_pipelines(self):
        """Test && and || with pipelines"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test line\n")
            test_file = f.name
        
        output_file = "/tmp/conditional_pipeline_test.txt"
        
        try:
            # Pipeline succeeds, so && executes
            exit_code = self.shell.run_command(f"cat {test_file} | grep test && echo found > {output_file}")
            assert exit_code == 0
            
            with open(output_file, 'r') as f:
                content = f.read()
            assert content.strip() == "found"
            
            # Pipeline fails, so || executes
            exit_code = self.shell.run_command(f"cat {test_file} | grep nonexistent || echo notfound > {output_file}")
            assert exit_code == 0
            
            with open(output_file, 'r') as f:
                content = f.read()
            assert content.strip() == "notfound"
        finally:
            os.unlink(test_file)
            if os.path.exists(output_file):
                os.unlink(output_file)
    
    def test_with_semicolon(self):
        """Test && and || interaction with semicolon"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
        
        try:
            # Semicolon should separate and_or_lists
            exit_code = self.shell.run_command(f"false || echo first > {test_file}; echo second >> {test_file}")
            assert exit_code == 0
            
            with open(test_file, 'r') as f:
                lines = f.read().strip().split('\n')
            assert lines[0] == "first"
            assert lines[1] == "second"
        finally:
            os.unlink(test_file)
    
    def test_background_with_conditional(self):
        """Test that && and || work correctly with background commands"""
        # Background command should not affect conditional execution
        exit_code = self.shell.run_command("sleep 0.1 & && echo foreground")
        assert exit_code == 0
    
    def test_builtin_commands(self):
        """Test && and || with builtin commands"""
        # cd to non-existent directory fails
        exit_code = self.shell.run_command("cd /nonexistent/directory && echo should_not_print")
        assert exit_code == 1
        
        # cd to valid directory succeeds
        exit_code = self.shell.run_command("cd / && pwd")
        assert exit_code == 0
    
    def test_newline_after_operator(self):
        """Test that newlines are allowed after && and ||"""
        # Bash allows newlines after && and ||
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_file = f.name
        
        try:
            # Simulate multi-line command
            cmd = f"true &&\necho success > {test_file}"
            exit_code = self.shell.run_command(cmd)
            assert exit_code == 0
            
            with open(test_file, 'r') as f:
                content = f.read()
            assert content.strip() == "success"
        finally:
            os.unlink(test_file)