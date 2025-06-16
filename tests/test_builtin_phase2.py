"""Tests for Phase 2 migrated builtins."""

import pytest
import os
from psh.shell import Shell
from psh.builtins import registry


class TestPhase2Builtins:
    """Test Phase 2 migrated builtins."""
    
    def test_registry_has_phase2_builtins(self):
        """Test that phase 2 builtins are registered."""
        phase2_builtins = [
            'history', 'version', 'env', 'export', 
            'set', 'unset', 'alias', 'unalias'
        ]
        for name in phase2_builtins:
            assert registry.has(name), f"{name} not registered"
    
    def test_history_builtin(self, capsys):
        """Test history builtin."""
        shell = Shell()
        # Add some commands to history
        shell._add_to_history("echo test1")
        shell._add_to_history("echo test2")
        shell._add_to_history("echo test3")
        
        # Test default (last 10)
        shell.run_command("history")
        captured = capsys.readouterr()
        assert "echo test3" in captured.out
        
        # Test with count (note: the history command itself gets added)
        shell.run_command("history 2")
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert len(lines) == 2
        # The last two commands should be "history" and "history 2"
        assert "history" in captured.out
    
    def test_version_builtin(self, capsys):
        """Test version builtin."""
        shell = Shell()
        # Test full version
        shell.run_command("version")
        captured = capsys.readouterr()
        assert "Python Shell (psh)" in captured.out
        
        # Test short version
        shell.run_command("version --short")
        captured = capsys.readouterr()
        # Should be just version number like "0.19.3"
        assert captured.out.strip().count('.') >= 2  # Major.minor.patch
    
    def test_env_builtin(self, capsys):
        """Test env builtin."""
        shell = Shell()
        # Set a test variable
        shell.env['TEST_ENV_VAR'] = 'test_value'
        
        # Test env display
        shell.run_command("env")
        captured = capsys.readouterr()
        assert "TEST_ENV_VAR=test_value" in captured.out
    
    def test_export_builtin(self, capsys):
        """Test export builtin."""
        shell = Shell()
        # Test export with assignment
        shell.run_command("export TEST_EXPORT=value123")
        assert shell.env.get('TEST_EXPORT') == 'value123'
        assert shell.state.get_variable('TEST_EXPORT') == 'value123'
        
        # Test export existing variable
        shell.state.set_variable('EXISTING_VAR', 'existing_value')
        shell.run_command("export EXISTING_VAR")
        assert shell.env.get('EXISTING_VAR') == 'existing_value'
        
        # Test listing exports
        shell.run_command("export")
        captured = capsys.readouterr()
        assert 'export TEST_EXPORT="value123"' in captured.out
    
    def test_set_builtin(self, capsys):
        """Test set builtin."""
        shell = Shell()
        # Test setting positional parameters
        shell.run_command("set arg1 arg2 arg3")
        assert shell.positional_params == ['arg1', 'arg2', 'arg3']
        
        # Test displaying variables
        shell.state.set_variable('MY_VAR', 'my_value')
        shell.run_command("set")
        captured = capsys.readouterr()
        assert "MY_VAR=my_value" in captured.out
        assert "edit_mode=" in captured.out
        
        # Test set -o
        shell.run_command("set -o vi")
        assert shell.edit_mode == 'vi'
        captured = capsys.readouterr()
        assert "Edit mode set to vi" in captured.out
    
    def test_unset_builtin(self):
        """Test unset builtin."""
        shell = Shell()
        # Set variables
        shell.state.set_variable('VAR1', 'value1')
        shell.env['VAR1'] = 'value1'
        shell.state.set_variable('VAR2', 'value2')
        
        # Unset VAR1
        shell.run_command("unset VAR1")
        assert not shell.state.scope_manager.has_variable('VAR1')
        assert 'VAR1' not in shell.env
        assert shell.state.scope_manager.has_variable('VAR2')  # VAR2 should still exist
        
        # Test unset with -f flag (functions)
        shell.function_manager.define_function('test_func', None)
        exit_code = shell.run_command("unset -f test_func")
        assert exit_code == 0
        assert shell.function_manager.get_function('test_func') is None
    
    def test_alias_builtin(self, capsys):
        """Test alias builtin."""
        shell = Shell()
        # Define an alias
        shell.run_command("alias ll='ls -la'")
        assert shell.alias_manager.get_alias('ll') == 'ls -la'
        
        # Display specific alias
        shell.run_command("alias ll")
        captured = capsys.readouterr()
        assert "alias ll='ls -la'" in captured.out
        
        # Define alias with quotes
        shell.run_command('alias grep="grep --color=auto"')
        assert shell.alias_manager.get_alias('grep') == 'grep --color=auto'
        
        # List all aliases
        shell.run_command("alias")
        captured = capsys.readouterr()
        assert "alias ll='ls -la'" in captured.out
        assert "alias grep='grep --color=auto'" in captured.out
    
    def test_unalias_builtin(self, capsys):
        """Test unalias builtin."""
        shell = Shell()
        # Create some aliases
        shell.alias_manager.define_alias('ll', 'ls -la')
        shell.alias_manager.define_alias('la', 'ls -a')
        
        # Remove one alias
        exit_code = shell.run_command("unalias ll")
        assert exit_code == 0
        assert shell.alias_manager.get_alias('ll') is None
        assert shell.alias_manager.get_alias('la') == 'ls -a'
        
        # Try to remove non-existent alias
        exit_code = shell.run_command("unalias nonexistent")
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err
        
        # Remove all aliases
        shell.run_command("unalias -a")
        assert len(shell.alias_manager.list_aliases()) == 0