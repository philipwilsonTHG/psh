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
from . import job_control
from . import test_command
from . import source_command
from . import function_support
from . import read_builtin
from . import eval_command
from . import help_command
from . import kill_command
from . import positional
from . import command_builtin
from . import signal_handling
from . import directory_stack
from . import disown
from . import type_builtin
from . import parse_tree
from . import debug_control
from . import parser_control

# Re-export for convenience
__all__ = ['registry', 'builtin', 'Builtin']