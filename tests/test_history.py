import pytest
import os
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock
from psh.shell import Shell


class TestHistory:
    def setup_method(self):
        # Use a temporary history file
        self.temp_history = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_history.close()
        
        # Patch the history file path before creating Shell
        # This prevents loading the user's real history
        with patch.dict(os.environ, {'HOME': os.path.dirname(self.temp_history.name)}):
            self.shell = Shell()
            self.shell.history_file = self.temp_history.name
            self.shell.history = []  # Clear any loaded history
    
    def teardown_method(self):
        # Clean up temporary file
        try:
            os.unlink(self.temp_history.name)
        except:
            pass
    
    def test_add_to_history(self):
        """Test adding commands to history"""
        self.shell._add_to_history("echo hello")
        assert self.shell.history == ["echo hello"]
        
        self.shell._add_to_history("ls -la")
        assert self.shell.history == ["echo hello", "ls -la"]
    
    def test_no_duplicate_consecutive_commands(self):
        """Test that consecutive duplicates are not added"""
        self.shell._add_to_history("echo hello")
        self.shell._add_to_history("echo hello")
        assert self.shell.history == ["echo hello"]
        
        self.shell._add_to_history("ls")
        self.shell._add_to_history("echo hello")
        assert self.shell.history == ["echo hello", "ls", "echo hello"]
    
    def test_history_max_size(self):
        """Test that history respects max size"""
        self.shell.max_history_size = 5
        
        for i in range(10):
            self.shell._add_to_history(f"command {i}")
        
        assert len(self.shell.history) == 5
        assert self.shell.history == [
            "command 5",
            "command 6", 
            "command 7",
            "command 8",
            "command 9"
        ]
    
    def test_history_builtin_default(self):
        """Test history built-in with default count"""
        # Add some commands
        for i in range(15):
            self.shell._add_to_history(f"command {i}")
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell._builtin_history(['history'])
            assert exit_code == 0
            
            output = mock_stdout.getvalue()
            lines = output.strip().split('\n')
            assert len(lines) == 10  # Default shows last 10
            
            # Check format and content
            assert "   11  command 10" in output
            assert "   15  command 14" in output
    
    def test_history_builtin_with_count(self):
        """Test history built-in with specific count"""
        for i in range(5):
            self.shell._add_to_history(f"cmd {i}")
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            exit_code = self.shell._builtin_history(['history', '3'])
            assert exit_code == 0
            
            output = mock_stdout.getvalue()
            lines = output.strip().split('\n')
            assert len(lines) == 3
            assert "cmd 2" in output
            assert "cmd 3" in output
            assert "cmd 4" in output
    
    def test_history_builtin_invalid_arg(self):
        """Test history built-in with invalid argument"""
        with patch('sys.stderr', new=StringIO()) as mock_stderr:
            exit_code = self.shell._builtin_history(['history', 'abc'])
            assert exit_code == 1
            assert "numeric argument required" in mock_stderr.getvalue()
    
    def test_run_command_adds_to_history(self):
        """Test that run_command adds to history"""
        with patch('sys.stdout', new=StringIO()):
            self.shell.run_command("echo test")
            assert "echo test" in self.shell.history
            
            self.shell.run_command("pwd")
            assert "pwd" in self.shell.history
    
    def test_empty_command_not_added_to_history(self):
        """Test that empty commands are not added to history"""
        self.shell.run_command("")
        assert len(self.shell.history) == 0
        
        self.shell.run_command("   ")
        assert len(self.shell.history) == 0
    
    def test_source_commands_not_added_to_history(self):
        """Test that commands from source files are not added to history"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.psh', delete=False) as f:
            f.write("echo sourced1\n")
            f.write("echo sourced2\n")
            script_path = f.name
        
        try:
            with patch('sys.stdout', new=StringIO()):
                self.shell.run_command(f"source {script_path}")
            
            # Only the source command should be in history
            assert self.shell.history == [f"source {script_path}"]
            assert "echo sourced1" not in self.shell.history
            assert "echo sourced2" not in self.shell.history
        finally:
            os.unlink(script_path)
    
    def test_save_and_load_history(self):
        """Test saving and loading history from file"""
        # Add some commands
        commands = ["echo hello", "ls -la", "pwd"]
        for cmd in commands:
            self.shell._add_to_history(cmd)
        
        # Save history
        self.shell._save_history()
        
        # Create new shell with patched HOME to avoid loading user's history
        with patch.dict(os.environ, {'HOME': os.path.dirname(self.temp_history.name)}):
            new_shell = Shell()
            new_shell.history_file = self.temp_history.name
            new_shell.history = []  # Clear any default history
            new_shell._load_history()
        
        assert new_shell.history == commands
    
    def test_load_history_trims_to_max_size(self):
        """Test that loading history respects max size"""
        # Write a large history file
        with open(self.temp_history.name, 'w') as f:
            for i in range(2000):
                f.write(f"command {i}\n")
        
        # Load with max size limit
        self.shell.max_history_size = 100
        self.shell._load_history()
        
        assert len(self.shell.history) == 100
        assert self.shell.history[0] == "command 1900"
        assert self.shell.history[-1] == "command 1999"
    
    def test_history_file_errors_handled_silently(self):
        """Test that history file errors don't crash the shell"""
        # Non-existent directory
        self.shell.history_file = "/nonexistent/directory/history"
        
        # These should not raise exceptions
        self.shell._load_history()
        self.shell._save_history()
        
        # Read-only file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            readonly_file = f.name
        
        try:
            os.chmod(readonly_file, 0o444)  # Read-only
            self.shell.history_file = readonly_file
            self.shell._save_history()  # Should not crash
        finally:
            os.chmod(readonly_file, 0o644)  # Restore permissions
            os.unlink(readonly_file)