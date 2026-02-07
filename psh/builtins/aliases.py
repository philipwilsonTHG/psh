"""Alias management builtins (alias, unalias)."""

import sys
from typing import TYPE_CHECKING, List

from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class AliasBuiltin(Builtin):
    """Define or display aliases."""

    @property
    def name(self) -> str:
        return "alias"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Define or display aliases."""
        if len(args) == 1:
            # No arguments - list all aliases
            for name, value in sorted(shell.alias_manager.list_aliases()):
                # Escape single quotes in value for display
                escaped_value = value.replace("'", "'\"'\"'")
                print(f"alias {name}='{escaped_value}'",
                      file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            return 0

        exit_code = 0

        # Process each argument
        i = 1
        while i < len(args):
            arg = args[i]

            if '=' in arg:
                # This looks like an assignment
                equals_pos = arg.index('=')
                name = arg[:equals_pos]
                value_start = arg[equals_pos + 1:]

                # Check if value starts with a quote
                if value_start and value_start[0] in ("'", '"'):
                    quote_char = value_start[0]
                    # Need to find the closing quote, which might be in later args
                    value_parts = [value_start[1:]]  # Remove opening quote

                    # Look for closing quote
                    found_close = False
                    j = i

                    # Check if closing quote is in the same arg
                    if value_start[1:].endswith(quote_char):
                        value = value_start[1:-1]
                        found_close = True
                    else:
                        # Look in subsequent args
                        j = i + 1
                        while j < len(args):
                            if args[j].endswith(quote_char):
                                value_parts.append(args[j][:-1])  # Remove closing quote
                                found_close = True
                                break
                            else:
                                value_parts.append(args[j])
                            j += 1

                        if found_close:
                            value = ' '.join(value_parts)
                            i = j  # Skip the args we consumed
                        else:
                            # No closing quote found
                            value = value_start
                else:
                    # No quotes, just use the value as is
                    value = value_start

                try:
                    shell.alias_manager.define_alias(name, value)
                except ValueError as e:
                    self.error(str(e), shell)
                    exit_code = 1
            else:
                # Show specific alias
                value = shell.alias_manager.get_alias(arg)
                if value is not None:
                    # Escape single quotes in value for display
                    escaped_value = value.replace("'", "'\"'\"'")
                    print(f"alias {arg}='{escaped_value}'",
                          file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
                else:
                    self.error(f"{arg}: not found", shell)
                    exit_code = 1

            i += 1

        return exit_code

    @property
    def help(self) -> str:
        return """alias: alias [name[=value] ...]
    
    Define or display aliases.
    With no arguments, print all aliases.
    With name=value, define an alias.
    With just name, display the alias value."""


@builtin
class UnaliasBuiltin(Builtin):
    """Remove aliases."""

    @property
    def name(self) -> str:
        return "unalias"

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Remove aliases."""
        if len(args) == 1:
            self.error("usage: unalias [-a] name [name ...]", shell)
            return 1

        if args[1] == '-a':
            # Remove all aliases
            shell.alias_manager.clear_aliases()
            return 0

        exit_code = 0
        for name in args[1:]:
            if not shell.alias_manager.undefine_alias(name):
                self.error(f"{name}: not found", shell)
                exit_code = 1

        return exit_code

    @property
    def help(self) -> str:
        return """unalias: unalias [-a] name [name ...]
    
    Remove aliases.
    
    Options:
      -a    Remove all aliases
    
    Without -a, remove the specified aliases."""
