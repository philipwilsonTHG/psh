"""Parser selection builtin."""

from typing import List

from .base import Builtin
from .registry import builtin

PARSERS = {
    'recursive_descent': ['rd', 'recursive', 'default'],
    'combinator': ['pc', 'functional'],
}

PARSER_LABELS = {
    'recursive_descent': 'production',
    'combinator': 'experimental',
}


@builtin
class ParserSelectBuiltin(Builtin):
    """Select the active parser implementation."""
    name = 'parser-select'

    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute parser-select command.

        Usage:
            parser-select              # List available parsers
            parser-select PARSER       # Switch to specified parser
        """
        if len(args) < 2:
            current = getattr(shell, '_active_parser', 'recursive_descent')
            for name, aliases in PARSERS.items():
                marker = '*' if name == current else ' '
                alias_str = ', '.join(aliases)
                label = PARSER_LABELS.get(name, '')
                shell.stdout.write(f" {marker} {name} [{label}] (aliases: {alias_str})\n")
            return 0

        requested = args[1]
        target = None
        for name, aliases in PARSERS.items():
            if requested == name or requested in aliases:
                target = name
                break

        if target is None:
            self.error(f"unknown parser: {requested}", shell)
            return 1

        shell._active_parser = target
        return 0
