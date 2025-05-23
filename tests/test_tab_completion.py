#!/usr/bin/env python3
"""Tests for tab completion functionality."""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tab_completion import CompletionEngine, LineEditor


class TestCompletionEngine:
    """Test the completion engine."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = CompletionEngine()
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create test file structure
        os.makedirs("dir1/subdir")
        os.makedirs("dir2")
        Path("file1.txt").touch()
        Path("file2.py").touch()
        Path("file with spaces.txt").touch()
        Path(".hidden_file").touch()
        Path("dir1/file_in_dir1.txt").touch()
        Path("dir1/subdir/nested.txt").touch()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_simple_file_completion(self):
        """Test basic file completion."""
        completions = self.engine._get_path_completions("fi")
        assert sorted(completions) == ["file with spaces.txt", "file1.txt", "file2.py"]
    
    def test_directory_completion(self):
        """Test directory completion adds trailing slash."""
        completions = self.engine._get_path_completions("dir")
        assert sorted(completions) == ["dir1/", "dir2/"]
    
    def test_hidden_file_completion(self):
        """Test hidden files are only shown when explicitly requested."""
        # Should not show hidden files by default
        completions = self.engine._get_path_completions("")
        assert ".hidden_file" not in completions
        
        # Should show hidden files when prefix starts with dot
        completions = self.engine._get_path_completions(".")
        assert ".hidden_file" in completions
    
    def test_path_with_directory(self):
        """Test completion with directory path."""
        completions = self.engine._get_path_completions("dir1/")
        assert sorted(completions) == ["dir1/file_in_dir1.txt", "dir1/subdir/"]
    
    def test_nested_path_completion(self):
        """Test completion in nested directories."""
        completions = self.engine._get_path_completions("dir1/subdir/")
        assert completions == ["dir1/subdir/nested.txt"]
    
    def test_no_matches(self):
        """Test when no files match."""
        completions = self.engine._get_path_completions("xyz")
        assert completions == []
    
    def test_common_prefix(self):
        """Test finding common prefix among completions."""
        # All start with "file"
        candidates = ["file1.txt", "file2.py", "file with spaces.txt"]
        prefix = self.engine.find_common_prefix(candidates)
        assert prefix == "file"
        
        # No common prefix
        candidates = ["abc", "xyz"]
        prefix = self.engine.find_common_prefix(candidates)
        assert prefix == ""
        
        # Single candidate
        candidates = ["single.txt"]
        prefix = self.engine.find_common_prefix(candidates)
        assert prefix == "single.txt"
    
    def test_escape_path(self):
        """Test escaping special characters in paths."""
        # Test various special characters
        assert self.engine.escape_path("file with spaces.txt") == r"file\ with\ spaces.txt"
        assert self.engine.escape_path("file&name") == r"file\&name"
        assert self.engine.escape_path("file(1).txt") == r"file\(1\).txt"
        assert self.engine.escape_path("file$var.txt") == r"file\$var.txt"
        assert self.engine.escape_path("file'quotes'.txt") == r"file\'quotes\'.txt"
    
    def test_find_word_start(self):
        """Test finding the start of the current word."""
        # Simple case
        line = "cat file"
        assert self.engine._find_word_start(line, 8) == 4
        
        # With multiple words
        line = "cat dir1/file"
        assert self.engine._find_word_start(line, 13) == 4
        
        # At beginning
        line = "file"
        assert self.engine._find_word_start(line, 4) == 0
        
        # After pipe
        line = "ls | cat fi"
        assert self.engine._find_word_start(line, 11) == 9
        
        # In quotes
        line = 'cat "file with'
        assert self.engine._find_word_start(line, 14) == 5  # After opening quote
    
    def test_absolute_path_completion(self):
        """Test completion with absolute paths."""
        # Create a file in /tmp for testing
        test_file = "/tmp/psh_test_file.txt"
        Path(test_file).touch()
        
        try:
            completions = self.engine._get_path_completions("/tmp/psh_test_")
            assert test_file in completions
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_home_directory_expansion(self):
        """Test tilde expansion in paths."""
        # This is tricky to test without affecting user's home
        # Just verify the expansion happens
        home = os.path.expanduser("~")
        completions = self.engine._get_path_completions("~/")
        
        # Should return paths starting with ~/
        for completion in completions:
            assert completion.startswith("~/")


def test_completion_integration():
    """Test that tab completion integrates properly."""
    # This is hard to test without a real terminal
    # Just verify the classes can be instantiated
    engine = CompletionEngine()
    editor = LineEditor()
    
    # Test that methods exist and are callable
    assert hasattr(editor, 'read_line')
    assert hasattr(engine, 'get_completions')
    
    # Test escape sequence handling
    assert editor.CTRL_C == '\x03'
    assert editor.TAB == '\t'
    assert editor.ENTER == '\r'


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])