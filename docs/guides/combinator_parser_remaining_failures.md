# Combinator Parser: Remaining Test Failures

**As of v0.166.0** (post bug-fix batch reducing 39 → 18 failures)

This document catalogues the 18 remaining test failures when running the
full test suite with `PSH_TEST_PARSER=combinator`.  None are regressions
from recent changes — all are pre-existing feature gaps, test
infrastructure issues, or executor bugs unrelated to the parser.

## Summary

| Category | Count | Root Cause |
|----------|------:|------------|
| Process substitution | 4 | Feature not fully wired in combinator path |
| C-style for IO redirection | 3 | Test pollution — all 3 pass in isolation |
| Arithmetic evaluation | 4 | Pre-existing arithmetic parser/evaluator gaps |
| capsys output capture | 2 | Shell writes to real stdout; `capsys` sees nothing |
| Associative array edge cases | 2 | Quoted spaces / equals in keys not handled |
| Case statement redirection | 1 | Case body redirections produce no output file |
| `set -e` + command-not-found | 1 | Executor does not abort on missing command with `errexit` |
| Redirection with `errexit` | 1 | Process substitution + `set -e` interaction |

## Detailed Failure List

### 1. Process Substitution (4 tests)

Process substitution (`<(cmd)`, `>(cmd)`) is not fully wired through the
combinator parser's execution path.  The lexer tokenises the syntax
correctly, but the resulting AST does not integrate with the executor's
FD setup.

| Test | Error |
|------|-------|
| `conformance/bash/test_bash_compatibility.py::TestBashCommandSubstitution::test_process_substitution` | Process substitution output not captured |
| `unit/executor/test_child_policy.py::TestCommandSubstitutionSignals::test_process_sub_basic_works` | Process substitution FD not connected |
| `unit/io_redirect/test_fd_operations.py::TestProcessSubRedirect::test_process_sub_redirect_completes` | Process substitution redirect incomplete |
| `unit/io_redirect/test_fd_operations.py::TestProcessSubRedirect::test_process_sub_redirect_multiline` | Process substitution redirect incomplete |

**Fix complexity:** Medium.  Requires wiring `ProcessSubstitution` AST
nodes into the executor's FD management and child-process lifecycle.

---

### 2. C-style For Loop IO Redirection (3 tests) — Test Pollution

All three tests **pass when run in isolation** but fail in the full batch
run due to test pollution from earlier tests affecting shell state.

| Test | Error |
|------|-------|
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_output_redirection` | Output file not created (batch only) |
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_append_redirection` | Output file not created (batch only) |
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_input_redirection` | Input file read fails (batch only) |

**Verification:**
```bash
# Passes:
PSH_TEST_PARSER=combinator python -m pytest \
  tests/integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection -xvs
# Fails only in the full suite run.
```

**Fix complexity:** Low, but requires identifying which earlier test
contaminates shell state.  Not a parser bug.

---

### 3. Arithmetic Evaluation in Compound Commands (4 tests)

The combinator parser builds `ArithmeticEvaluation` nodes with slightly
different expression formatting than the recursive descent parser.  When
nested inside `if (( ... ))` conditions, the evaluator receives malformed
expressions and reports "Unexpected token after expression".

| Test | Error |
|------|-------|
| `unit/expansion/test_arithmetic_integration.py::TestArithmeticIntegration::test_arithmetic_in_if_conditions` | `unexpected error: Unexpected token after expression: 1` |
| `unit/expansion/test_arithmetic_integration_core.py::TestArithmeticIntegrationCore::test_arithmetic_in_if_conditions` | Same as above |
| `unit/expansion/test_arithmetic_integration_essential.py::TestArithmeticIntegrationEssential::test_arithmetic_in_if_conditions` | Same as above |
| `unit/expansion/test_arithmetic_integration.py::TestArithmeticIntegration::test_arithmetic_with_brace_expansion` | `Unexpected token after valid input: RBRACE '}'` |

**Example command:**
```bash
if (( $((x / y)) > 1 )); then echo "greater"; fi
```

**Root cause:** The combinator's `_build_arithmetic_command` joins tokens
with spaces and normalises whitespace, but the interaction between nested
`$((...))` inside `(( ))` produces expression strings the evaluator
cannot parse.  The brace expansion test (`echo $((1+{1..5}))`) fails
because the lexer emits `RBRACE` tokens that the combinator parser does
not expect after an expression.

**Fix complexity:** Medium.  Requires aligning the arithmetic expression
builder with the evaluator's expected input format, and possibly teaching
the parser to pass through brace tokens inside arithmetic contexts.

---

### 4. capsys Output Capture (2 tests)

These tests use pytest's `capsys` fixture to capture output, but the
combinator shell writes directly to real stdout (fd 1) rather than
through Python's `sys.stdout`.  The `capsys` fixture only intercepts
Python-level writes, so it sees empty output.

| Test | Error |
|------|-------|
| `integration/control_flow/test_case_statements.py::TestCaseStatements::test_case_with_character_classes` | `assert 'a is lowercase' in ''` (capsys empty) |
| `unit/executor/test_executor_visitor_control_flow.py::TestComplexControlFlow::test_case_in_loop` | `assert 'text: apple' in ''` (capsys empty) |

**Example command:**
```bash
for char in a 1 Z @ _; do
    case $char in
        [a-z]) echo "$char is lowercase" ;;
        [A-Z]) echo "$char is uppercase" ;;
        [0-9]) echo "$char is a digit" ;;
        *) echo "$char is special" ;;
    esac
done
```

**Fix complexity:** Low.  Switch these tests to use `captured_shell`
instead of `capsys`, or investigate why the combinator path bypasses
Python-level stdout.

---

### 5. Associative Array Edge Cases (2 tests)

The array assignment fix (synthesising `name=(item1 item2 ...)` tokens)
handles simple indexed arrays correctly, but associative arrays with
quoted spaces in keys or `=` characters in keys/values are not parsed
into the correct structure.

| Test | Error |
|------|-------|
| `integration/builtins/test_declare_comprehensive.py::TestDeclareArrays::test_declare_associative_array_init_with_quoted_spaces` | `AssociativeArray({})` — keys with spaces lost |
| `integration/builtins/test_declare_comprehensive.py::TestDeclareArrays::test_declare_associative_array_init_with_equals_in_keys_values` | `AssociativeArray({})` — keys with `=` lost |

**Example commands:**
```bash
declare -A assoc=(["first key"]="first value" ["second key"]="second value")
declare -A assoc=(["k=1"]="v=2" ["k=3"]="v=4")
```

**Root cause:** The synthetic token approach concatenates raw token values
without preserving the `[key]=value` structure that the executor's array
initialisation code expects for associative arrays.  The recursive
descent parser's `ArrayParser` handles these patterns with dedicated
bracket/quote-aware parsing.

**Fix complexity:** High.  Requires either routing to the special
command's `_build_array_initialization` parser when `declare -A` is
detected, or teaching the synthetic token builder to preserve associative
array structure including quoted keys and values with special characters.

---

### 6. Case Statement Redirection (1 test)

A `case` statement with output redirection inside the body fails to
create the expected output file.

| Test | Error |
|------|-------|
| `integration/control_flow/test_nested_structures_io_conservative.py::TestBasicNestedIO::test_append_redirection_in_case` | `FileNotFoundError: .../numbers.txt` — redirect target never created |

**Example command:**
```bash
for item in apple 123 banana; do
    case "$item" in
        [0-9]*) echo "Number: $item" >> numbers.txt ;;
        *) echo "Text: $item" >> text.txt ;;
    esac
done
```

**Root cause:** The case body's redirection (`>> numbers.txt`) is not
being applied to the echo commands within case items.  This may be
related to how the combinator parser builds case item bodies — the
redirection may be attached to the case statement rather than to the
individual commands within the items.

**Fix complexity:** Medium.  Requires investigating how case item
commands and their redirections are represented in the combinator's AST
versus the recursive descent parser's AST.

---

### 7. `set -e` with Command Not Found (1 test)

When `set -e` (errexit) is active and a command is not found, the shell
should abort with a non-zero exit code.  Instead, the combinator path
continues execution and returns 0.

| Test | Error |
|------|-------|
| `integration/command_resolution/test_command_resolution.py::TestCommandNotFound::test_command_not_found_with_errexit` | `assert 0 != 0` — shell did not abort |

**Example command:**
```bash
set -e; nonexistent_command_abc; echo "should not reach here"
```

The shell prints `psh: nonexistent_command_abc: command not found` and
`should not reach here`, then exits 0.

**Root cause:** This is an executor bug, not a parser bug.  The
`set -e` abort logic does not trigger on command-not-found errors in the
combinator execution path.

**Fix complexity:** Low, but in the executor, not the parser.

---

### 8. Redirection with `errexit` in Process Substitution Context (1 test)

| Test | Error |
|------|-------|
| `integration/redirection/test_advanced_redirection.py::TestProcessSubstitution::test_redirection_with_errexit` | Process substitution + `set -e` interaction failure |

**Root cause:** Overlaps with the process substitution gap (section 1)
and the `set -e` executor bug (section 7).  The test exercises process
substitution under `errexit` mode — both features have independent
issues in the combinator path.

**Fix complexity:** Depends on fixes for sections 1 and 7.

---

## How to Run

```bash
# Full combinator test suite (excluding known-excluded directories)
PSH_TEST_PARSER=combinator python -m pytest tests/ \
  --ignore=tests/integration/subshells/ \
  --ignore=tests/integration/functions/test_function_advanced.py \
  --ignore=tests/integration/variables/test_variable_assignment.py \
  -q --tb=line

# Run a specific failing test with verbose output
PSH_TEST_PARSER=combinator python -m pytest <test_path> -xvs
```

## History

| Date | Failures | Notes |
|------|----------|-------|
| v0.166.0 (pre-fix) | 39 | Baseline before bug-fix batch |
| v0.166.0 (post-fix) | 18 | Fixed: pipeline routing, for-loop expansions, stderr redirects, array assignments, C-style for `do` |
