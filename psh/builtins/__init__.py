"""Shell builtins package."""

# Import all builtin modules to trigger registration
from . import (
    aliases,
    command_builtin,
    core,
    debug_control,
    directory_stack,
    disown,
    environment,
    eval_command,
    function_support,
    help_command,
    io,
    job_control,
    kill_command,
    navigation,
    parse_tree,
    parser_control,
    parser_experiment,
    positional,
    read_builtin,
    shell_options,
    shell_state,
    signal_handling,
    source_command,
    test_command,
    type_builtin,
)
from .base import Builtin
from .registry import builtin, registry

# Re-export for convenience
__all__ = ['registry', 'builtin', 'Builtin']
