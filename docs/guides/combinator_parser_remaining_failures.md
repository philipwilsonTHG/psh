# Combinator Parser: Remaining Test Failures

**As of v0.167.0** (post bug-fix batch reducing 18 → 11 failures)

This document catalogues the 11 remaining test failures when running the
full test suite with `PSH_TEST_PARSER=combinator`.  None are regressions
from recent changes — all are pre-existing feature gaps or test
infrastructure issues.

## Summary

| Category | Count | Root Cause | Difficulty |
|----------|------:|------------|------------|
| C-style for IO redirection | 3 | Need `-s` flag — not a parser bug | N/A |
| Nested arithmetic operators | 3 | `>` consumed as redirect inside `(( ))` | Hard |
| Case character class (multi-line) | 3 | Lexer LBRACKET tokenization at line start | Medium |
| Associative array edge cases | 2 | Quoted keys/values not preserved | Medium |

## Detailed Failure List

### 1. C-style For Loop IO Redirection (3 tests) — Need `-s` Flag

These tests use `isolated_shell_with_temp_dir` and test I/O redirection
with C-style for loops.  They **pass with the `-s` flag** (and pass under
the recursive descent parser for the same reason).  `run_tests.py` already
handles this by deselecting them from Phase 1 and running them with `-s`
in Phase 3.

| Test | Error |
|------|-------|
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_output_redirection` | Output file not created (capture interference) |
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_append_redirection` | Output file not created (capture interference) |
| `integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection::test_c_style_with_input_redirection` | Input file read fails (capture interference) |

**Verification:**
```bash
# Passes with -s:
PSH_TEST_PARSER=combinator python -m pytest \
  tests/integration/control_flow/test_c_style_for_loops.py::TestCStyleForIORedirection -xvs
```

**Fix complexity:** N/A.  Not a parser bug.  Already handled by the test
runner.

---

### 2. Nested Arithmetic `(( $((expr)) > n ))` (3 tests)

The `>` operator inside `(( ))` is consumed as a redirect operator instead
of an arithmetic comparison when preceded by a `$((expr))` expansion.

| Test | Error |
|------|-------|
| `unit/expansion/test_arithmetic_integration.py::TestArithmeticIntegration::test_arithmetic_in_if_conditions` | `unexpected error: Unexpected token after expression: 1` |
| `unit/expansion/test_arithmetic_integration_core.py::TestArithmeticIntegrationCore::test_arithmetic_in_if_conditions` | Same |
| `unit/expansion/test_arithmetic_integration_essential.py::TestArithmeticIntegrationEssential::test_arithmetic_in_if_conditions` | Same |

**Example command:**
```bash
if (( $((x / y)) > 1 )); then echo "greater"; fi
```

**Root cause:** The combinator's `_build_arithmetic_command` in
`special_commands.py` collects tokens between `((` and `))`.  When
`$((5 / 2))` appears inside `(( ))`, the inner `))` is ambiguous —
it could close the nested `$((` or the outer `((`.  The parser
resolves this incorrectly, producing `expression: "$((5 / 2)) 1"`
(the `>` is missing, consumed as a redirect by the command layer).

Simple arithmetic like `(( 5 > 3 ))` works correctly — the bug only
manifests when `$((expr))` precedes `>` inside `(( ))`.

**Fix complexity:** Hard.  Requires context-aware operator handling to
prevent `>`, `<`, `>=`, `<=` from being interpreted as redirects when
inside an arithmetic evaluation context.  The recursive descent parser
handles this via an `in_arithmetic` context flag that suppresses
redirect interpretation.

---

### 3. Case Statement Character Class Patterns — Multi-line (3 tests)

Case patterns containing character classes (`[a-z]`, `[0-9]*`) fail
when the case statement spans multiple lines.  Single-line equivalents
work correctly.

| Test | Error |
|------|-------|
| `integration/control_flow/test_case_statements.py::TestCaseStatements::test_case_with_character_classes` | `assert 'a is lowercase' in ''` |
| `integration/control_flow/test_nested_structures_io_conservative.py::TestBasicNestedIO::test_append_redirection_in_case` | `FileNotFoundError: .../numbers.txt` |
| `unit/executor/test_executor_visitor_control_flow.py::TestComplexControlFlow::test_case_in_loop` | `assert 'text: apple' in ''` |

**Example command:**
```bash
# Works (single line):
case 123 in [0-9]*) echo number;; esac

# Fails (multi-line):
case 123 in
    [0-9]*) echo number ;;
esac
```

**Root cause:** The lexer produces different tokens depending on position:

| Context | Tokens |
|---------|--------|
| Mid-line | `WORD '[0-9]*'` `RPAREN ')'` |
| Line start | `LBRACKET '['` `WORD '0-9'` `WORD ']*'` `RPAREN ')'` |

When `[` appears at the start of a line (after a newline), the lexer
emits `LBRACKET` instead of treating it as part of a `WORD`.  The case
pattern parser expects a single word token for the pattern and cannot
reconstruct the glob from the split tokens.

**Fix complexity:** Medium.  The case pattern parser in
`control_structures/conditionals.py` needs to handle `LBRACKET` as the
start of a character class pattern, collecting tokens through `]` and
any trailing glob characters to reconstruct the full pattern string.

---

### 4. Associative Array Initialisation with Quoted Keys (2 tests)

The array assignment handler produces incorrect synthetic tokens for
associative arrays with quoted keys containing spaces or `=` characters.

| Test | Error |
|------|-------|
| `integration/builtins/test_declare_comprehensive.py::TestDeclareArrays::test_declare_associative_array_init_with_quoted_spaces` | `AssociativeArray({})` — keys with spaces lost |
| `integration/builtins/test_declare_comprehensive.py::TestDeclareArrays::test_declare_associative_array_init_with_equals_in_keys_values` | `AssociativeArray({})` — keys with `=` lost |

**Example commands:**
```bash
declare -A assoc=(["first key"]="first value" ["second key"]="second value")
declare -A assoc=(["k=1"]="v=2" ["k=3"]="v=4")
```

**Root cause:** The combinator's array assignment code in `commands.py`
synthesises a single token by joining raw token values:
`assoc=(first key ]= first value)` instead of the correct
`assoc=(["first key"]="first value")`.  The `LBRACKET` token is consumed
separately, quotes are stripped, and the `[key]=value` structure is lost.

The recursive descent parser's `ArrayParser` has dedicated
bracket/quote-aware parsing that preserves the full `["key"]="value"`
syntax.

**Fix complexity:** Medium.  The synthetic token builder needs to
preserve quotes and bracket syntax for `[key]=value` entries, or the
combinator should route `declare -A` commands through the existing
array initialisation parser.

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

# Via the smart test runner (handles -s flag tests automatically)
python run_tests.py --combinator > tmp/combinator-results.txt 2>&1
tail -15 tmp/combinator-results.txt
```

## History

| Date | Failures | Notes |
|------|----------|-------|
| v0.166.0 (pre-fix) | 39 | Baseline before bug-fix batch |
| v0.167.0 (batch 1) | 18 | Fixed: pipeline routing, for-loop expansions, stderr redirects, array assignments, C-style for `do` |
| v0.167.0 (batch 2) | 11 | Fixed: process substitution (LiteralPart), errexit in TopLevel, RBRACE in brace expansion |
