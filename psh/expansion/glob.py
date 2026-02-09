"""Glob (pathname) expansion implementation."""
import glob
import os
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..shell import Shell


class GlobExpander:
    """Handles pathname expansion (globbing)."""

    def __init__(self, shell: 'Shell'):
        self.shell = shell
        self.state = shell.state

    def expand(self, pattern: str) -> List[str]:
        """
        Expand glob pattern.

        Returns a list of matching filenames, or an empty list
        if no matches are found.
        """
        # Check for extglob patterns first
        if self.state.options.get('extglob', False):
            from .extglob import contains_extglob
            if contains_extglob(pattern):
                return self._expand_extglob(pattern)

        # Check if the pattern contains glob characters
        if not any(c in pattern for c in ['*', '?', '[']):
            return [pattern]

        # Perform glob expansion
        dotglob = self.state.options.get('dotglob', False)
        matches = glob.glob(pattern, include_hidden=dotglob)

        if matches:
            # Sort matches for consistent output
            return sorted(matches)
        else:
            return []

    def _expand_extglob(self, pattern: str) -> List[str]:
        """Expand an extglob pattern against the filesystem."""
        from .extglob import expand_extglob

        dotglob = self.state.options.get('dotglob', False)

        # Determine directory and filename pattern
        dirname = os.path.dirname(pattern)
        basename = os.path.basename(pattern)

        if not dirname:
            dirname = '.'

        matches = expand_extglob(basename, dirname, dotglob=dotglob)

        if matches:
            if dirname != '.':
                matches = [os.path.join(dirname, m) for m in matches]
            return sorted(matches)
        return []
