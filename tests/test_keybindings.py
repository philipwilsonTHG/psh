"""Tests for vi and emacs key bindings."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from psh.line_editor import LineEditor
from psh.keybindings import EditMode
from psh.shell import Shell


@pytest.fixture
def shell():
    """Provide a shell instance for testing."""
    return Shell()


class MockStdin:
    """Mock stdin for testing key input."""
    def __init__(self, inputs):
        self.inputs = list(inputs)
        self.position = 0
    
    def read(self, n=1):
        if self.position >= len(self.inputs):
            return ''
        result = self.inputs[self.position]
        self.position += 1
        return result


class TestEmacsKeyBindings:
    """Test emacs key binding functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.editor = LineEditor(edit_mode='emacs')
        self.stdout_mock = Mock()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_mock
    
    def teardown_method(self):
        """Restore environment."""
        sys.stdout = self.original_stdout
    
    def test_basic_movement(self):
        """Test basic cursor movement keys."""
        # Test Ctrl-A (beginning of line)
        self.editor.buffer = list('hello world')
        self.editor.cursor_pos = 5
        self.editor._execute_action('move_beginning_of_line', '\x01')
        assert self.editor.cursor_pos == 0
        
        # Test Ctrl-E (end of line)
        self.editor._execute_action('move_end_of_line', '\x05')
        assert self.editor.cursor_pos == 11
        
        # Test Ctrl-F (forward char)
        self.editor.cursor_pos = 5
        self.editor._execute_action('move_forward_char', '\x06')
        assert self.editor.cursor_pos == 6
        
        # Test Ctrl-B (backward char)
        self.editor._execute_action('move_backward_char', '\x02')
        assert self.editor.cursor_pos == 5
    
    def test_word_movement(self):
        """Test word-based movement."""
        self.editor.buffer = list('hello world test')
        
        # Test Alt-f (forward word)
        self.editor.cursor_pos = 0
        self.editor._move_word_forward()
        assert self.editor.cursor_pos == 6  # After "hello "
        
        # Test Alt-b (backward word)
        self.editor.cursor_pos = 12  # In "test"
        self.editor._move_word_backward()
        assert self.editor.cursor_pos == 6  # Beginning of "world"
    
    def test_editing_operations(self):
        """Test text editing operations."""
        # Test Ctrl-D (delete char)
        self.editor.buffer = list('hello')
        self.editor.cursor_pos = 2
        self.editor._delete_char()
        assert ''.join(self.editor.buffer) == 'helo'
        
        # Test Ctrl-K (kill to end of line)
        self.editor.buffer = list('hello world')
        self.editor.cursor_pos = 5
        self.editor._kill_line()
        assert ''.join(self.editor.buffer) == 'hello'
        assert self.editor.kill_ring[-1] == ' world'
        
        # Test Ctrl-U (kill whole line)
        self.editor.buffer = list('hello world')
        self.editor.cursor_pos = 5
        self.editor._kill_whole_line()
        assert self.editor.buffer == []
        assert self.editor.kill_ring[-1] == 'hello world'
        
        # Test Ctrl-W (kill word backward)
        self.editor.buffer = list('hello world')
        self.editor.cursor_pos = 11
        self.editor._kill_word_backward()
        assert ''.join(self.editor.buffer) == 'hello '
        assert self.editor.kill_ring[-1] == 'world'
    
    def test_yank_operations(self):
        """Test yank (paste) operations."""
        # Set up kill ring
        self.editor.kill_ring = ['test text']
        self.editor.buffer = list('hello ')
        self.editor.cursor_pos = 6
        
        # Test Ctrl-Y (yank)
        self.editor._yank()
        assert ''.join(self.editor.buffer) == 'hello test text'
        assert self.editor.cursor_pos == 15
    
    def test_transpose_chars(self):
        """Test character transposition."""
        # Test Ctrl-T
        self.editor.buffer = list('hello')
        self.editor.cursor_pos = 3  # After 'l'
        self.editor._transpose_chars()
        assert ''.join(self.editor.buffer) == 'helol'


class TestViKeyBindings:
    """Test vi key binding functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.editor = LineEditor(edit_mode='vi')
        self.stdout_mock = Mock()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_mock
    
    def teardown_method(self):
        """Restore environment."""
        sys.stdout = self.original_stdout
    
    def test_mode_switching(self):
        """Test switching between vi modes."""
        # Should start in insert mode
        assert self.editor.mode == EditMode.VI_INSERT
        
        # Test ESC to normal mode
        self.editor.buffer = list('hello')
        self.editor.cursor_pos = 5
        self.editor._enter_vi_normal_mode()
        assert self.editor.mode == EditMode.VI_NORMAL
        assert self.editor.cursor_pos == 4  # Moves back one
        
        # Test 'i' to insert mode
        self.editor._enter_vi_insert_mode()
        assert self.editor.mode == EditMode.VI_INSERT
    
    def test_vi_movement(self):
        """Test vi movement commands."""
        self.editor.buffer = list('hello world')
        self.editor.mode = EditMode.VI_NORMAL
        
        # Test 'h' (left)
        self.editor.cursor_pos = 5
        self.editor._move_left()
        assert self.editor.cursor_pos == 4
        
        # Test 'l' (right)
        self.editor._move_right()
        assert self.editor.cursor_pos == 5
        
        # Test '0' (beginning of line)
        self.editor._move_home()
        assert self.editor.cursor_pos == 0
        
        # Test '$' (end of line)
        self.editor._move_end()
        assert self.editor.cursor_pos == 11
        
        # Test 'w' (word forward)
        self.editor.cursor_pos = 0
        self.editor._move_word_forward()
        assert self.editor.cursor_pos == 6
        
        # Test 'b' (word backward)
        self.editor._move_word_backward()
        assert self.editor.cursor_pos == 0
    
    def test_vi_editing(self):
        """Test vi editing commands."""
        # Test 'x' (delete char)
        self.editor.buffer = list('hello')
        self.editor.cursor_pos = 2
        self.editor.mode = EditMode.VI_NORMAL
        self.editor._delete_char()
        assert ''.join(self.editor.buffer) == 'helo'
        
        # Test 'X' (backspace)
        self.editor.cursor_pos = 2
        self.editor._backspace()
        assert ''.join(self.editor.buffer) == 'hlo'


class TestHistorySearch:
    """Test history search functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.history = ['echo hello', 'ls -la', 'echo world', 'grep test']
        self.editor = LineEditor(history=self.history)
        self.stdout_mock = Mock()
        self.original_stdout = sys.stdout
        sys.stdout = self.stdout_mock
    
    def teardown_method(self):
        """Restore environment."""
        sys.stdout = self.original_stdout
    
    def test_reverse_search(self):
        """Test Ctrl-R reverse history search."""
        # Start search
        self.editor._start_reverse_search()
        assert self.editor.search_mode is True
        assert self.editor.search_direction == -1
        
        # Search for 'echo'
        self.editor.search_pattern = 'echo'
        self.editor._perform_search()
        assert self.editor.history_pos == 2  # 'echo world' (searching backward)
        
        # Continue search
        self.editor._search_next(-1)
        assert self.editor.history_pos == 0  # 'echo hello'
    
    def test_forward_search(self):
        """Test forward history search."""
        self.editor.history_pos = 0
        self.editor.search_mode = True
        self.editor.search_direction = 1
        self.editor.search_pattern = 'echo'
        
        self.editor._perform_search()
        assert self.editor.history_pos == 2  # 'echo world'
    
    def test_search_abort(self):
        """Test aborting search with Ctrl-G."""
        self.editor.original_line = 'current input'
        self.editor._start_reverse_search()
        self.editor.search_pattern = 'test'
        self.editor._perform_search()
        
        # Abort search
        self.editor._abort_search()
        assert self.editor.search_mode is False
        assert ''.join(self.editor.buffer) == 'current input'


class TestSetCommand:
    """Test the set command for changing edit modes."""
    
    def test_set_vi_mode(self, shell):
        """Test setting vi mode."""
        result = shell._builtin_set(['set', '-o', 'vi'])
        assert result == 0
        assert shell.edit_mode == 'vi'
    
    def test_set_emacs_mode(self, shell):
        """Test setting emacs mode."""
        shell.edit_mode = 'vi'  # Start in vi mode
        result = shell._builtin_set(['set', '-o', 'emacs'])
        assert result == 0
        assert shell.edit_mode == 'emacs'
    
    def test_set_invalid_mode(self, shell, capsys):
        """Test setting invalid mode."""
        result = shell._builtin_set(['set', '-o', 'invalid'])
        assert result == 1
        captured = capsys.readouterr()
        assert 'invalid option' in captured.err
    
    def test_show_options(self, shell, capsys):
        """Test showing current options."""
        shell.edit_mode = 'vi'
        result = shell._builtin_set(['set', '-o'])
        assert result == 0
        captured = capsys.readouterr()
        assert 'edit_mode vi' in captured.out
    
    def test_unset_vi_mode(self, shell, capsys):
        """Test unsetting vi mode (switches to emacs)."""
        shell.edit_mode = 'vi'
        result = shell._builtin_set(['set', '+o', 'vi'])
        assert result == 0
        assert shell.edit_mode == 'emacs'
        captured = capsys.readouterr()
        assert 'Edit mode set to emacs' in captured.out