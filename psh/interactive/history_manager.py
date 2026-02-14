"""Command history management."""
import os
import readline
from typing import List

from .base import InteractiveComponent


class HistoryManager(InteractiveComponent):
    """Manages command history."""

    def add_to_history(self, command: str) -> None:
        """Add a command to history."""
        # Don't add duplicates of the immediately previous command
        if not self.state.history or self.state.history[-1] != command:
            self.state.history.append(command)
            readline.add_history(command)
            # Trim history if it exceeds max size
            if len(self.state.history) > self.state.max_history_size:
                self.state.history = self.state.history[-self.state.max_history_size:]

    def load_from_file(self) -> None:
        """Load command history from file."""
        try:
            if os.path.exists(self.state.history_file):
                with open(self.state.history_file, 'r') as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if line:
                            self.state.history.append(line)
                            readline.add_history(line)
                # Trim to max size
                if len(self.state.history) > self.state.max_history_size:
                    self.state.history = self.state.history[-self.state.max_history_size:]
        except OSError:
            # Silently ignore history file errors
            pass

    def save_to_file(self) -> None:
        """Save command history to file."""
        try:
            with open(self.state.history_file, 'w') as f:
                # Save only the last max_history_size commands
                for cmd in self.state.history[-self.state.max_history_size:]:
                    f.write(cmd + '\n')
        except OSError:
            # Silently ignore history file errors
            pass

    def get_history(self) -> List[str]:
        """Get the command history."""
        return self.state.history.copy()

    def clear_history(self) -> None:
        """Clear command history."""
        self.state.history.clear()
        readline.clear_history()
