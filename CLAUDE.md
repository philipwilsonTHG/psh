# CLAUDE.md

This guide helps AI assistants work effectively with the Python Shell (psh) codebase.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed to teach shell internals through clean, readable Python code. It features:
- Hand-written recursive descent parser for clarity
- Component-based architecture with clear separation of concerns
- Comprehensive test suite (1600+ tests)
- Near-complete POSIX compliance (~93-95%)
- Visitor pattern for AST operations

## Quick Start Commands

```bash
# Run tests
python -m pytest tests/                    # Full test suite
python -m pytest tests/test_foo.py -v     # Specific test file
python -m pytest -k "test_name" -xvs      # Specific test with output

# Run psh
python -m psh                              # Interactive shell
python -m psh script.sh                    # Run script
python -m psh -c "echo hello"             # Run command

# Debug options
python -m psh --debug-ast                  # Show AST before execution
python -m psh --debug-tokens              # Show tokenization
python -m psh --debug-expansion           # Trace expansions
python -m psh --validate script.sh        # Validate without executing
```

## Critical Information

### To increment the system version after completing an enhancement:
1. Update the version number in psh/version.py
2. If appropriate, update the user's guide (docs/user_guide/*) with new features
3. If appropriate, update ARCHITECTURE.md and ARCHITECTURE.llm with architectural changes.
4. Commit changes in the git repo
5. Tag the commit with the new version

### Known Test Issues
1. **Test Isolation Problem**: ~20 tests fail when run in full suite but pass individually
   - Caused by test pollution affecting subprocess execution
   - Tests using `subprocess.run([sys.executable, '-m', 'psh', ...])` are affected
   - Workaround: Run failing tests individually
   - Fixed 6 bash comparison tests by adding PYTHONPATH to subprocess environment

2. **Pytest Collection Conflicts**: 
   - Don't name source files starting with `test_` 
   - Don't name classes starting with `Test` unless they're actual test classes
   - These will confuse pytest's test collection

3. **File Descriptor Tests**: 
   - Tests involving I/O redirection may conflict with pytest's output capture
   - Use `MockStdout` pattern from test_shell_options.py for reliable output capture

### Common Tasks

**Add a new builtin:**
1. Create file in `psh/builtins/` (e.g., `mycommand.py`)
2. Inherit from `Builtin` class and implement `execute()` method
3. Add `@builtin` decorator to auto-register
4. Add tests in `tests/test_builtins.py` or dedicated test file

**Add a shell option (set -x, etc):**
1. Add to short_to_long mapping in `psh/builtins/environment.py` SetBuiltin
2. Add to `psh/core/state.py` options dictionary with default value
3. Implement behavior in relevant component (e.g., executor for xtrace)
4. Add tests in `tests/test_shell_options.py`

**Modify parser:**
1. Add tokens to `psh/token_types.py` if needed
2. Update `psh/lexer/` package for new tokens (core.py for main logic, constants.py for new token constants)
3. Add AST nodes to `psh/ast_nodes.py`
4. Update `psh/parser.py` with parsing logic
5. Implement visitor methods in `psh/visitor/executor_visitor.py`

## Architecture Quick Reference

### Key Files
- `psh/shell.py` - Main orchestrator (~500 lines)
- `psh/parser.py` - Recursive descent parser
- `psh/lexer/` - Modular tokenizer package with mixin architecture
- `psh/visitor/executor_visitor.py` - Main execution engine
- `psh/core/state.py` - Central state management
- `psh/expansion/manager.py` - Orchestrates all expansions

### Component Managers
Each manager handles a specific aspect:
- `ExpansionManager` - Variable, command substitution, globs, etc.
- `IOManager` - Redirections, pipes, heredocs
- `JobManager` - Background jobs, job control
- `FunctionManager` - Shell function definitions
- `AliasManager` - Shell aliases

### Execution Flow
```
Input → Line Continuation → Tokenization → Parsing → AST → Expansion → Execution
```

## Development Guidelines

### Testing
- Use the global `shell` fixture from `conftest.py`
- Test with `shell.run_command()` not direct method calls
- For subprocess tests, use absolute paths and explicit working directory
- Remember: builtin output goes to `shell.stdout`, not captured by print()

### Code Patterns
```python
# Builtin implementation
@builtin
class MyBuiltin(Builtin):
    name = "mybuiltin"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        # Validate args
        if len(args) < 2:
            self.error("not enough arguments", shell)
            return 1
        # Do work
        return 0

# Visitor implementation  
class MyVisitor(ASTVisitor[T]):
    def visit_SimpleCommand(self, node: SimpleCommand) -> T:
        # Process node
        return result
```

### Error Handling
- Use `self.error()` in builtins for consistent error messages
- Return appropriate exit codes (0=success, 1=general error, 2=usage error)
- For control flow, use exceptions (LoopBreak, LoopContinue, FunctionReturn)

## Current Development Status

**Version**: 0.58.0 (see version.py for detailed history)

**Recent Work**:
- **Lexer Package Refactoring (v0.58.0)**: Transformed monolithic 1500+ line lexer into modular package
  - Clean modular design with 7 focused components
  - Mixin-based architecture with LexerHelpers and StateHandlers
  - Clean separation: core logic, helpers, state handlers, constants, Unicode support
  - Direct imports from `psh.lexer` package with clean API
- POSIX set builtin options implemented (-a, -b, -C, -f, -n, -v)
- Wait builtin completed for job synchronization  
- Trap builtin with signal handling
- File descriptor duplication fixes

**Active Issues**:
- Test isolation problems with subprocess tests
- Some bash comparison tests fail due to parser limitations
- Command substitution output capture in test environment

## Debugging Tips

1. **Import Errors**: Clear `__pycache__` directories if you see module import issues
2. **Test Failures**: Run failing tests individually to check for test pollution
3. **Parser Issues**: Use `--debug-ast` and `--debug-tokens` to see parsing details
4. **Expansion Issues**: Use `--debug-expansion` to trace variable/command expansion

## Resources

- **Architecture**: See ARCHITECTURE.llm for detailed component guide
- **POSIX Compliance**: See docs/posix/posix_compliance_summary.md
- **Version History**: See version.py for detailed changelog
- **Test Patterns**: See tests/test_shell_options.py for good examples

## Important Notes

- Use `tmp/` subdirectory for temporary files, not system `/tmp`
- The visitor executor is now the default (legacy executor was removed)
- All source code has been written by Claude using Sonnet 4 and Opus 4 models
- Educational focus means clarity over performance in implementation choices

## Development Principles

- If we assert that a feature of psh is POSIX or bash conformant in the user's guide (docs/user_guide/*) then we must have a test in conformance_tests which proves it.