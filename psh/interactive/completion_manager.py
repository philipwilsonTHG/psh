"""Tab completion management for interactive shell."""
import readline
from typing import List, Optional

from ..tab_completion import CompletionEngine
from .base import InteractiveComponent


class CompletionManager(InteractiveComponent):
    """Manages tab completion for the interactive shell."""

    def __init__(self, shell):
        super().__init__(shell)
        self.completion_engine = CompletionEngine()
        self.current_matches = []
        self.current_text = ""

    def setup_readline(self):
        """Configure readline for tab completion."""
        # Set the completer function
        readline.set_completer(self._readline_completer)

        # Configure tab as the completion trigger
        readline.parse_and_bind('tab: complete')

        # Set word delimiters for completion
        readline.set_completer_delims(' \t\n;|&<>')

    def execute(self, text: str, line: str, cursor_pos: int) -> List[str]:
        """
        Perform tab completion for the given context.

        Args:
            text: The text to complete
            line: The full command line
            cursor_pos: Current cursor position

        Returns:
            List of possible completions
        """
        return self.get_completions(text, line, cursor_pos)

    def get_completions(self, text: str, line: str, cursor_pos: int) -> List[str]:
        """
        Get all possible completions for the given context.

        Args:
            text: The text to complete
            line: The full command line
            cursor_pos: Current cursor position

        Returns:
            List of possible completions
        """
        # Use the existing completion engine
        completions = self.completion_engine.get_completions(text, line, cursor_pos)

        # Filter out any duplicates and sort
        unique_completions = sorted(list(set(completions)))

        return unique_completions

    def _readline_completer(self, text: str, state: int) -> Optional[str]:
        """
        Readline completer function.

        This is called by readline to get completions. It's called repeatedly
        with increasing state values until it returns None.

        Args:
            text: The text to complete
            state: The state (0 for first call, increments for each match)

        Returns:
            The next completion or None when done
        """
        # On first call, generate the list of matches
        if state == 0:
            # Get the current line and cursor position from readline
            line = readline.get_line_buffer()
            cursor_pos = readline.get_endidx()

            # Get completions from our engine
            self.current_matches = self.get_completions(text, line, cursor_pos)
            self.current_text = text

        # Return the state'th match, or None if we're out of matches
        if state < len(self.current_matches):
            return self.current_matches[state]
        else:
            return None

    def complete_command(self, text: str) -> List[str]:
        """
        Complete a command name.

        Args:
            text: Partial command name

        Returns:
            List of matching command names
        """
        # For now, delegate to file completion
        # In the future, this could include:
        # - Built-in commands
        # - Functions
        # - Aliases
        # - Commands in PATH
        line = readline.get_line_buffer()
        cursor_pos = readline.get_endidx()
        return self.completion_engine.get_completions(text, line, cursor_pos)

    def complete_path(self, text: str) -> List[str]:
        """
        Complete a file or directory path.

        Args:
            text: Partial path

        Returns:
            List of matching paths
        """
        line = readline.get_line_buffer()
        cursor_pos = readline.get_endidx()
        return self.completion_engine.get_completions(text, line, cursor_pos)

    def complete_variable(self, text: str) -> List[str]:
        """
        Complete a variable name.

        Args:
            text: Partial variable name (including $)

        Returns:
            List of matching variable names
        """
        # Extract variable name without $
        if text.startswith('$'):
            prefix = text[1:]
        else:
            prefix = text

        matches = []

        # Check shell variables
        for name in self.state.variables:
            if name.startswith(prefix):
                matches.append('$' + name)

        # Check environment variables
        for name in self.state.env:
            if name.startswith(prefix):
                matches.append('$' + name)

        return sorted(matches)
