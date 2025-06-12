"""Core PSH modules for state management and variable handling."""

from .exceptions import (
    LoopBreak,
    LoopContinue,
    UnboundVariableError,
    ReadonlyVariableError
)
from .variables import (
    Variable,
    VarAttributes,
    IndexedArray,
    AssociativeArray
)
from .scope import ScopeManager, VariableScope
from .scope_enhanced import EnhancedScopeManager
from .state import ShellState
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
    'ScopeManager',
    'EnhancedScopeManager',
    'VariableScope',
    # State and options
    'ShellState',
    # 'ShellOptions',  # Not yet implemented
]