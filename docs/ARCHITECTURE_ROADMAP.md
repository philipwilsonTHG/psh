# PSH Architecture Roadmap

This document outlines planned architectural improvements and enhancements for PSH (Python Shell). These items represent longer-term improvements that would enhance PSH's compatibility, performance, and educational value.

## Tokenizer/Lexer Improvements

### 1. Treat Unexpanded Braces as Single Word Tokens

**Current Behavior**: PSH tokenizes `{` and `}` as separate LBRACE and RBRACE tokens, even when they don't form a valid brace expansion. This causes `echo {}` to output `{ }` instead of `{}`.

**Proposed Change**: Modify the tokenizer to keep braces as part of WORD tokens when they don't form valid expansions.

**Rationale**:
- **Bash Compatibility**: Bash treats invalid brace patterns as literal text. Many scripts depend on this behavior.
- **Script Portability**: Scripts that work with literal braces (e.g., JSON generation, code templates) currently break in PSH.
- **User Expectations**: The principle of least surprise - users expect `echo {}` to output `{}`.
- **Consistency**: If braces don't expand, they should be treated like any other literal characters.

**Implementation Notes**:
- The tokenizer would need to look ahead to determine if `{...}` forms a valid brace expansion
- Valid patterns include: `{a,b,c}`, `{1..10}`, `{a..z}`, nested expansions
- Invalid patterns like `{}`, `{a}`, `{a..1}` should remain as literal text
- Function definitions `name() {}` would still need special handling

**Impact**: Low risk, well-contained change in the lexer layer. Would fix 4-6 failing brace expansion tests.

---

## Parser Enhancements

### 2. Support Command Groups in Pipelines

**Current State**: PSH cannot parse `{ cmd1; cmd2; } | cmd3` - brace groups aren't recognized as pipeline components.

**Proposed Change**: Extend parser to recognize brace groups as valid pipeline components.

**Rationale**:
- Common shell pattern for grouping commands without creating a subshell
- More efficient than `(cmd1; cmd2) | cmd3` which forks a new process
- Required for full POSIX compliance

---

## Expansion System Improvements

### 3. Implement Remaining Parameter Expansions

**Missing Features**:
- `${!var}` - Indirect expansion
- `${var@Q}` - Quote for reuse as input
- `${var@E}` - Expand escape sequences
- `${var@P}` - Expand as prompt string
- `${var@A}` - Assignment form
- `${var@a}` - Attributes

**Rationale**: Complete bash compatibility for parameter expansion.

---

## Process Management

### 4. Implement Coprocess Support

**Feature**: Support for `coproc` to create bidirectional pipes with background processes.

**Rationale**:
- Powerful feature for interactive process communication
- Educational value in demonstrating advanced IPC
- Bash compatibility for complex scripts

---

## Performance Optimizations

### 5. Implement Builtin Command Caching

**Current State**: Builtin lookup happens on every command execution.

**Proposed Change**: Cache builtin lookups after first resolution.

**Rationale**:
- Improve performance for script execution
- Reduce overhead in tight loops
- Still maintain ability to override with functions

---

## Error Handling

### 6. Enhanced Error Recovery in Parser

**Current State**: Parser stops on first error.

**Proposed Change**: Implement error recovery to continue parsing after errors.

**Rationale**:
- Better error messages showing multiple issues
- Useful for shell script linting
- Educational value in showing all problems at once

---

## Signal Handling

### 7. Complete Signal Handling (SIGWINCH, SIGPIPE)

**Missing Signals**:
- SIGWINCH - Terminal resize handling
- SIGPIPE - Broken pipe handling improvements
- Signal handling in arithmetic expressions

**Rationale**: Professional terminal behavior and robustness.

---

## Compatibility Features

### 8. Implement Extended Glob Patterns

**Features**: Support for `@()`, `*()`, `+()`, `?()`, `!()` patterns when `shopt -s extglob` is set.

**Rationale**:
- Common in modern bash scripts
- Powerful pattern matching capabilities
- Good educational example of parser extensions

---

## Architecture Refactoring

### 9. Plugin System for Builtins

**Concept**: Allow dynamic loading of builtin commands as plugins.

**Rationale**:
- Extensibility without modifying core
- Educational value in showing plugin architectures
- Easy way to add domain-specific builtins

---

## Testing Infrastructure

### 10. Improved Test Output Capture

**Current Issues**: Tests using forked processes have trouble capturing output.

**Proposed Solution**: Implement proper PTY-based testing infrastructure.

**Rationale**:
- Enable testing of interactive features
- Better subprocess output capture
- More reliable test suite

---

## Documentation

### 11. Interactive Tutorial Mode

**Concept**: Built-in interactive tutorial teaching shell concepts.

**Features**:
- Step-by-step lessons
- Practice exercises
- Progress tracking

**Rationale**: Enhance PSH's educational mission.

---

## Priority Guidelines

When considering implementation order:

1. **High Priority**: Changes that fix compatibility issues or enable common use cases
2. **Medium Priority**: Performance improvements and new features
3. **Low Priority**: Nice-to-have features that few scripts use

The unexpanded braces fix would be **Medium Priority** - it affects edge cases but improves compatibility and user experience.

---

## Contributing

When adding items to this roadmap:
1. Clearly describe current behavior and proposed change
2. Provide strong rationale (compatibility, performance, education)
3. Assess implementation complexity and impact
4. Consider backward compatibility
5. Link to relevant bug reports or feature requests