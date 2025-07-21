# CLAUDE.md

This guide helps AI assistants work effectively with the Python Shell (psh) codebase.

## Project Overview

Python Shell (psh) is an educational Unix shell implementation designed to teach shell internals through clean, readable Python code. It features:
- Hand-written recursive descent parser for clarity
- Component-based architecture with clear separation of concerns
- Comprehensive test suite 
- Near-complete POSIX compliance (~93% measured by conformance tests)
- Visitor pattern for AST operations
- Comprehensive conformance testing framework for POSIX/bash compatibility

## Quick Start Commands

```bash
# Run tests
python -m pytest tests/                    # Main test suite (3000+ tests)
python -m pytest tests/test_foo.py -v     # Specific test file
python -m pytest tests/unit/builtins/ -v  # Specific test category
python -m pytest -k "test_name" -xvs      # Specific test with output

# Run conformance tests (POSIX/bash compatibility)
cd tests/conformance
python run_conformance_tests.py           # Full conformance suite
python run_conformance_tests.py --posix-only    # POSIX compliance only
python run_conformance_tests.py --bash-only     # Bash compatibility only
python run_conformance_tests.py --summary-only  # Just show summary

# Run specific test categories  
python -m pytest tests/unit/              # Unit tests (builtins, expansion, lexer, parser)
python -m pytest tests/integration/       # Integration tests (pipelines, control flow)
python -m pytest tests/system/            # System tests (interactive, initialization)
python -m pytest tests/performance/       # Performance benchmarks

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

## Test Organization

PSH uses a modern, well-organized test suite:

### Main Test Suite (`tests/`)
- **Location**: `/tests/`
- **Count**: ~3000 tests
- **Status**: Modern, well-organized structure (migrated 2025)
- **Organization**:
  - `unit/` - Unit tests (builtins, expansion, lexer, parser)
  - `integration/` - Integration tests (pipelines, control flow, functions)
  - `system/` - System tests (interactive, initialization, scripts)
  - `performance/` - Performance benchmarks and stress tests
  - `conformance/` - POSIX/bash compatibility tests
- **Command**: `python -m pytest tests/`

### Legacy Test Suite (`tests_archived/`)
- **Location**: `/tests_archived/`
- **Status**: Archived legacy tests (pre-2025 migration)
- **Use**: Historical reference only
- **Note**: Superseded by modern test structure

### Conformance Testing Framework
- **Location**: `/tests/conformance/`
- **Purpose**: Measure POSIX compliance and bash compatibility
- **Features**:
  - Compares PSH output with bash for identical commands
  - Categorizes differences (identical, documented, extensions, bugs)
  - Generates detailed compliance reports
  - Current metrics: 93.1% POSIX compliance, 72.7% bash compatibility

### Test Selection Guidelines
- **Development work**: Use `/tests/` organized by category
- **Unit testing**: Use `tests/unit/` for component-specific tests
- **Integration testing**: Use `tests/integration/` for feature interaction tests
- **Compatibility verification**: Use `tests/conformance/` 
- **Performance analysis**: Use `tests/performance/`

## Critical Information

### To increment the system version after completing an enhancement:
1. Update the version number in psh/version.py
2. If appropriate, update the user's guide (docs/user_guide/*) with new features
3. If appropriate, update ARCHITECTURE.md and ARCHITECTURE.llm with architectural changes.
4. Commit changes in the git repo
5. Tag the commit with the new version

### Known Test Issues

1. **Interactive Test Limitations**: 
   - Interactive tests in `tests/system/interactive/` are currently skipped
   - Use pexpect but have process management issues
   - Marked with `pytest.mark.skip` until pexpect issues resolved

2. **Pytest Collection Best Practices**: 
   - Don't name source files starting with `test_` 
   - Don't name classes starting with `Test` unless they're actual test classes
   - These will confuse pytest's test collection

3. **I/O Redirection Tests**: 
   - Tests involving I/O redirection may conflict with pytest's output capture
   - Use PSH-compatible fixtures instead of pytest's capsys for complex redirection
   - Modern test suite has proper fixture isolation to handle this

4. **Legacy Test Issues (Resolved)**: 
   - Previous test isolation problems were resolved in 2025 migration
   - Legacy tests archived in `tests_archived/` for historical reference

### Common Tasks

**Add a new builtin:**
1. Create file in `psh/builtins/` (e.g., `mycommand.py`)
2. Inherit from `Builtin` class and implement `execute()` method
3. Add `@builtin` decorator to auto-register
4. Add tests in `tests/unit/builtins/` for new features (recommended)
5. Add conformance tests in `tests/conformance/` if POSIX/bash relevant

**Add a shell option (set -x, etc):**
1. Add to short_to_long mapping in `psh/builtins/environment.py` SetBuiltin
2. Add to `psh/core/state.py` options dictionary with default value
3. Implement behavior in relevant component (e.g., executor for xtrace)
4. Add tests in `tests/unit/builtins/` (recommended)

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

**Test Writing Guidelines**

Choose the right fixture based on test type:

1. **Unit Tests** (use `captured_shell`):
   - Testing builtin command output
   - Testing parser/lexer components  
   - Testing expansion logic
   - No file I/O or process spawning

2. **Integration Tests** (use `isolated_shell_with_temp_dir`):
   - Testing I/O redirection
   - Testing pipelines
   - Testing job control
   - File system operations

3. **System Tests** (use `subprocess`):
   - Testing full shell behavior
   - Comparing with bash
   - Testing process lifecycle
   - Interactive features (when possible)

**Output Capture Rules**:
1. NEVER use capsys with shell tests that do I/O redirection
2. ALWAYS use captured_shell for builtin output testing
3. PREFER subprocess.run for external command testing
4. AVOID mixing capture methods in the same test

**Example Patterns**:

```python
# Unit test with captured_shell
def test_echo_output(captured_shell):
    result = captured_shell.run_command("echo hello")
    assert result == 0
    assert captured_shell.get_stdout() == "hello\n"
    assert captured_shell.get_stderr() == ""

# Integration test with isolated shell
def test_file_redirection(isolated_shell_with_temp_dir):
    shell = isolated_shell_with_temp_dir
    shell.run_command("echo test > file.txt")
    
    # Read file directly, not through shell output
    import os
    with open(os.path.join(shell.state.variables['PWD'], 'file.txt')) as f:
        assert f.read() == "test\n"

# Conformance test with subprocess
def test_posix_compliance():
    import subprocess
    cmd = "echo $((1 + 1))"
    
    psh = subprocess.run([sys.executable, '-m', 'psh', '-c', cmd], 
                        capture_output=True, text=True)
    bash = subprocess.run(['bash', '-c', cmd], 
                         capture_output=True, text=True)
    
    assert psh.stdout == bash.stdout
```

**For conformance tests**:
- Add to `tests_new/conformance/posix/` or `tests_new/conformance/bash/`
- Inherit from `ConformanceTest` base class
- Use `assert_identical_behavior()` for exact PSH/bash matching
- Use `assert_documented_difference()` for known differences

**Best Practices**:
- Clear output between tests: `captured_shell.clear_output()`
- Check both stdout and stderr
- Always verify exit codes
- Use appropriate test markers (@pytest.mark.serial, @pytest.mark.isolated)

See `docs/test_pattern_guide.md` for comprehensive examples and patterns.

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