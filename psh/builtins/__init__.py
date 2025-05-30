"""Shell builtins package."""

from .registry import registry, builtin
from .base import Builtin

# Import all builtin modules to trigger registration
from . import core
from . import io
from . import navigation

# Re-export for convenience
__all__ = ['registry', 'builtin', 'Builtin']