"""Base class for shell builtins."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..shell import Shell


class Builtin(ABC):
    """Abstract base class for all shell builtins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the primary command name."""
        pass

    @property
    def aliases(self) -> List[str]:
        """Return any command aliases."""
        return []

    @abstractmethod
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """
        Execute the builtin command.

        Args:
            args: Command arguments, including the command name as args[0]
            shell: The shell instance for accessing state and I/O

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass

    @property
    def synopsis(self) -> str:
        """Return brief command syntax for the builtin."""
        return f"{self.name}"

    @property
    def description(self) -> str:
        """Return one-line description for the builtin."""
        return self.__class__.__doc__ or 'no description available'

    @property
    def help(self) -> str:
        """Return detailed help text for the builtin."""
        return f"{self.synopsis}\n    {self.description}"

    def error(self, message: str, shell: 'Shell') -> None:
        """Print an error message to stderr."""
        import sys
        stderr = shell.stderr if hasattr(shell, 'stderr') else sys.stderr
        print(f"{self.name}: {message}", file=stderr)
        stderr.flush()
