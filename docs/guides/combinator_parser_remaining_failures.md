# Combinator Parser: Remaining Test Failures

**As of v0.169.0** (post bug-fix batches reducing 18 → 5 failures)

This document catalogues the 5 remaining test failures when running the
full test suite with `PSH_TEST_PARSER=combinator`.

## Summary

| Category | Count | Root Cause | Difficulty |
|----------|------:|------------|------------|
| C-style for IO redirection | 3 | Need `-s` flag — not a parser bug | N/A |
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

### 2. Associative Array Initialisation with Quoted Keys (2 tests)

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
| v0.168.0 (batch 2) | 11 | Fixed: process substitution (LiteralPart), errexit in TopLevel, RBRACE in brace expansion |
| v0.169.0 (batch 3) | 5 | Fixed: lexer arithmetic operator drop, case pattern LBRACKET character classes |
