"""Token formatting utilities for debugging."""
from ..token_types import Token


class TokenFormatter:
    """Formats token lists for debug output."""

    @staticmethod
    def format(tokens):
        """Format token list for debugging output."""
        result = []
        for i, token in enumerate(tokens):
            if isinstance(token, Token):
                result.append(f"  [{i:3d}] {token.type.name:20s} '{token.value}'")
            else:
                result.append(f"  [{i:3d}] {str(token)}")
        return "\n".join(result)
