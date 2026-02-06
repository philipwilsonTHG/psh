# Test Suite Review & Recommendations

**Date**: 2026-02-06
**Version**: 0.107.0

## Current State

| Metric | Value | Change from 0.97.0 |
|--------|-------|---------------------|
| Passed | 2,671 | +30 |
| Failed | 0 (1 intermittent race condition) | — |
| Skipped | 172 | — |
| XFail | 41 | -7 |
| POSIX Compliance | 98.4% | +1.5% |
| Bash Compatibility | 91.8% | +3.6% |

The test suite is in good shape -- zero real failures, well-organized structure, and clear categorization of expected issues. Items 1-6 from the original recommendations have been implemented in v0.107.0. All 4 conformance bugs from recommendation 7 have been resolved.

---

## Completed Recommendations (v0.107.0)

### ~~1. Reclassify `echo $$` conformance result~~ DONE

`echo $$` reclassified from `psh_bug` to `documented_difference` with ID `PROCESS_ID_DIFFERENCE`. Different PIDs is expected behavior since PSH and bash are separate processes.

### ~~2. Fix glob expansion on variable results~~ DONE

`PATTERN="*.txt"; echo $PATTERN` now correctly glob-expands after variable expansion per POSIX. Removed `VARIABLE` from the glob exclusion list in `_process_single_word()`. The `test_glob_with_variable` xfail has been removed.

### ~~3. Fix partial quoting in glob patterns~~ DONE

`echo "test"*.txt` now correctly expands the unquoted `*` while preserving the quoted `test` literal. Implemented using `\x00` markers to distinguish quoted vs unquoted glob characters in composite tokens, with proper handling for `${...}` expansion syntax so array subscripts are not affected. The `test_partial_quoting` xfail has been removed.

### ~~4. Move I/O-capture xfails to `-s` test phase~~ DONE

3 C-style for loop I/O redirection tests moved from xfail to Phase 3 of `run_tests.py` (run with `-s`). The alias test (`test_alias_with_arguments`) was left as xfail since it's a real non-interactive mode limitation, not an I/O capture issue.

### ~~5. Implement `shopt` builtin~~ DONE

Created `psh/builtins/shell_options.py` with full `shopt` implementation:
- Flags: `-s` (set), `-u` (unset), `-p` (print reusable), `-q` (query silently)
- Options: `dotglob`, `nullglob`, `extglob` (stub), `nocaseglob`, `globstar`
- Added `nullglob` support in glob expansion (no-match returns empty instead of literal)
- 16 tests in `tests/unit/builtins/test_shopt.py`

### ~~6. Add regression tests~~ DONE

Created `tests/regression/test_bug_fixes_4f4d854.py` with 12 tests covering:
- Command substitution trailing newline stripping
- IFS word splitting (whitespace vs non-whitespace delimiters)
- dotglob option behavior
- Comment recognition after `)` and `}` tokens

---

## Completed Recommendations (v0.107.0, 2026-02-06)

### ~~7. Fix Remaining Conformance Bugs (4 bugs)~~ DONE

All 4 `psh_bug` conformance items resolved:

- **`echo \$(echo test)`** -- Reclassified as `documented_difference` (ID: `ERROR_MESSAGE_FORMAT`). Both shells reject with exit code 2; only the error message format differs.
- **`sleep 1 & jobs`** -- Fixed job format string in `psh/job_control.py` to match bash: wider state field (24 chars), ` &` suffix for background jobs. Also fixed background job `+` marker by calling `register_background_job()` in `psh/executor/strategies.py` so `current_job` is properly set.
- **`history`** -- Fixed in `psh/shell.py` to only load history for interactive shells. Bash doesn't load persistent history in non-interactive mode (`bash -c 'history'` outputs nothing).
- **`pushd /tmp`** -- Fixed in `psh/builtins/directory_stack.py` to initialize the stack with the current directory before pushing the new one. `pushd /tmp` from `~` now produces stack `[/tmp, ~]` matching bash. Remaining output difference (different CWD paths) classified as `documented_difference` (ID: `PUSHD_CWD_DIFFERENCE`) since it's a test environment artifact.

---

## Completed Recommendations (v0.110.0, 2026-02-06)

### ~~8. Fix the Intermittent Race Condition~~ DONE

Fixed `_wait_for_all` in `psh/builtins/job_control.py` to collect exit statuses from already-completed jobs before waiting for running ones. Previously, if a background job (e.g. `false &`) completed and was reaped before `wait` was called, its exit status was lost because the `while` loop only iterated over non-DONE jobs. Now DONE jobs are checked first for their stored exit status, then removed. Verified stable over 20 consecutive runs.

---

## Remaining Recommendations

### 1. Reclassify Conformance Test Errors

9 conformance results are `test_error` but most are actually known missing features (extglob, exec FDs). They should be reclassified as `documented_difference` with appropriate notes, which would give a more accurate picture of actual compliance.

### 2. Implement `extglob` (Medium-term)

The `shopt` builtin now supports toggling `extglob`, but the glob expansion engine doesn't implement extended globbing patterns (`?(pattern)`, `*(pattern)`, etc.). Implementing this would resolve 2+ conformance test errors.

### 3. Fill Performance Test Gaps

- `tests/performance/memory/` and `tests/performance/stress/` are empty directories
- Consider adding memory and stress tests for expansion, parsing, and process creation

### 4. Interactive Test Strategy

119 tests behind `--run-interactive` and 20 requiring `pexpect`. These cover history, tab completion, line editing, and job control. Current options:
- Install `pexpect` and enable those 20 tests
- Fix PTY-based line editing to unblock the 10 skipped `test_line_editing.py` tests
- Consider running interactive tests in CI with a dedicated phase

---

## Detailed Breakdown

### Skipped Tests (172 total)

| Category | Count | Details |
|----------|-------|---------|
| Interactive (--run-interactive) | 119 | Completion, history, line editing, spawn tests |
| pexpect not installed | 20 | Line editing, history nav, tab completion |
| PTY-based tests | 19 | Job control, line editing via PTY |
| Parser combinator parity | 10 | select, arrays, redirections, heredocs, etc. |
| Advanced arithmetic TODO | 11 | Parameter expansion, brace expansion, nesting |
| Arithmetic integration | 6 | Here docs/strings with arithmetic |
| Other individual skips | 4 | Here doc functions, ANSI-C quoting, composite words, background subshell |
| Line editing | 1 | Cursor movement |

### XFail Tests (41 total)

#### By Classification

| Classification | Count | Description |
|----------------|-------|-------------|
| Test Infrastructure | 1 | Alias expansion in non-interactive mode |
| Missing Features | 2 | extglob, exec FDs |
| Design Differences | 3 | Escaped command sub, POSIX variable scoping |
| Other | 35 | Alias expansion, control flow, functions, builtins, parsing |

#### By Subsystem

| Subsystem | Count | Tests |
|-----------|-------|-------|
| Parsing/Expansion | 9 | Character classes, error recovery, mixed quoting, logical ops, brace expansion edge cases |
| Control Flow | 5 | Case fallthrough, heredoc in case, while-read pipes, nested structures (2) |
| Aliases | 6 | Expansion timing, special chars, subshell inheritance, array syntax, pipe, args |
| Subshells | 5 | Nested subshells, complex redirections, process sub, stderr redirect, command not found |
| Conformance | 2 | Extended globbing, advanced redirection |
| Functions | 4 | Background job, pipeline filter, pipeline chain, many commands |
| Builtins | 4 | Declare nameref, disown (2), history clear |
| Job Control | 1 | Background job redirection error |
| While Loops | 1 | Command condition with read |
| Performance | 1 | Long brace expansion |
| Pipelines | 1 | Error in middle |
| Parameters | 1 | Scoping |
| Arrays | 1 | Parameter expansion operators |

### Conformance Results (239 total)

| Category | Count | Percentage |
|----------|-------|------------|
| Identical | 222 | 92.9% |
| Documented Difference | 6 | 2.5% |
| PSH Extension | 2 | 0.8% |
| PSH Bug | 0 | 0.0% |
| Test Error | 9 | 3.8% |

#### PSH Bugs (0)

All previously reported bugs have been resolved. See "Completed Recommendations (v0.107.0, 2026-02-06)" above.

#### Test Errors (9)

1. `unset x; echo ${x:?undefined}` -- Error expansion for unset variables (POSIX)
2. `x=; echo ${x:?empty}` -- Error expansion for empty variables (POSIX)
3. `shopt -s extglob; echo ?(pattern)` -- Extended globbing (Bash)
4-6. Duplicate test-level errors for extglob, redirection
7. `exec 3> file.txt` -- Exec with numbered file descriptors (Bash)
8-9. Alias and other test-level errors

#### Documented Differences (6)

1. `VAR=value echo $VAR` -- Command-prefixed variable expansion (PSH is more POSIX-correct)
2. `A=1 B=2 echo $A$B` -- Multi-assignment prefix expansion (PSH is more POSIX-correct)
3. `popd` -- Directory stack behavior
4. `echo $$` -- Process ID differs between PSH and bash (expected)
5. `echo \$(echo test)` -- Both shells reject as syntax error; error message format differs
6. `pushd /tmp` -- Both shells correctly show two-entry stack; CWD differs due to test environment

#### PSH Extensions (2)

1. `alias greet="echo hello"; greet world` -- Alias expansion in non-interactive mode
2. `version` -- PSH-specific command

---

## What's Working Well

- Test organization (unit/integration/system/conformance) is clean and logical
- The `run_tests.py` smart runner properly handles the pytest `-s` issue for subshells and I/O tests
- xfail reasons are specific and actionable
- Conformance framework gives objective compliance metrics
- 97%+ of tests (2,671/2,712+ non-skipped) pass
- Regression tests guard against re-introduction of fixed bugs

---

## Summary: Recommended Next Steps

1. Reclassify 9 conformance test errors for more accurate metrics
2. Implement `extglob` glob expansion patterns
3. Add performance/stress tests
4. Enable interactive tests with `pexpect`
