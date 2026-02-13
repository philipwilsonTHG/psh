# Combinator Parser: Remaining Test Failures

**As of v0.170.0** (associative array fix reducing 5 → 3 failures)

This document catalogues the 3 remaining test failures when running the
full test suite with `PSH_TEST_PARSER=combinator`.

## Summary

| Category | Count | Root Cause | Difficulty |
|----------|------:|------------|------------|
| C-style for IO redirection | 3 | Need `-s` flag — not a parser bug | N/A |

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
| v0.170.0 (batch 4) | 3 | Fixed: associative array initialization (quoted keys/values, bracket tokens) |
