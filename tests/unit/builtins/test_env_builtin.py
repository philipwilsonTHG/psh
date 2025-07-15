"""
Tests for the env builtin command.

Tests environment variable display and export/env synchronization.
"""

import pytest
import os
from pathlib import Path


class TestEnvBuiltin:
    """Test the env builtin functionality."""
    
    def test_env_shows_environment(self, shell, clean_env):
        """Test that env displays environment variables."""
        # Export a test variable through the shell
        result = shell.run_command('export TEST_ENV_VAR=test_value')
        assert result == 0
        
        # Run env and capture output
        result = shell.run_command('env > /tmp/env_output.txt')
        assert result == 0
        
        # Check output contains our variable
        with open('/tmp/env_output.txt', 'r') as f:
            output = f.read()
        assert 'TEST_ENV_VAR=test_value' in output
        
        # Clean up
        os.unlink('/tmp/env_output.txt')
    
    def test_export_env_sync(self, shell):
        """Test that exported variables appear in env output."""
        # Export a variable
        result = shell.run_command('export SYNC_TEST=synchronized')
        assert result == 0
        
        # Check env shows it
        result = shell.run_command('env > /tmp/sync_test.txt')
        assert result == 0
        
        with open('/tmp/sync_test.txt', 'r') as f:
            output = f.read()
        assert 'SYNC_TEST=synchronized' in output
        
        # Clean up
        os.unlink('/tmp/sync_test.txt')
    
    def test_env_in_pipeline(self, shell):
        """Test that env works correctly in pipelines."""
        # Export variables
        shell.run_command('export PIPE_VAR1=value1')
        shell.run_command('export PIPE_VAR2=value2')
        
        # Test in pipeline
        result = shell.run_command('env | /usr/bin/grep PIPE_VAR > /tmp/pipe_test.txt')
        assert result == 0
        
        with open('/tmp/pipe_test.txt', 'r') as f:
            output = f.read()
        assert 'PIPE_VAR1=value1' in output
        assert 'PIPE_VAR2=value2' in output
        
        # Clean up
        os.unlink('/tmp/pipe_test.txt')
    
    def test_env_external_command_compatibility(self, shell):
        """Test that exported variables are visible to external commands."""
        # Export a variable
        shell.run_command('export EXTERNAL_VAR=visible')
        
        # Use external env command
        result = shell.run_command('/usr/bin/env | /usr/bin/grep EXTERNAL_VAR > /tmp/external_test.txt')
        assert result == 0
        
        with open('/tmp/external_test.txt', 'r') as f:
            output = f.read()
        assert 'EXTERNAL_VAR=visible' in output
        
        # Clean up
        os.unlink('/tmp/external_test.txt')
    
    def test_env_builtin_priority(self, shell):
        """Test that env builtin is used instead of external command."""
        # This is a bit tricky to test directly, but we can check behavior
        # The builtin should work even if PATH is empty
        result = shell.run_command('PATH="" env > /dev/null')
        assert result == 0  # Should succeed with builtin
    
    def test_export_without_value(self, shell):
        """Test exporting existing variable."""
        # Set variable without export
        shell.run_command('NO_EXPORT_YET=test')
        
        # Variable shouldn't be in env yet
        # Use grep -c which always returns 0, and check the count
        shell.run_command('env | /usr/bin/grep -c NO_EXPORT_YET > /tmp/count1.txt || echo "0" > /tmp/count1.txt')
        with open('/tmp/count1.txt', 'r') as f:
            assert f.read().strip() == '0'
        
        # Export it
        shell.run_command('export NO_EXPORT_YET')
        
        # Now it should be in env
        result = shell.run_command('env | /usr/bin/grep NO_EXPORT_YET > /tmp/export_test.txt')
        assert result == 0
        with open('/tmp/export_test.txt', 'r') as f:
            assert 'NO_EXPORT_YET=test' in f.read()
        
        # Clean up
        os.unlink('/tmp/count1.txt')
        os.unlink('/tmp/export_test.txt')
    
    def test_multiple_exports(self, shell):
        """Test multiple variables exported at once."""
        # Export multiple variables
        result = shell.run_command('export A=1 B=2 C=3')
        assert result == 0
        
        # Check all are in env
        result = shell.run_command('env | /usr/bin/grep -E "^[ABC]=" | /usr/bin/sort > /tmp/multi_test.txt')
        assert result == 0
        
        with open('/tmp/multi_test.txt', 'r') as f:
            output = f.read()
        assert 'A=1\n' in output
        assert 'B=2\n' in output
        assert 'C=3\n' in output
        
        # Clean up
        os.unlink('/tmp/multi_test.txt')


@pytest.fixture
def clean_env():
    """Fixture to clean up test environment variables."""
    # Store original env
    original_env = os.environ.copy()
    yield
    # Restore original env
    for key in list(os.environ.keys()):
        if key not in original_env:
            del os.environ[key]
    for key, value in original_env.items():
        os.environ[key] = value