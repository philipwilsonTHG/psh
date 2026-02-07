#!/usr/bin/env python3
"""Tab completion implementation for psh."""

import os
import sys
import termios
import tty
from typing import List, Optional


class TerminalManager:
    """Manages terminal mode for raw input handling."""

    def __init__(self):
        self.old_settings = None
        self.is_raw = False

    def enter_raw_mode(self):
        """Put terminal in raw mode to capture individual keystrokes."""
        # Enter raw mode for any TTY (including PTYs)
        # Note: isatty() returns True for both real terminals and pseudo-terminals
        if sys.stdin.isatty() and not self.is_raw:
            try:
                self.old_settings = termios.tcgetattr(sys.stdin)
                tty.setraw(sys.stdin.fileno())
                self.is_raw = True
            except (termios.error, OSError):
                # If we can't set raw mode, continue without it
                pass

    def exit_raw_mode(self):
        """Restore normal terminal mode."""
        if self.old_settings is not None and self.is_raw:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            self.is_raw = False

    def __enter__(self):
        self.enter_raw_mode()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_raw_mode()


class CompletionEngine:
    """Handles tab completion logic."""

    def get_completions(self, text: str, line: str, cursor_pos: int) -> List[str]:
        """Get possible completions for the current context."""
        # Extract the word being completed
        word_start = self._find_word_start(line, cursor_pos)
        current_word = line[word_start:cursor_pos]

        # Get file/directory completions
        return self._get_path_completions(current_word)

    def _find_word_start(self, line: str, cursor_pos: int) -> int:
        """Find the start of the current word."""
        # Handle quotes
        in_quotes = False
        quote_char = None
        escape_next = False

        for i in range(cursor_pos):
            if escape_next:
                escape_next = False
                continue

            if line[i] == '\\':
                escape_next = True
                continue

            if line[i] in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = line[i]
                elif line[i] == quote_char:
                    in_quotes = False
                    quote_char = None

        # Find word boundary
        pos = cursor_pos - 1
        while pos >= 0:
            char = line[pos]

            # If we're in quotes, only stop at the opening quote
            if in_quotes:
                if char == quote_char and (pos == 0 or line[pos-1] != '\\'):
                    return pos + 1
            else:
                # Stop at whitespace or special shell characters
                if char in ' \t;|&<>':
                    return pos + 1

            pos -= 1

        return 0

    def _get_path_completions(self, partial_path: str) -> List[str]:
        """Get file/directory completions for a partial path."""
        # Remember if we started with ~
        started_with_tilde = partial_path.startswith('~')
        expanded_path = partial_path

        # Handle home directory expansion for searching
        if started_with_tilde:
            expanded_path = os.path.expanduser(partial_path)

        # Determine directory and basename
        if os.path.sep in expanded_path:
            dirname, basename = os.path.split(expanded_path)
            if not dirname:
                dirname = os.path.sep
        else:
            dirname = '.'
            basename = expanded_path

        # Expand the directory path
        dirname = os.path.expanduser(dirname)
        if not os.path.isabs(dirname):
            dirname = os.path.abspath(dirname)

        try:
            # Get all entries in the directory
            entries = os.listdir(dirname)

            # Filter entries that match the basename
            matches = []
            for entry in entries:
                # Include hidden files only if explicitly requested
                if not basename and entry.startswith('.'):
                    continue
                if entry.startswith(basename):
                    matches.append(entry)

            # Build full paths and add indicators
            results = []
            for match in sorted(matches):
                full_path = os.path.join(dirname, match)

                # Add trailing slash for directories
                if os.path.isdir(full_path):
                    match += os.path.sep

                # Reconstruct the path as it should appear
                if os.path.sep in partial_path:
                    # Keep the original directory part
                    dir_part = partial_path.rsplit(os.path.sep, 1)[0]
                    result = dir_part + os.path.sep + match
                else:
                    result = match

                results.append(result)

            return results

        except (OSError, PermissionError):
            return []

    def find_common_prefix(self, candidates: List[str]) -> str:
        """Find the longest common prefix among candidates."""
        if not candidates:
            return ""

        if len(candidates) == 1:
            return candidates[0]

        # Find common prefix
        prefix = candidates[0]
        for candidate in candidates[1:]:
            # Shorten prefix until it matches
            while not candidate.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    break

        return prefix

    def escape_path(self, path: str) -> str:
        """Escape special characters in a path for shell use."""
        # Characters that need escaping
        special_chars = ' \t\n\\$`"\'(){}[]&;|<>*?!#'

        escaped = []
        for i, char in enumerate(path):
            # Don't escape tilde at the beginning (it's for home directory expansion)
            if char == '~' and i == 0:
                escaped.append(char)
            elif char in special_chars:
                escaped.append('\\')
                escaped.append(char)
            else:
                escaped.append(char)

        return ''.join(escaped)


class LineEditor:
    """Interactive line editor with tab completion."""

    CTRL_C = '\x03'
    CTRL_D = '\x04'
    TAB = '\t'
    ENTER = '\r'
    BACKSPACE = '\x7f'
    ESCAPE = '\x1b'

    def __init__(self, history: Optional[List[str]] = None):
        self.buffer = []
        self.cursor_pos = 0
        self.history = history or []
        self.history_pos = len(self.history)
        self.completion_engine = CompletionEngine()
        self.terminal = TerminalManager()
        self.original_line = ""
        self.completion_state = None
        self.current_prompt = ""

    def read_line(self, prompt: str = "") -> Optional[str]:
        """Read a line with editing and tab completion support."""
        # Print prompt
        sys.stdout.write(prompt)
        sys.stdout.flush()

        self.buffer = []
        self.cursor_pos = 0
        self.history_pos = len(self.history)
        self.original_line = ""
        self.completion_state = None
        self.current_prompt = prompt

        with self.terminal:
            while True:
                char = sys.stdin.read(1)

                if char == self.CTRL_C:
                    # Clear line and raise KeyboardInterrupt
                    # Move to beginning of line first
                    sys.stdout.write('\r')
                    # Clear entire line
                    sys.stdout.write('\033[K')
                    # Show ^C on its own line
                    sys.stdout.write('^C\r\n')
                    sys.stdout.flush()
                    raise KeyboardInterrupt()

                elif char == self.CTRL_D:
                    if not self.buffer:
                        # EOF on empty line
                        sys.stdout.write('\r\n')
                        sys.stdout.flush()
                        return None
                    else:
                        # Delete character at cursor
                        self._delete_char()

                elif char == self.TAB:
                    self._handle_tab()

                elif char == self.ENTER:
                    sys.stdout.write('\r\n')
                    sys.stdout.flush()
                    line = ''.join(self.buffer)
                    if line.strip():
                        self.history.append(line)
                    return line

                elif char == self.BACKSPACE:
                    self._backspace()

                elif char == self.ESCAPE:
                    # Handle escape sequences (arrow keys, etc.)
                    self._handle_escape_sequence()

                elif ord(char) >= 32:  # Printable character
                    self._insert_char(char)
                    self.completion_state = None

    def _insert_char(self, char: str):
        """Insert a character at the cursor position."""
        self.buffer.insert(self.cursor_pos, char)
        self.cursor_pos += 1

        # Redraw the line from cursor position
        sys.stdout.write(char)

        # If we're not at the end, redraw the rest and move cursor back
        if self.cursor_pos < len(self.buffer):
            rest = ''.join(self.buffer[self.cursor_pos:])
            sys.stdout.write(rest)
            sys.stdout.write('\b' * len(rest))

        sys.stdout.flush()

    def _backspace(self):
        """Delete character before cursor."""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
            del self.buffer[self.cursor_pos]

            # Move cursor back
            sys.stdout.write('\b')

            # Redraw from cursor to end of line
            rest = ''.join(self.buffer[self.cursor_pos:])
            sys.stdout.write(rest + ' ')
            sys.stdout.write('\b' * (len(rest) + 1))
            sys.stdout.flush()

    def _delete_char(self):
        """Delete character at cursor."""
        if self.cursor_pos < len(self.buffer):
            del self.buffer[self.cursor_pos]

            # Redraw from cursor to end of line
            rest = ''.join(self.buffer[self.cursor_pos:])
            sys.stdout.write(rest + ' ')
            sys.stdout.write('\b' * (len(rest) + 1))
            sys.stdout.flush()

    def _handle_tab(self):
        """Handle tab completion."""
        line = ''.join(self.buffer)

        # Get completions
        completions = self.completion_engine.get_completions(
            line[:self.cursor_pos], line, self.cursor_pos
        )

        if not completions:
            # No completions, just beep or do nothing
            sys.stdout.write('\a')
            sys.stdout.flush()
            return

        if len(completions) == 1:
            # Single completion - use it
            self._apply_completion(completions[0])
        else:
            # Multiple completions
            common_prefix = self.completion_engine.find_common_prefix(completions)

            # Find the word being completed
            word_start = self.completion_engine._find_word_start(line, self.cursor_pos)
            current_word = line[word_start:self.cursor_pos]

            if len(common_prefix) > len(current_word):
                # Can expand to common prefix
                self._apply_completion(common_prefix)
            else:
                # Show all completions
                self._show_completions(completions)

    def _apply_completion(self, completion: str):
        """Apply a completion to the current line."""
        line = ''.join(self.buffer)

        # Find the word being completed
        word_start = self.completion_engine._find_word_start(line, self.cursor_pos)

        # Check if we need to escape the completion
        if word_start == 0 or line[word_start-1] not in '"\'':
            # Not in quotes, escape special characters
            completion = self.completion_engine.escape_path(completion)

        # Calculate what we need to erase
        chars_to_erase = self.cursor_pos - word_start

        # Move cursor back to word start
        if chars_to_erase > 0:
            sys.stdout.write('\b' * chars_to_erase)

        # Clear from cursor to end of line
        sys.stdout.write('\033[K')

        # Write the completion
        sys.stdout.write(completion)

        # Write any remaining text after the cursor
        if self.cursor_pos < len(line):
            remaining = line[self.cursor_pos:]
            sys.stdout.write(remaining)
            # Move cursor back to end of completion
            sys.stdout.write('\b' * len(remaining))

        sys.stdout.flush()

        # Update buffer and cursor position
        new_line = line[:word_start] + completion
        if self.cursor_pos < len(line):
            new_line += line[self.cursor_pos:]

        self.buffer = list(new_line)
        self.cursor_pos = word_start + len(completion)

    def _show_completions(self, completions: List[str]):
        """Display multiple completions."""
        # Save current line
        self.terminal.exit_raw_mode()

        # Display completions
        sys.stdout.write('\r\n')
        self._display_in_columns(completions)

        # Redraw prompt and current line
        self.terminal.enter_raw_mode()
        # In raw mode, we need both newline and carriage return
        sys.stdout.write('\r\n')
        # Now print prompt and buffer
        sys.stdout.write(self.current_prompt)
        sys.stdout.write(''.join(self.buffer))

        # Position cursor correctly
        if self.cursor_pos < len(self.buffer):
            sys.stdout.write('\b' * (len(self.buffer) - self.cursor_pos))

        sys.stdout.flush()

    def _display_in_columns(self, items: List[str]):
        """Display items in columns."""
        if not items:
            return

        # Get terminal width
        try:
            import shutil
            term_width = shutil.get_terminal_size().columns
        except:
            term_width = 80

        # Calculate column width (add 2 for spacing)
        max_len = max(len(item) for item in items)
        col_width = max_len + 2

        # Calculate number of columns
        num_cols = max(1, term_width // col_width)

        # Display items
        for i, item in enumerate(sorted(items)):
            sys.stdout.write(item.ljust(col_width))
            if (i + 1) % num_cols == 0:
                sys.stdout.write('\n')

        if len(items) % num_cols != 0:
            sys.stdout.write('\n')

        sys.stdout.flush()

    def _handle_escape_sequence(self):
        """Handle escape sequences like arrow keys."""
        # Read the rest of the sequence
        seq = sys.stdin.read(2)

        if seq == '[A':  # Up arrow
            self._history_up()
        elif seq == '[B':  # Down arrow
            self._history_down()
        elif seq == '[C':  # Right arrow
            self._move_right()
        elif seq == '[D':  # Left arrow
            self._move_left()
        elif seq == '[H':  # Home
            self._move_home()
        elif seq == '[F':  # End
            self._move_end()

    def _move_left(self):
        """Move cursor left."""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
            sys.stdout.write('\b')
            sys.stdout.flush()

    def _move_right(self):
        """Move cursor right."""
        if self.cursor_pos < len(self.buffer):
            sys.stdout.write(self.buffer[self.cursor_pos])
            self.cursor_pos += 1
            sys.stdout.flush()

    def _move_home(self):
        """Move cursor to beginning of line."""
        if self.cursor_pos > 0:
            sys.stdout.write('\b' * self.cursor_pos)
            self.cursor_pos = 0
            sys.stdout.flush()

    def _move_end(self):
        """Move cursor to end of line."""
        if self.cursor_pos < len(self.buffer):
            rest = ''.join(self.buffer[self.cursor_pos:])
            sys.stdout.write(rest)
            self.cursor_pos = len(self.buffer)
            sys.stdout.flush()

    def _history_up(self):
        """Move up in history."""
        if self.history_pos > 0:
            # Save current line if at bottom of history
            if self.history_pos == len(self.history):
                self.original_line = ''.join(self.buffer)

            # Clear current line
            self._clear_current_line()

            # Update to previous history entry
            self.history_pos -= 1
            self._replace_line(self.history[self.history_pos])

            # Display the new line
            sys.stdout.write(''.join(self.buffer))
            sys.stdout.flush()

    def _history_down(self):
        """Move down in history."""
        if self.history_pos < len(self.history):
            # Clear current line
            self._clear_current_line()

            self.history_pos += 1

            if self.history_pos == len(self.history):
                # Restore original line
                self._replace_line(self.original_line)
            else:
                self._replace_line(self.history[self.history_pos])

            # Display the new line
            sys.stdout.write(''.join(self.buffer))
            sys.stdout.flush()

    def _clear_current_line(self):
        """Clear the current input line (preserving prompt)."""
        # Move cursor to beginning of input
        if self.cursor_pos > 0:
            sys.stdout.write('\b' * self.cursor_pos)
        # Clear from cursor to end of line
        sys.stdout.write('\033[K')
        sys.stdout.flush()

    def _replace_line(self, new_line: str):
        """Replace the current line with new text."""
        self.buffer = list(new_line)
        self.cursor_pos = len(self.buffer)

    def _redraw_line(self):
        """Redraw the current line."""
        # Move cursor to beginning of input (after prompt)
        # We need to move back by cursor_pos characters
        if self.cursor_pos > 0:
            sys.stdout.write('\b' * self.cursor_pos)

        # Clear to end of line and redraw
        sys.stdout.write('\033[K')
        sys.stdout.write(''.join(self.buffer))

        # Position cursor
        if self.cursor_pos < len(self.buffer):
            sys.stdout.write('\b' * (len(self.buffer) - self.cursor_pos))

        sys.stdout.flush()

    def _clear_line(self):
        """Clear the current line."""
        # Move to beginning and clear
        if self.cursor_pos > 0:
            sys.stdout.write('\b' * self.cursor_pos)
        sys.stdout.write('\033[K')
        sys.stdout.flush()
