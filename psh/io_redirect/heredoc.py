"""Here document implementation."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..shell import Shell


class HeredocHandler:
    """Handles here document collection and processing."""

    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state

    def _read_heredoc_content(self, redirect):
        """Read heredoc content from input until delimiter is found."""
        # Skip if content is already populated (from parser)
        if redirect.heredoc_content is not None:
            return

        # Fall back to reading from stdin (for interactive mode)
        lines = []
        delimiter = redirect.target

        # Read lines until we find the delimiter
        while True:
            try:
                line = input()
                if line.strip() == delimiter:
                    break
                if redirect.type == '<<-':
                    # Strip leading tabs
                    line = line.lstrip('\t')
                lines.append(line)
            except EOFError:
                break

        redirect.heredoc_content = '\n'.join(lines)
        if lines:  # Add final newline if there was content
            redirect.heredoc_content += '\n'
