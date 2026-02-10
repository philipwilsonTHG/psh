"""Eval builtin implementation."""
from .base import Builtin
from .registry import builtin


@builtin
class EvalBuiltin(Builtin):
    """Execute arguments as shell commands."""

    name = "eval"
    help_text = "Execute arguments as a shell command"

    def execute(self, args, shell):
        """Execute the eval builtin.

        Concatenates all arguments into a single string and executes
        it as shell commands. The string goes through full shell
        processing including tokenization, parsing, and execution.

        Args:
            args: List of arguments where args[0] is 'eval'
            shell: The shell instance

        Returns:
            Exit status of the executed command(s), or 0 if empty
        """
        # Skip args[0] which is 'eval' itself
        if len(args) <= 1:
            # Empty eval returns 0
            return 0

        # Concatenate all arguments after 'eval' with spaces
        command_string = ' '.join(args[1:])

        # Execute using shell's run_command method
        # This ensures full processing: tokenization, parsing, execution
        # add_to_history=False prevents eval commands from polluting history
        return shell.run_command(command_string, add_to_history=False)
