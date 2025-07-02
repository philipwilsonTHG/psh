# Executor Package Refactoring Plan

## Overview

This document details the plan to refactor the monolithic ExecutorVisitor (~2000 lines) into a well-structured package following the successful patterns established in the lexer and expansion packages.

## Current State

The ExecutorVisitor is a single large class in `psh/visitor/executor_visitor.py` that handles all execution logic:
- Command execution (simple, pipeline, subshell)
- Control structures (if, while, for, case, select)
- Function management
- Array operations
- I/O redirection
- Job control
- Process management

## Issues with Current Architecture

1. **Monolithic Design**: ~2000 lines in a single class
2. **Tight Coupling**: Direct dependencies on multiple managers
3. **Complex State Management**: Multiple context flags scattered throughout
4. **Difficult Testing**: Hard to test individual components
5. **Maintenance Burden**: Changes require understanding entire class

## Proposed Package Structure

```
psh/executor/
├── __init__.py          # Public API exports
├── core.py              # Main ExecutorVisitor coordinating execution
├── command.py           # Command execution (simple, external, builtin)
├── pipeline.py          # Pipeline execution and process management
├── control_flow.py      # Control structures (if, while, for, case)
├── function.py          # Function execution and management
├── array.py             # Array operations and assignments
├── arithmetic.py        # Arithmetic evaluation execution
├── subshell.py          # Subshell and brace group execution
├── context.py           # ExecutionContext and state management
├── strategies.py        # Execution strategies for different command types
└── utils.py             # Shared utilities and helpers
```

## Implementation Phases

### Phase 1: Package Creation ✅ COMPLETED
- Created executor package directory structure
- Moved ExecutorVisitor to `core.py`
- Updated imports throughout codebase
- Fixed circular import issues
- Verified basic functionality

### Phase 2: Extract Execution Context (Next)
Create a structured context object to replace scattered state:

```python
# context.py
@dataclass
class ExecutionContext:
    """Encapsulates execution state for cleaner parameter passing."""
    in_pipeline: bool = False
    in_subshell: bool = False
    in_forked_child: bool = False
    loop_depth: int = 0
    current_function: Optional[str] = None
    pipeline_context: Optional[PipelineContext] = None
    background_job: Optional[Job] = None
    
    def fork_context(self) -> 'ExecutionContext':
        """Create context for forked child process."""
        return ExecutionContext(
            in_pipeline=self.in_pipeline,
            in_subshell=True,
            in_forked_child=True,
            loop_depth=self.loop_depth,
            current_function=self.current_function
        )
```

### Phase 3: Extract Command Execution
Move command execution logic to dedicated module:

```python
# command.py
class CommandExecutor:
    """Handles execution of simple commands."""
    
    def __init__(self, shell: Shell, context: ExecutionContext):
        self.shell = shell
        self.context = context
        self.strategies = {
            'builtin': BuiltinExecutionStrategy(shell),
            'function': FunctionExecutionStrategy(shell),
            'external': ExternalExecutionStrategy(shell)
        }
    
    def execute(self, command: SimpleCommand) -> int:
        """Execute a simple command using appropriate strategy."""
        # Handle assignments
        # Determine command type
        # Delegate to strategy
```

### Phase 4: Extract Pipeline Execution
Create dedicated pipeline executor:

```python
# pipeline.py
class PipelineExecutor:
    """Handles pipeline execution with proper process management."""
    
    def __init__(self, shell: Shell, job_manager: JobManager):
        self.shell = shell
        self.job_manager = job_manager
    
    def execute(self, pipeline: Pipeline, context: ExecutionContext) -> int:
        """Execute a pipeline of commands."""
        # Handle single command optimization
        # Create pipeline context
        # Fork processes
        # Manage process groups
        # Wait for completion
```

### Phase 5: Extract Control Flow
Move control structures to dedicated module:

```python
# control_flow.py
class ControlFlowExecutor:
    """Handles control structure execution."""
    
    def execute_if(self, node: IfConditional, visitor: ExecutorVisitor) -> int:
        """Execute if/then/else statement."""
        
    def execute_while(self, node: WhileLoop, visitor: ExecutorVisitor) -> int:
        """Execute while loop."""
        
    def execute_for(self, node: ForLoop, visitor: ExecutorVisitor) -> int:
        """Execute for loop."""
```

### Phase 6: Extract Specialized Operations
Move array, function, and subshell operations:

```python
# array.py
class ArrayOperationExecutor:
    """Handles array initialization and element operations."""
    
# function.py  
class FunctionExecutor:
    """Handles function execution with scope management."""
    
# subshell.py
class SubshellExecutor:
    """Handles subshell and brace group execution."""
```

### Phase 7: Refactor Core Visitor
Update core.py to delegate to specialized executors:

```python
# core.py
class ExecutorVisitor(ASTVisitor[int]):
    """Main executor that delegates to specialized components."""
    
    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell
        self.context = ExecutionContext()
        
        # Initialize specialized executors
        self.command_executor = CommandExecutor(shell, self.context)
        self.pipeline_executor = PipelineExecutor(shell, shell.job_manager)
        self.control_flow_executor = ControlFlowExecutor()
        # ... etc
    
    def visit_SimpleCommand(self, node: SimpleCommand) -> int:
        return self.command_executor.execute(node)
    
    def visit_Pipeline(self, node: Pipeline) -> int:
        return self.pipeline_executor.execute(node, self.context)
```

## Benefits

1. **Separation of Concerns**: Each module handles one aspect
2. **Testability**: Isolated components with clear interfaces
3. **Maintainability**: Easier to understand and modify
4. **Extensibility**: New features can be added to specific modules
5. **Performance**: Potential for optimized execution paths

## Testing Strategy

1. **Unit Tests**: Test each executor component independently
2. **Integration Tests**: Verify components work together
3. **Regression Tests**: Ensure existing functionality preserved
4. **Performance Tests**: Verify no performance degradation

## Migration Strategy

1. **Incremental Refactoring**: One component at a time
2. **Maintain Compatibility**: Keep same public API
3. **Parallel Development**: Old code remains until new is ready
4. **Comprehensive Testing**: Test at each step

## Success Criteria

1. All existing tests pass
2. Code coverage maintained or improved
3. Performance unchanged or better
4. Clear module boundaries
5. Improved developer experience

## Future Enhancements

After refactoring:
1. Parallel pipeline execution optimization
2. Async command execution support
3. Enhanced debugging capabilities
4. Performance profiling per component
5. Plugin architecture for custom executors

## Status

- [x] Phase 1: Package creation and basic setup
- [x] Phase 2: Extract execution context
- [x] Phase 3: Extract command execution
- [x] Phase 4: Extract pipeline execution
- [x] Phase 5: Extract control flow
- [x] Phase 6: Extract specialized operations
- [x] Phase 7: Refactor core visitor

## Completed Phases

### Phase 1: Package Creation (Completed)
- Created executor package directory structure
- Moved ExecutorVisitor to core.py
- Fixed circular imports
- Updated all imports throughout codebase

### Phase 2: Execution Context (Completed)
- Created ExecutionContext dataclass in context.py
- Replaced scattered state variables with structured context
- Moved PipelineContext to pipeline.py
- Updated all references to use context object
- Created comprehensive tests for ExecutionContext
- Verified functionality with integration tests

The ExecutionContext provides:
- Immutable context creation methods
- Clear state encapsulation
- Helper methods for common checks
- Proper context inheritance for subprocesses

### Phase 3: Command Execution (Completed)
- Created CommandExecutor class in command.py
- Implemented Strategy pattern with three strategies:
  - BuiltinExecutionStrategy: Handles builtin commands
  - FunctionExecutionStrategy: Placeholder for function execution (Phase 6)
  - ExternalExecutionStrategy: Handles external command execution with full fork/exec
- Extracted all command execution logic from ExecutorVisitor
- Simplified visit_SimpleCommand to single delegation call
- Maintained full compatibility with existing functionality
- Created comprehensive tests for CommandExecutor

The CommandExecutor provides:
- Clean separation of command execution logic
- Strategy pattern for different command types
- Proper handling of variable assignments
- Support for command-specific assignments
- Redirection handling for all command types
- Xtrace support

### Phase 4: Pipeline Execution (Completed)
- Created PipelineExecutor class in pipeline.py
- Moved all pipeline execution logic from ExecutorVisitor
- Handles complex pipeline features:
  - Multi-stage pipelines with proper pipe management
  - Process group management for job control
  - Terminal control for foreground pipelines
  - Background pipeline execution
  - Pipeline negation (NOT operator)
  - Pipefail option support
- Removed ~200 lines of pipeline code from core.py
- Removed all old command execution methods
- Created comprehensive tests for PipelineExecutor

The PipelineExecutor provides:
- Complete pipeline execution management
- Process forking and pipe creation
- Job control integration
- Terminal control handling
- Clean separation from visitor logic
- Support for pipeline-specific options

Code reduction achieved:
- Removed _execute_pipeline (~140 lines)
- Removed _setup_pipeline_redirections (~18 lines)
- Removed _wait_for_pipeline (~20 lines)
- Removed _pipeline_to_string (~3 lines)
- Removed _command_to_string (~8 lines)
- Removed _execute_command (~22 lines)
- Removed _execute_builtin (~27 lines)
- Removed _execute_function (~65 lines)
- Removed _execute_external (~112 lines)
- Total: ~415 lines removed from core.py

### Phase 5: Control Flow Extraction (Completed)
- Created ControlFlowExecutor class in control_flow.py
- Moved all control flow logic from ExecutorVisitor:
  - If/elif/else conditionals (execute_if)
  - While loops (execute_while)
  - For loops (execute_for)
  - C-style for loops (execute_c_style_for)
  - Case statements (execute_case)
  - Select loops (execute_select)
  - Break statements (execute_break)
  - Continue statements (execute_continue)
- Extracted helper methods:
  - _expand_for_loop_items: Handles expansion for for loops
  - _expand_select_items: Handles expansion for select loops
  - _expand_single_item: Common expansion logic
  - _word_split_and_glob: Field splitting and glob expansion
  - _convert_case_pattern_for_fnmatch: Pattern conversion for case
  - _display_select_menu: Menu display for select
- Removed ~539 lines from core.py
- All control flow tests passing

The ControlFlowExecutor provides:
- Complete control structure execution
- Proper loop depth tracking
- Exception-based flow control (break/continue)
- Redirection handling for control structures
- Pipeline context management
- Clean separation from visitor logic

Code reduction achieved:
- Removed visit_IfConditional (~27 lines)
- Removed visit_WhileLoop (~33 lines)
- Removed visit_ForLoop (~125 lines)
- Removed visit_CaseConditional (~47 lines)
- Removed visit_CStyleForLoop (~54 lines)
- Removed visit_SelectLoop (~170 lines)
- Removed visit_BreakStatement (~7 lines)
- Removed visit_ContinueStatement (~7 lines)
- Removed _convert_case_pattern_for_fnmatch (~47 lines)
- Removed _display_select_menu (~22 lines)
- Total: ~539 lines of control flow code removed from core.py

### Phase 6: Specialized Operations Extraction (Completed)
- Created ArrayOperationExecutor class in array.py
- Created FunctionOperationExecutor class in function.py  
- Created SubshellExecutor class in subshell.py
- Moved all specialized operations from ExecutorVisitor:
  - Array initialization (execute_array_initialization)
  - Array element assignment (execute_array_element_assignment)
  - Function definition (execute_function_def)
  - Subshell execution (execute_subshell)
  - Brace group execution (execute_brace_group)
- Extracted helper methods:
  - _add_expanded_element_to_array: Array element expansion
  - _is_explicit_array_assignment: Check for [i]=val syntax
  - _parse_explicit_array_assignment: Parse [i]=val syntax
  - _execute_in_subshell: Main subshell execution
  - _execute_foreground_subshell: Foreground subshell logic
  - _execute_background_brace_group: Background brace groups
- Removed ~395 lines from core.py
- All tests passing (except those requiring function execution)

The specialized executors provide:
- ArrayOperationExecutor: Complete array handling with expansion
- FunctionOperationExecutor: Function definition (execution in Phase 7)
- SubshellExecutor: Subshell and brace group execution with isolation

Code reduction achieved:
- Removed visit_ArrayInitialization (~64 lines)
- Removed visit_ArrayElementAssignment (~69 lines)
- Removed visit_FunctionDef (~4 lines)
- Removed visit_SubshellGroup (~3 lines)
- Removed visit_BraceGroup (~29 lines)
- Removed _add_expanded_element_to_array (~40 lines)
- Removed _is_explicit_array_assignment (~5 lines)
- Removed _parse_explicit_array_assignment (~20 lines)
- Removed _execute_in_subshell (~10 lines)
- Removed _execute_foreground_subshell (~66 lines)
- Removed _execute_background_brace_group (~35 lines)
- Removed _handle_array_assignment (~9 lines)
- Total: ~354 lines of specialized operation code removed from core.py

### Phase 7: Core Visitor Refactoring and Function Execution (Completed)
- Implemented full function execution in FunctionOperationExecutor
- Updated FunctionExecutionStrategy to use the function executor
- Fixed positional parameter handling ($0, $1, $2, etc.)
- Integrated with function_stack for return builtin support
- Cleaned up empty sections and debug code
- Final core.py size: 542 lines (down from ~1994)

Function execution implementation:
- Proper positional parameter setup (args only, not function name)
- Script name ($0) handling via state.script_name
- Function stack management for return builtin
- Context preservation and restoration
- Full compatibility with existing tests

Final statistics:
- **Original ExecutorVisitor**: ~1994 lines
- **Final core.py**: 542 lines
- **Total reduction**: 73% (1452 lines removed)
- **Modules created**: 7 specialized executors
- **All tests passing**: Complete compatibility maintained

The executor package is now fully refactored with:
1. **core.py** (542 lines) - Main visitor coordinating execution
2. **command.py** - Simple command execution with strategies
3. **pipeline.py** - Pipeline execution and process management
4. **control_flow.py** - Control structures (if, loops, case, etc.)
5. **array.py** - Array initialization and element operations
6. **function.py** - Function definition and execution
7. **subshell.py** - Subshell and brace group execution
8. **context.py** - Execution state management
9. **strategies.py** - Command execution strategies

Last updated: Phase 7 completed successfully - Refactoring complete!