"""
PSH Executor Package

This package implements the execution engine for PSH using a modular
visitor pattern architecture. It transforms AST nodes into executed
commands with proper process management, I/O handling, and job control.

The package is organized into focused modules:
- core: Main ExecutorVisitor coordinating execution
- command: Simple command execution (builtins, functions, externals)
- pipeline: Pipeline execution and process management
- control_flow: Control structures (if, while, for, case, select)
- function: Function execution and scope management
- array: Array initialization and element operations
- arithmetic: Arithmetic evaluation execution
- subshell: Subshell and brace group execution
- context: Execution context and state management
- utils: Shared utilities and helpers
"""

from .array import ArrayOperationExecutor
from .command import CommandExecutor
from .context import ExecutionContext
from .control_flow import ControlFlowExecutor
from .core import ExecutorVisitor
from .function import FunctionOperationExecutor
from .pipeline import PipelineContext, PipelineExecutor
from .strategies import (
    BuiltinExecutionStrategy,
    ExecutionStrategy,
    ExternalExecutionStrategy,
    FunctionExecutionStrategy,
)
from .subshell import SubshellExecutor

__all__ = [
    'ExecutorVisitor',
    'ExecutionContext',
    'PipelineContext',
    'PipelineExecutor',
    'CommandExecutor',
    'ControlFlowExecutor',
    'ArrayOperationExecutor',
    'FunctionOperationExecutor',
    'SubshellExecutor',
    'ExecutionStrategy',
    'BuiltinExecutionStrategy',
    'FunctionExecutionStrategy',
    'ExternalExecutionStrategy'
]
