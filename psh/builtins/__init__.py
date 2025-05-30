"""Shell builtins package."""

from .registry import registry, builtin
from .base import Builtin

# Import all builtin modules to trigger registration
from . import core
from . import io  
from . import navigation
from . import shell_state
from . import environment
from . import aliases

# Re-export for convenience
__all__ = ['registry', 'builtin', 'Builtin']