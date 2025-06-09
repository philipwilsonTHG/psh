"""Integration tests for unified control structures."""

import pytest
from psh.shell import Shell
from psh.state_machine_lexer import tokenize
from psh.parser_refactored import parse


class TestUnifiedIntegration:
    """Test end-to-end execution with unified types."""
    
    def test_while_loop_statement_integration(self, shell):
        """Test parsing and executing while loop as statement."""
        # Enable unified types
        shell.state.set_variable('i', '0')
        
        code = "while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done"
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=True)
        
        # Execute
        status = shell.execute_toplevel(ast)
        assert status == 0
        assert shell.state.get_variable('i') == '3'
    
    def test_for_loop_statement_integration(self, shell):
        """Test parsing and executing for loop as statement."""
        code = "for i in a b c; do echo $i; done"
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=True)
        
        # Execute
        status = shell.execute_toplevel(ast)
        assert status == 0
    
    def test_while_loop_pipeline_integration(self, shell):
        """Test parsing and executing while loop in pipeline."""
        code = "echo -e '1\\n2\\n3' | while read n; do echo \"Number: $n\"; done"
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=True)
        
        # Execute - pipeline returns CommandList
        status = shell.execute_command_list(ast)
        assert status == 0
    
    def test_for_loop_pipeline_integration(self, shell):
        """Test parsing and executing for loop in pipeline."""
        code = "echo '1 2 3' | for i in $(cat); do echo \"Item: $i\"; done"
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=True)
        
        # Execute  
        status = shell.execute_command_list(ast)
        assert status == 0
    
    def test_mixed_old_new_types(self, shell):
        """Test that old parser still works."""
        # Without unified types
        code = "while true; do echo 'test'; break; done"
        tokens = tokenize(code)
        ast = parse(tokens, use_unified_types=False)  # Default
        
        status = shell.execute_toplevel(ast)
        assert status == 0