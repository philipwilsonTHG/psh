#!/usr/bin/env python3
"""Key binding modes for command line editing."""

from enum import Enum, auto
from typing import Optional, Callable, Dict, Tuple


class EditMode(Enum):
    """Editing modes available."""
    EMACS = auto()
    VI_INSERT = auto()
    VI_NORMAL = auto()
    VI_VISUAL = auto()


class KeyBindings:
    """Base class for key binding implementations."""
    
    # Common control characters
    CTRL_A = '\x01'
    CTRL_B = '\x02'
    CTRL_C = '\x03'
    CTRL_D = '\x04'
    CTRL_E = '\x05'
    CTRL_F = '\x06'
    CTRL_G = '\x07'
    CTRL_H = '\x08'
    CTRL_K = '\x0b'
    CTRL_L = '\x0c'
    CTRL_N = '\x0e'
    CTRL_P = '\x10'
    CTRL_R = '\x12'
    CTRL_T = '\x14'
    CTRL_U = '\x15'
    CTRL_W = '\x17'
    CTRL_Y = '\x19'
    CTRL_UNDERSCORE = '\x1f'
    
    TAB = '\t'
    ENTER = '\r'
    BACKSPACE = '\x7f'
    ESCAPE = '\x1b'
    
    def __init__(self):
        self.bindings: Dict[str, Callable] = {}
        self.setup_bindings()
    
    def setup_bindings(self):
        """Setup key bindings - to be overridden by subclasses."""
        pass
    
    def get_action(self, key: str) -> Optional[Callable]:
        """Get the action for a key, if any."""
        return self.bindings.get(key)


class EmacsKeyBindings(KeyBindings):
    """Emacs-style key bindings."""
    
    def setup_bindings(self):
        """Setup Emacs key bindings."""
        self.bindings = {
            # Movement
            self.CTRL_A: 'move_beginning_of_line',
            self.CTRL_E: 'move_end_of_line',
            self.CTRL_F: 'move_forward_char',
            self.CTRL_B: 'move_backward_char',
            
            # Editing
            self.CTRL_D: 'delete_char',
            self.CTRL_H: 'backward_delete_char',
            self.BACKSPACE: 'backward_delete_char',
            self.CTRL_K: 'kill_line',
            self.CTRL_U: 'kill_whole_line',
            self.CTRL_W: 'kill_word_backward',
            self.CTRL_Y: 'yank',
            self.CTRL_T: 'transpose_chars',
            
            # History
            self.CTRL_P: 'previous_history',
            self.CTRL_N: 'next_history',
            self.CTRL_R: 'reverse_search_history',
            
            # Other
            self.CTRL_L: 'clear_screen',
            self.CTRL_G: 'abort',
            self.CTRL_C: 'interrupt',
            self.TAB: 'complete',
            self.ENTER: 'accept_line',
        }
        
        # Meta (Alt) key bindings
        self.meta_bindings = {
            'b': 'move_word_backward',
            'f': 'move_word_forward',
            'd': 'kill_word_forward',
            self.BACKSPACE: 'kill_word_backward',
            '<': 'move_to_first_history',
            '>': 'move_to_last_history',
        }


class ViKeyBindings(KeyBindings):
    """Vi-style key bindings."""
    
    def __init__(self):
        super().__init__()
        self.mode = EditMode.VI_INSERT
        self.repeat_count = 1
        self.pending_motion = None
        self.register = '"'  # Default register
        self.registers = {'"': ''}  # Storage for yanked/deleted text
    
    def setup_bindings(self):
        """Setup Vi key bindings for both insert and normal modes."""
        # Insert mode bindings
        self.insert_bindings = {
            self.ESCAPE: 'enter_normal_mode',
            self.CTRL_C: 'interrupt',
            self.BACKSPACE: 'backward_delete_char',
            self.CTRL_H: 'backward_delete_char',
            self.CTRL_W: 'kill_word_backward',
            self.CTRL_U: 'kill_whole_line',
            self.TAB: 'complete',
            self.ENTER: 'accept_line',
        }
        
        # Normal mode bindings
        self.normal_bindings = {
            # Mode switching
            'i': 'enter_insert_mode',
            'I': 'enter_insert_mode_at_beginning',
            'a': 'append_mode',
            'A': 'append_mode_at_end',
            'o': 'open_line_below',
            'O': 'open_line_above',
            'v': 'enter_visual_mode',
            'V': 'enter_visual_line_mode',
            
            # Movement
            'h': 'move_backward_char',
            'l': 'move_forward_char',
            'j': 'next_history',
            'k': 'previous_history',
            'w': 'move_word_forward',
            'W': 'move_WORD_forward',
            'b': 'move_word_backward',
            'B': 'move_WORD_backward',
            'e': 'move_word_end',
            'E': 'move_WORD_end',
            '0': 'move_beginning_of_line',
            '^': 'move_first_non_blank',
            '$': 'move_end_of_line',
            'gg': 'move_to_first_history',
            'G': 'move_to_last_history',
            
            # Editing
            'x': 'delete_char',
            'X': 'backward_delete_char',
            'd': 'delete_motion',
            'dd': 'delete_line',
            'D': 'delete_to_end',
            'c': 'change_motion',
            'cc': 'change_line',
            'C': 'change_to_end',
            'y': 'yank_motion',
            'yy': 'yank_line',
            'p': 'paste_after',
            'P': 'paste_before',
            'r': 'replace_char',
            'R': 'enter_replace_mode',
            'u': 'undo',
            self.CTRL_R: 'redo',
            
            # Search
            '/': 'search_forward',
            '?': 'search_backward',
            'n': 'search_next',
            'N': 'search_previous',
            '*': 'search_word_forward',
            '#': 'search_word_backward',
            
            # Other
            '.': 'repeat_last_change',
            ':': 'enter_command_mode',
            self.CTRL_L: 'clear_screen',
            self.CTRL_C: 'interrupt',
            self.ENTER: 'accept_line',
        }
        
        # Visual mode bindings (similar to normal mode with some differences)
        self.visual_bindings = self.normal_bindings.copy()
        self.visual_bindings.update({
            self.ESCAPE: 'exit_visual_mode',
            'd': 'delete_selection',
            'c': 'change_selection',
            'y': 'yank_selection',
        })
    
    def get_action(self, key: str) -> Optional[str]:
        """Get the action for a key based on current mode."""
        if self.mode == EditMode.VI_INSERT:
            return self.insert_bindings.get(key)
        elif self.mode == EditMode.VI_NORMAL:
            return self.normal_bindings.get(key)
        elif self.mode == EditMode.VI_VISUAL:
            return self.visual_bindings.get(key)
        return None