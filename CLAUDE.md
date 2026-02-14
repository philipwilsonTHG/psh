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
# Run tests (RECOMMENDED - uses smart test runner)
# IMPORTANT: Always redirect full test output to a file so you can inspect
# failures without re-running the entire suite:
python run_tests.py > tmp/test-results.txt 2>&1; tail -15 tmp/test-results.txt
# If failures are found, grep the saved file instead of re-running:
#   grep FAILED tmp/test-results.txt
#   grep -A 10 "FAILURES" tmp/test-results.txt

python run_tests.py --quick                # Fast tests only
python run_tests.py --parallel             # Parallel mode (~10x faster)
python run_tests.py --parallel 8           # Parallel with 8 workers
python run_tests.py --all-nocapture        # Simple mode - run all with -s

# Run tests manually (for specific scenarios)
python -m pytest tests/                    # Most tests (note: subshell tests will fail)
python -m pytest tests/integration/subshells/ -s  # Subshell tests (MUST use -s)
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
python -m psh --debug-exec                 # Debug executor (process groups, signals)
python -m psh --validate script.sh        # Validate without executing
```

## Test Organization

PSH uses a modern, well-organized test suite:

### Main Test Suite (`tests/`)
- **Location**: `/tests/`
- **Count**: ~3,450 tests
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

### Testing the Combinator Parser

The combinator parser (`psh/parser/combinators/`) is an experimental alternative
to the production recursive descent parser.  The existing test suite can be
re-run against it to measure coverage and find regressions.

**How parser selection works at test time**

Set the `PSH_TEST_PARSER` environment variable to `combinator`.  The `Shell`
constructor reads this variable and switches the active parser for all
commands executed during the test run.  No test code changes are needed.

**Running the full suite with the combinator parser**

```bash
# Via the smart test runner (recommended)
python run_tests.py --combinator > tmp/combinator-results.txt 2>&1
tail -15 tmp/combinator-results.txt

# Via pytest directly (must exclude subshell tests manually)
PSH_TEST_PARSER=combinator python -m pytest tests/ \
  --ignore=tests/integration/subshells/ \
  --ignore=tests/integration/functions/test_function_advanced.py \
  --ignore=tests/integration/variables/test_variable_assignment.py \
  -q --tb=line > tmp/combinator-results.txt 2>&1
tail -5 tmp/combinator-results.txt
```

**Running a specific test or file with the combinator parser**

```bash
PSH_TEST_PARSER=combinator python -m pytest tests/integration/control_flow/test_case_statements.py -xvs
PSH_TEST_PARSER=combinator python -m pytest -k "test_for_loop" -xvs
```

**Combinator-specific unit tests**

Direct unit tests for the combinator modules live in
`tests/unit/parser/combinators/`.  These test parser internals (token matching,
AST construction) without going through the shell:

```bash
python -m pytest tests/unit/parser/combinators/ -v
```

**Comparing before/after a change**

When fixing combinator bugs, capture failure lists before and after to verify
no regressions:

```bash
# Before: save baseline failures
PSH_TEST_PARSER=combinator python -m pytest tests/ \
  --ignore=tests/integration/subshells/ -q --tb=line 2>&1 \
  | grep "^FAILED" | sort > tmp/before-failures.txt

# ... make changes ...

# After: save new failures and diff
PSH_TEST_PARSER=combinator python -m pytest tests/ \
  --ignore=tests/integration/subshells/ -q --tb=line 2>&1 \
  | grep "^FAILED" | sort > tmp/after-failures.txt

comm -23 tmp/before-failures.txt tmp/after-failures.txt  # Fixed tests
comm -13 tmp/before-failures.txt tmp/after-failures.txt  # New regressions (should be empty)
```

**Always verify the recursive descent parser is unaffected**

After changing combinator code, confirm the production parser still passes:

```bash
python -m pytest tests/behavioral/test_golden_behavior.py -q --tb=line
python -m pytest tests/unit/parser/ -q --tb=line
```

**Interactive testing**

You can switch parsers inside a running psh session:

```bash
python -m psh --parser combinator         # Start with combinator
python -m psh --parser rd                 # Start with recursive descent (default)
# Or switch at runtime:
parser-select combinator                  # Inside psh REPL
parser-select rd                          # Switch back
```

**Known exclusions in combinator mode**

The test runner ignores these directories because the combinator parser does
not yet handle the features they exercise (subshell FD inheritance, advanced
function scoping, complex variable assignment):

- `tests/integration/subshells/`
- `tests/integration/functions/test_function_advanced.py`
- `tests/integration/variables/test_variable_assignment.py`

**Current combinator parser test status**: 0 remaining failures out of ~3,350
tests (as of v0.171.0).  See `docs/guides/combinator_parser_remaining_failures.md`
for history.

**Lint**

Always lint combinator code after changes:

```bash
ruff check psh/parser/combinators/
```

## Critical Information

### To increment the system version after completing an enhancement:
1. Update `psh/version.py`: bump `__version__`; add a new entry to `CHANGELOG.md`
2. Update the version string in **all** of these files (they must always match):
   - `README.md` — the `**Current Version**:` line
   - `ARCHITECTURE.md` — the `**Current Version**:` line
   - `ARCHITECTURE.llm` — the `Version:` line
   - `CLAUDE.md` — the `**Version**:` line in "Current Development Status"
3. If the change affects any of the following, update the relevant docs:
   - **Test count or file count** → `README.md` "Project Statistics" section and
     `CLAUDE.md` test count
   - **New features or user-visible behavior** → `docs/user_guide/*`
   - **Architectural changes** (new subsystems, changed execution flow, new
     component managers) → `ARCHITECTURE.md` and `ARCHITECTURE.llm`
   - **Recent Development** milestones → `README.md` "Recent Development" section
     (keep the 10 most notable entries)
   - **Development status** summary → `CLAUDE.md` "Current Development Status"
     "Recent Work" section
4. Commit changes in the git repo
5. Tag the commit with the new version

### Architecture documentation files and what they contain

These files have version-stamped metadata that must stay in sync:

| File | Contains | Key metadata |
|------|----------|-------------|
| `psh/version.py` | Canonical version | `__version__` |
| `CHANGELOG.md` | Detailed version history | `## VERSION` entries |
| `README.md` | User-facing overview | Version, test count, LOC, file count, recent development |
| `ARCHITECTURE.md` | Detailed architecture guide | Version |
| `ARCHITECTURE.llm` | LLM-optimized architecture | Version |
| `CLAUDE.md` | AI assistant working guide | Version, test count, recent work summary |

### Known Test Issues

1. **Subshell Tests Require Special Handling** (IMPORTANT):
   - Tests in `tests/integration/subshells/` MUST be run with pytest's `-s` flag
   - Reason: Pytest's output capture interferes with file descriptor operations in forked child processes
   - When PSH forks for a subshell and redirects to a file, the child inherits pytest's capture objects instead of real file descriptors
   - **Solution**: Use the provided test runner (`python run_tests.py`) which handles this automatically
   - **Manual workaround**: `python -m pytest tests/integration/subshells/ -s`
   - Affected tests: ~43 subshell tests + some function/variable tests
   - Status: All functionality works correctly; this is purely a test infrastructure issue
   - Documentation: See `tests/integration/subshells/README.md` for detailed explanation

2. **Interactive Test Limitations**:
   - Interactive tests in `tests/system/interactive/` are currently skipped
   - Use pexpect but have process management issues
   - Marked with `pytest.mark.skip` until pexpect issues resolved

3. **Pytest Collection Best Practices**:
   - Don't name source files starting with `test_`
   - Don't name classes starting with `Test` unless they're actual test classes
   - These will confuse pytest's test collection

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
2. Update `psh/lexer/` package for new tokens (modular_lexer.py for main logic, constants.py for new token constants)
3. Add AST nodes to `psh/ast_nodes.py`
4. Update the appropriate module in `psh/parser/recursive_descent/parsers/`
5. Implement visitor methods in `psh/executor/core.py` (or the relevant specialized executor)

## Architecture Quick Reference

### Subsystem Documentation

Each major subsystem has its own CLAUDE.md with detailed guidance:

| Subsystem | Location | Purpose |
|-----------|----------|---------|
| **Lexer** | `psh/lexer/CLAUDE.md` | Tokenization, recognizers, quote/expansion parsing |
| **Parser** | `psh/parser/CLAUDE.md` | Recursive descent parsing, AST construction |
| **Executor** | `psh/executor/CLAUDE.md` | Command execution, process management, control flow |
| **Expansion** | `psh/expansion/CLAUDE.md` | Variable, command, tilde, glob expansion |
| **Core/State** | `psh/core/CLAUDE.md` | Shell state, variables, scopes, options |
| **Builtins** | `psh/builtins/CLAUDE.md` | Built-in commands, registration, adding new builtins |
| **I/O Redirect** | `psh/io_redirect/CLAUDE.md` | Redirections, heredocs, process substitution |
| **Visitor** | `psh/visitor/CLAUDE.md` | AST visitor pattern, traversal, transformation |
| **Interactive** | `psh/interactive/CLAUDE.md` | REPL, job control, history, completion |

These provide focused documentation for working within each subsystem.

### Key Files
- `psh/shell.py` - Main orchestrator (~316 lines)
- `psh/parser/` - Recursive descent parser package
- `psh/lexer/` - Modular tokenizer package with recognizer architecture
- `psh/executor/` - Execution engine with visitor pattern
- `psh/core/state.py` - Central state management
- `psh/expansion/manager.py` - Orchestrates all expansions

### Component Managers
Each manager handles a specific aspect:
- `ExpansionManager` - Variable, command substitution, globs, etc.
- `IOManager` - Redirections, pipes, heredocs
- `JobManager` - Background jobs, job control
- `ProcessLauncher` - Unified process creation with proper job control (NEW in v0.103.0)
- `FunctionManager` - Shell function definitions
- `AliasManager` - Shell aliases

### Process Execution Architecture
PSH uses a unified process creation system for all forked processes:
- **ProcessLauncher** (`psh/executor/process_launcher.py`) - Single source of truth for all process creation
- **ProcessRole Enum**: SINGLE, PIPELINE_LEADER, PIPELINE_MEMBER
- **ProcessConfig**: Configuration for launch (role, pgid, foreground, sync pipes, I/O setup)
- **Benefits**: Eliminates code duplication, consistent signal handling, centralized job control
- **Used by**: Pipelines, external commands, builtins (background), subshells, brace groups

### Word AST (SimpleCommand Arguments)
The parser always builds **Word AST nodes** for command arguments. Each
`SimpleCommand.words` list contains `Word` objects with `LiteralPart` and
`ExpansionPart` nodes carrying per-part quote context (`quoted`, `quote_char`).

As of v0.120.0, `words` is the **sole** argument metadata representation.
The legacy `arg_types`/`quote_types` string lists have been removed.
Use Word helper properties for semantic queries:

| Property | Replaces | Purpose |
|----------|----------|---------|
| `word.is_quoted` | `arg_type == 'STRING'` | True if wholly quoted |
| `word.is_unquoted_literal` | `arg_type == 'WORD'` | Plain unquoted word |
| `word.is_variable_expansion` | `arg_type == 'VARIABLE'` | Single `$VAR` expansion |
| `word.has_expansion_parts` | checking for expansion types | Any expansion present |
| `word.has_unquoted_expansion` | unquoted + `$` in arg | Vulnerable to splitting |
| `word.effective_quote_char` | `quote_types[i]` | The quote char (`'`, `"`, `$'`, or None) |

### Execution Flow
```
Input → Line Continuation → Tokenization → Parsing → AST → Expansion → Execution
                                                                         ↓
                                                                   ProcessLauncher
                                                                   (fork + job control)
```

## Development Guidelines

### Testing

**Running Tests Efficiently**

When running the full test suite or any large test run, always redirect output to a file so you can inspect results without re-running:

```bash
# Good: save output, then inspect
python run_tests.py > tmp/test-results.txt 2>&1; tail -15 tmp/test-results.txt
grep FAILED tmp/test-results.txt          # List failures
grep -B 5 "AssertionError" tmp/test-results.txt  # See assertion details

# Bad: piping to tail loses output, forcing a second run to find failures
python run_tests.py 2>&1 | tail -15
# ...then having to re-run to grep for FAILED
```

The same applies to `pytest` runs — redirect to a file first, then inspect:

```bash
python -m pytest tests/unit/ > tmp/unit-results.txt 2>&1; tail -20 tmp/unit-results.txt
```

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
   - Testing subshells
   - File system operations
   - **IMPORTANT**: Tests with subshells + file redirections MUST be run with `-s` flag
   - Use the test runner (`python run_tests.py`) to handle this automatically

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
- Add to `tests/conformance/posix/` or `tests/conformance/bash/`
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

**Version**: 0.186.0 (see CHANGELOG.md for detailed history)

**Recent Work**:
- **Move create_parser to parser package (v0.186.0)**:
  - Moved `create_parser()` from `psh/utils/parser_factory.py` to
    `psh/parser/__init__.py`; deleted `parser_factory.py`
  - Changed signature to take explicit `active_parser` and `trace_parsing`
    arguments instead of the whole `shell` object
  - Updated parser `__all__` (5 → 6 items), utils `__all__` (10 → 9 items)
- **Core Public API Cleanup (v0.185.0)**:
  - Rewrote `__init__.py`: added module docstring, 7 new imports
    (`ExpansionError`, `OptionHandler`, `TrapManager`, `is_valid_assignment`,
    `extract_assignments`, `is_exported`); updated `__all__` from 11 to 18
  - Fixed 43 bypass imports across 16 files (exceptions, variables, options,
    trap_manager, assignment_utils, state) to use package-level imports
  - Removed stale `scope.py` row from `core/CLAUDE.md`
- **Builtins Public API Cleanup (v0.184.0)**:
  - Populated `__init__.py` with `FunctionReturn` and `PARSERS` imports;
    updated `__all__` from 3 to 5 items; added module-level docstring
  - Fixed 7 bypass imports across 6 files (`core.py`, `function.py`,
    `command.py`, `strategies.py` x2, `pipeline.py`, `__main__.py`) to
    use package-level imports
  - Corrected 6 command-to-file mapping errors in `builtins/CLAUDE.md`
- **Utils Public API Cleanup (v0.183.0)**:
  - Populated `__init__.py` with `__all__` (11 items), imports, and docstring;
    all public symbols now importable from `psh.utils` directly
  - Deleted ~103 lines of dead code from `signal_utils.py`: `block_signals()`,
    `restore_default_signals()` context managers, and
    `SignalNotifier.has_notifications()` (zero callers each)
  - Fixed 4 bypass imports in `signal_manager.py`, `function_support.py`,
    `source_processor.py`, `debug_control.py` to use package-level imports
- **Executor Public API Cleanup (v0.182.0)**:
  - Trimmed `__all__` from 13 to 5 items; removed 10 items
    (`PipelineContext`, `PipelineExecutor`, `CommandExecutor`,
    `ControlFlowExecutor`, `ArrayOperationExecutor`,
    `FunctionOperationExecutor`, `SubshellExecutor`,
    `ExecutionStrategy`, `BuiltinExecutionStrategy`,
    `FunctionExecutionStrategy`) that remain importable as convenience imports
  - Added 2 missing items: `apply_child_signal_policy` and
    `TestExpressionEvaluator` (both have production callers)
  - Fixed 5 bypass imports in 4 files (`command_builtin.py`, `shell.py`,
    `command_sub.py`, `process_sub.py`) to use package-level imports
  - Fixed `__init__.py` docstring: removed non-existent modules
    (`arithmetic`, `utils`); added `strategies`, `process_launcher`,
    `child_policy`, `test_evaluator`
- **Visitor Public API Cleanup (v0.181.0)**:
  - Trimmed `__all__` from 14 to 9 items; removed 5 Tier 3 items
    (`ASTTransformer`, `ValidatorVisitor`, `LinterConfig`, `LintLevel`,
    `SecurityIssue`) that remain importable as convenience imports
  - Deleted unused `ASTTransformer` and `CompositeVisitor` classes from
    `base.py` (~105 lines); zero subclasses or external callers
  - Fixed 7 bypass imports (`from psh.visitor.base import ASTVisitor` →
    `from psh.visitor import ASTVisitor`) across executor and parser
    visualization modules
  - Deduplicated `BASH_BUILTINS` in `MetricsVisitor`; replaced with
    `SHELL_BUILTINS` import from `constants.py`
  - Updated `visitor/CLAUDE.md`: fixed return type table, added
    `constants.py` to key files, removed ASTTransformer/CompositeVisitor
    documentation sections
- **Expansion Public API Cleanup (v0.180.0)**:
  - Populated `__init__.py` with `ExpansionManager` import and `__all__`;
    added `contains_extglob`/`match_extglob` convenience imports
  - Updated `shell.py` to use package-level import
  - Fixed broken `ArithmeticEvaluator` import in `function_support.py`
    (wrong module path and wrong constructor argument)
  - Eliminated redundant `VariableExpander` construction (2 sites in
    `shell_state.py`); replaced with `shell.expansion_manager`
  - Eliminated redundant `WordSplitter` construction in `control_flow.py`
  - Updated `expansion/CLAUDE.md`: removed stale `base.py` references;
    rewrote "Adding a New Expansion Type" section
- **I/O Redirect Public API Cleanup (v0.179.0)**:
  - Populated `__init__.py` with `IOManager` import and `__all__`
  - Deleted 5 dead `IOManager` methods (~55 lines) and 3 dead
    `HeredocHandler` methods (~82 lines) plus unused imports
  - Consolidated `_dup2_preserve_target` as module-level function
  - Extracted `_expand_redirect_target`, `_check_noclobber` helpers
  - Moved saved FD state from Shell to `FileRedirector`
  - Initialized `_saved_fds_list` in `__init__` (removed `hasattr` guards)
  - Added 6 per-type redirect helpers (`_redirect_input_from_file`,
    `_redirect_heredoc`, `_redirect_herestring`, `_redirect_output_to_file`,
    `_redirect_dup_fd`, `_redirect_close_fd`)
  - Rewrote `apply_redirections`, `apply_permanent_redirections`,
    `setup_child_redirections`, `setup_builtin_redirections` to use helpers
- **Parser Public API Cleanup (v0.178.0)**:
  - Trimmed `__all__` from 17 to 5 items; demoted Tier 2 to convenience
    imports; removed Tier 3 from package-level `__all__`; deleted
    `factory.py` (6 functions); trimmed `context_factory.py` from 8 to 1
    function; deleted `parse_strict_posix`/`parse_permissive`; fixed
    bypass imports in `parse_tree.py` and `parser_factory.py`
- **Lexer Public API Cleanup (v0.177.0)**:
  - Trimmed `__all__` from 27 to 5 items; demoted Tier 2 to convenience
    imports; removed Tier 3 from package-level imports; replaced
    `isinstance(token, RichToken)` with `token.parts`; deleted stale
    `__version__`; added API reference doc
## Debugging Tips

1. **Import Errors**: Clear `__pycache__` directories if you see module import issues
2. **Test Failures**: Run failing tests individually to check for test pollution
3. **Parser Issues**: Use `--debug-ast` and `--debug-tokens` to see parsing details
4. **Expansion Issues**: Use `--debug-expansion` to trace variable/command expansion

## Resources

- **Architecture**: See ARCHITECTURE.llm for detailed component guide
- **POSIX Compliance**: See docs/posix/posix_compliance_summary.md
- **Version History**: See CHANGELOG.md for detailed changelog
- **Test Patterns**: See tests/test_shell_options.py for good examples

## Important Notes

- Use `tmp/` subdirectory for temporary files, not system `/tmp`
- The visitor executor is now the default (legacy executor was removed)
- All source code has been written by Claude using Sonnet 4 and Opus 4 models
- Educational focus means clarity over performance in implementation choices

## Development Principles

- If we assert that a feature of psh is POSIX or bash conformant in the user's guide (docs/user_guide/*) then we must have a test in conformance_tests which proves it.