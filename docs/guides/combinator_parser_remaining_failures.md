# Combinator Parser: Remaining Test Failures

**As of v0.171.0** — 0 remaining failures

The combinator parser now passes all tests in the main test suite
(excluding the directories that are structurally excluded due to subshell
FD inheritance, advanced function scoping, and complex variable assignment).

## Summary

No remaining failures.  The last 3 "failures" were test infrastructure
issues (pytest capture interference with forked child FDs), not parser
bugs.  They were resolved by rewriting the tests to use `subprocess.run()`.

## How to Run

```bash
# Full combinator test suite (excluding known-excluded directories)
PSH_TEST_PARSER=combinator python -m pytest tests/ \
  --ignore=tests/integration/subshells/ \
  --ignore=tests/integration/functions/test_function_advanced.py \
  --ignore=tests/integration/variables/test_variable_assignment.py \
  -q --tb=line

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
| v0.171.0 (batch 5) | 0 | Rewrote C-style for I/O redirection tests to use subprocess (test infra fix, not parser bug) |
