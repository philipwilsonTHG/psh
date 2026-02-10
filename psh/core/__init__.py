"""Core PSH modules for state management and variable handling."""

from .exceptions import LoopBreak, LoopContinue, ReadonlyVariableError, UnboundVariableError
from .scope_enhanced import EnhancedScopeManager, VariableScope
from .state import ShellState
from .variables import AssociativeArray, IndexedArray, VarAttributes, Variable

# from .options import ShellOptions  # Not yet implemented

__all__ = [
    # Exceptions
    'LoopBreak',
    'LoopContinue',
    'UnboundVariableError',
    'ReadonlyVariableError',
    # Variables
    'Variable',
    'VarAttributes',
    'IndexedArray',
    'AssociativeArray',
    # Scope management
    'EnhancedScopeManager',
    'VariableScope',
    # State and options
    'ShellState',
    # 'ShellOptions',  # Not yet implemented
]
