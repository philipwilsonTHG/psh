"""
Test compatibility between legacy and visitor executors.

This test ensures both executors produce identical results.
"""

import pytest
import os
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser import parse


class TestExecutorCompatibility:
    """Test that both executors produce identical results."""
    
    def run_with_executor(self, command, use_visitor=False):
        """Run command with specified executor and capture output."""
        # Create shell with specified executor
        shell = Shell(use_visitor_executor=use_visitor)
        
        # Capture output
        stdout = StringIO()
        stderr = StringIO()
        
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Parse command once
            tokens = tokenize(command)
            ast = parse(tokens)
            
            # Execute
            exit_code = shell.execute(ast)
        
        return {
            'exit_code': exit_code,
            'stdout': stdout.getvalue(),
            'stderr': stderr.getvalue(),
            'variables': dict(shell.variables),
            'last_exit_code': shell.last_exit_code
        }
    
    def assert_identical_results(self, command):
        """Assert that both executors produce identical results."""
        legacy_result = self.run_with_executor(command, use_visitor=False)
        visitor_result = self.run_with_executor(command, use_visitor=True)
        
        # Compare results
        assert legacy_result['exit_code'] == visitor_result['exit_code'], \
            f"Exit codes differ: legacy={legacy_result['exit_code']}, visitor={visitor_result['exit_code']}"
        
        assert legacy_result['stdout'] == visitor_result['stdout'], \
            f"Stdout differs:\nLegacy: {repr(legacy_result['stdout'])}\nVisitor: {repr(visitor_result['stdout'])}"
        
        assert legacy_result['stderr'] == visitor_result['stderr'], \
            f"Stderr differs:\nLegacy: {repr(legacy_result['stderr'])}\nVisitor: {repr(visitor_result['stderr'])}"
        
        assert legacy_result['last_exit_code'] == visitor_result['last_exit_code'], \
            f"Last exit codes differ: legacy={legacy_result['last_exit_code']}, visitor={visitor_result['last_exit_code']}"
    
    def test_simple_commands(self):
        """Test simple command execution."""
        self.assert_identical_results('echo hello')
        self.assert_identical_results('echo $HOME')
        self.assert_identical_results('VAR=value; echo $VAR')
    
    def test_pipelines(self):
        """Test pipeline execution."""
        self.assert_identical_results('echo hello | cat')
        self.assert_identical_results('echo one; echo two | cat')
    
    def test_control_structures(self):
        """Test control structure execution."""
        self.assert_identical_results('if true; then echo yes; fi')
        self.assert_identical_results('for i in 1 2 3; do echo $i; done')
        self.assert_identical_results('i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done')
    
    def test_functions(self):
        """Test function definition and execution."""
        self.assert_identical_results('foo() { echo hello; }; foo')
        self.assert_identical_results('function bar { return 42; }; bar; echo $?')
    
    def test_arithmetic(self):
        """Test arithmetic evaluation."""
        self.assert_identical_results('echo $((2 + 2))')
        self.assert_identical_results('((x = 5)); echo $x')
        self.assert_identical_results('for ((i=0; i<3; i++)); do echo $i; done')
    
    def test_expansions(self):
        """Test various expansions."""
        self.assert_identical_results('echo ${HOME:-/tmp}')
        self.assert_identical_results('X=hello; echo ${#X}')
        self.assert_identical_results('Y=foobar; echo ${Y/foo/bar}')
    
    @pytest.mark.parametrize('command', [
        'true',
        'false',
        'exit 0',
        'exit 1',
        'exit 42',
    ])
    def test_exit_codes(self, command):
        """Test that exit codes match."""
        # Note: We can't use assert_identical_results for exit commands
        # because they terminate the shell
        legacy_shell = Shell(use_visitor_executor=False)
        visitor_shell = Shell(use_visitor_executor=True)
        
        # Parse command
        tokens = tokenize(command)
        ast = parse(tokens)
        
        # Execute and compare exit codes
        try:
            legacy_exit = legacy_shell.execute(ast)
        except SystemExit as e:
            legacy_exit = e.code if e.code is not None else 0
            
        try:
            visitor_exit = visitor_shell.execute(ast)
        except SystemExit as e:
            visitor_exit = e.code if e.code is not None else 0
        
        assert legacy_exit == visitor_exit


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
