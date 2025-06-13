# Shell.py Refactoring Plan

## Executive Summary

The shell.py file has grown to 2,712 lines with 68 methods, exhibiting the "God Object" anti-pattern. This refactoring plan outlines a phased approach to decompose the monolithic Shell class into a clean component-based architecture while maintaining all functionality and test compatibility.

## Current State Analysis

### Size and Complexity
- **File**: 2,712 lines
- **Methods**: 68 methods in Shell class
- **Responsibilities**: 7+ major areas (execution, expansion, I/O, control flow, scripting, interactive, utilities)

### Existing Modular Components
The codebase already has some modular components that we can build upon:
- `AliasManager` - Alias management
- `FunctionManager` - Function definitions
- `JobManager` - Job control
- `LineEditor` / `MultiLineInputHandler` - Interactive editing
- `arithmetic.py` - Arithmetic expansion
- `brace_expansion.py` - Brace expansion
- `builtins/` - Modular builtin system with registry

## Proposed Architecture

```
psh/
├── shell.py                    # Slim orchestrator (~300 lines)
├── core/
│   ├── __init__.py
│   ├── state.py               # Shell state container
│   └── exceptions.py          # LoopBreak, LoopContinue, etc.
├── executor/
│   ├── __init__.py
│   ├── command.py             # Single command execution
│   ├── pipeline.py            # Pipeline execution
│   ├── control_flow.py        # if/while/for/case/break/continue
│   ├── function.py            # Function execution
│   └── process.py             # Process management, fork/exec
├── expansion/
│   ├── __init__.py
│   ├── manager.py             # ExpansionManager orchestrates all expansions
│   ├── variable.py            # Variable and parameter expansion
│   ├── command_sub.py         # Command substitution
│   ├── glob.py                # Glob pattern expansion
│   └── tilde.py               # Tilde expansion (already exists conceptually)
├── io_redirect/
│   ├── __init__.py
│   ├── manager.py             # IOManager for all redirection logic
│   ├── file_redirect.py       # File-based redirections
│   ├── heredoc.py             # Here documents and here strings
│   └── process_sub.py         # Process substitution
├── scripting/
│   ├── __init__.py
│   ├── runner.py              # Script execution orchestrator
│   ├── validator.py           # Script validation (binary detection, etc.)
│   ├── shebang.py             # Shebang parsing and execution
│   └── rc_loader.py           # RC file loading
├── interactive/
│   ├── __init__.py
│   ├── repl.py                # Main REPL loop
│   ├── history.py             # History management
│   └── signal_handler.py      # Signal handling
└── utils/
    ├── __init__.py
    ├── ast_formatter.py       # AST formatting for debug
    └── token_formatter.py     # Token formatting for debug
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. **Create core module structure**
   - Set up directory structure
   - Create `core/state.py` to hold shell state
   - Move exceptions to `core/exceptions.py`
   - Create base interfaces for each component

2. **Extract ShellState class**
   ```python
   class ShellState:
       def __init__(self):
           self.env = {}
           self.variables = {}
           self.positional_params = []
           self.last_exit_code = 0
           self.script_name = "psh"
           # ... etc
   ```

3. **Update tests to use new imports**
   - Update import statements as we move code
   - Ensure all tests continue to pass

### Phase 2: Expansion System (Week 1-2)
1. **Create ExpansionManager**
   - Central orchestrator for all expansions
   - Maintains proper expansion order
   - Handles interaction between different expansion types

2. **Extract expansion methods**
   - `_expand_string_variables()` → `expansion/variable.py`
   - `_expand_variable()` → `expansion/variable.py`
   - `_expand_tilde()` → `expansion/tilde.py`
   - `_execute_command_substitution()` → `expansion/command_sub.py`
   - Glob expansion logic → `expansion/glob.py`

3. **Create clean interfaces**
   ```python
   class ExpansionManager:
       def __init__(self, shell_state):
           self.state = shell_state
           self.variable_expander = VariableExpander(shell_state)
           self.command_sub = CommandSubstitution(shell_state)
           # ...
       
       def expand_arguments(self, command):
           # Orchestrate expansions in correct order
   ```

### Phase 3: I/O Redirection (Week 2)
1. **Create IOManager**
   - Centralize all redirection logic
   - Handle both builtin and external command redirections

2. **Extract redirection methods**
   - `_apply_redirections()` → `io_redirect/manager.py`
   - `_restore_redirections()` → `io_redirect/manager.py`
   - `_setup_builtin_redirections()` → `io_redirect/manager.py`
   - `_setup_child_redirections()` → `io_redirect/manager.py`
   - Process substitution logic → `io_redirect/process_sub.py`
   - Heredoc handling → `io_redirect/heredoc.py`

3. **Simplify redirection handling**
   ```python
   class IOManager:
       def with_redirections(self, redirects, func):
           """Context manager for applying redirections"""
           saved = self.apply_redirections(redirects)
           try:
               return func()
           finally:
               self.restore_redirections(saved)
   ```

### Phase 4: Executor Components (Week 2-3)
1. **Create CommandExecutor**
   - Single command execution logic
   - Builtin vs external command dispatch
   - Variable assignment handling

2. **Create PipelineExecutor**
   - Pipeline setup and execution
   - Process group management
   - Job control integration

3. **Create ControlFlowExecutor**
   - All control structures (if/while/for/case)
   - Break/continue handling
   - Enhanced test statement execution

4. **Extract execution methods**
   - `execute_command()` → `executor/command.py`
   - `execute_pipeline()` → `executor/pipeline.py`
   - `execute_if_statement()` → `executor/control_flow.py`
   - `execute_while_statement()` → `executor/control_flow.py`
   - `execute_for_statement()` → `executor/control_flow.py`
   - `execute_case_statement()` → `executor/control_flow.py`
   - Process management → `executor/process.py`

### Phase 5: Script Handling (Week 3)
1. **Create ScriptRunner**
   - Main script execution orchestrator
   - Input source management

2. **Extract script methods**
   - `run_script()` → `scripting/runner.py`
   - `_validate_script_file()` → `scripting/validator.py`
   - `_is_binary_file()` → `scripting/validator.py`
   - Shebang handling → `scripting/shebang.py`
   - RC file loading → `scripting/rc_loader.py`

### Phase 6: Interactive Features (Week 3-4)
1. **Create InteractiveShell**
   - REPL loop management
   - Prompt handling
   - Signal management

2. **Extract interactive methods**
   - `interactive_loop()` → `interactive/repl.py`
   - History methods → `interactive/history.py`
   - Signal handlers → `interactive/signal_handler.py`

### Phase 7: Final Integration (Week 4)
1. **Refactor Shell class**
   - Reduce to orchestrator role
   - Clean component initialization
   - Simple delegation methods

2. **Final Shell class structure**
   ```python
   class Shell:
       def __init__(self, ...):
           self.state = ShellState(...)
           self.expansion = ExpansionManager(self.state)
           self.io_manager = IOManager(self.state)
           self.executor = ExecutorManager(self.state)
           self.script_runner = ScriptRunner(self)
           self.interactive = InteractiveShell(self)
       
       def run_command(self, command_string):
           """Main entry point"""
           tokens = tokenize(command_string)
           tokens = self.alias_manager.expand_aliases(tokens)
           ast = parse(tokens)
           return self.executor.execute(ast)
   ```

## Testing Strategy

### Continuous Testing
- Run full test suite after each extraction
- Create integration tests for new components
- Maintain backward compatibility throughout

### Test Updates
- Update imports incrementally
- Create test helpers for component testing
- Add component-level unit tests

### Regression Prevention
- Keep old methods as delegates initially
- Gradual deprecation with warnings
- Final removal only after verification

## Benefits

### Immediate Benefits
1. **Better Code Organization** - Easy to find functionality
2. **Improved Testability** - Components can be tested in isolation
3. **Easier Debugging** - Clear boundaries between components
4. **Parallel Development** - Multiple developers can work on different components

### Long-term Benefits
1. **Extensibility** - New features as new components
2. **Maintainability** - Changes localized to specific modules
3. **Educational Value** - Each component teaches specific concepts
4. **Performance** - Opportunity to optimize individual components

## Risk Mitigation

### Backward Compatibility
- Keep Shell API stable
- Use delegation pattern initially
- Gradual migration of functionality

### Test Coverage
- Ensure 100% test pass rate at each phase
- Add new tests for components
- Integration tests for component interaction

### Documentation
- Update docstrings as we refactor
- Create component documentation
- Maintain CLAUDE.md accuracy

## Success Metrics

1. **Code Metrics**
   - Shell.py reduced from 2,712 to ~300 lines
   - Average component size < 500 lines
   - Clear single responsibility per component

2. **Quality Metrics**
   - All tests passing
   - No performance regression
   - Improved code coverage

3. **Developer Experience**
   - Easier to understand codebase
   - Faster feature development
   - Clearer debugging paths

## Next Steps

1. **Review and Approval** - Team review of this plan
2. **Create Branch** - `refactor/shell-decomposition`
3. **Phase 1 Implementation** - Core infrastructure
4. **Incremental PRs** - One phase per PR
5. **Documentation Updates** - Keep docs in sync

## Conclusion

This refactoring will transform shell.py from a monolithic God Object into a clean, modular architecture. The phased approach ensures we maintain functionality while improving code quality. The investment in refactoring will pay dividends in maintainability, testability, and educational value.