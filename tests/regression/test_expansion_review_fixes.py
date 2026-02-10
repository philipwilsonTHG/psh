"""
Regression tests for expansion subsystem fixes from code quality reviews.

Phase 1 (v0.142.0):
  1. ${var:=default} parsed correctly via string-based expansion path
  2. ${var:?msg} parsed correctly via string-based expansion path

Phase 4 (v0.145.0):
  3. Multiple "$@" in one quoted word
  4. Quote-aware scanners for command substitution
"""

import subprocess
import sys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _psh(cmd: str) -> subprocess.CompletedProcess:
    """Run a command in psh and return the result."""
    return subprocess.run(
        [sys.executable, '-m', 'psh', '-c', cmd],
        capture_output=True, text=True, timeout=10,
    )


# ===========================================================================
# Phase 1 — ${var:=default} and ${var:?msg} in string contexts
# ===========================================================================

class TestColonOperatorParsing:
    """${var:=default} and ${var:?msg} must not be parsed as substring
    extraction (the : operator) in the string-based expansion path used
    by expand_string_variables().
    """

    def test_colon_equals_default_assignment(self):
        """${var:=default} assigns and returns default when var is unset."""
        result = _psh('unset x; echo "${x:=hello}"; echo "$x"')
        assert result.returncode == 0
        assert result.stdout == "hello\nhello\n"

    def test_colon_question_error_message(self):
        """${var:?msg} prints error and fails when var is unset."""
        result = _psh('unset x; echo "${x:?variable not set}" 2>/dev/null; echo "exit=$?"')
        # The expansion error should cause the command to fail
        assert "exit=1" in result.stdout or result.returncode != 0

    def test_colon_equals_with_existing_value(self):
        """${var:=default} returns existing value without overwriting."""
        result = _psh('x=existing; echo "${x:=default}"; echo "$x"')
        assert result.returncode == 0
        assert result.stdout == "existing\nexisting\n"

    def test_colon_question_with_existing_value(self):
        """${var:?msg} returns value when var is set."""
        result = _psh('x=hello; echo "${x:?should not fail}"')
        assert result.returncode == 0
        assert result.stdout.strip() == "hello"


# ===========================================================================
# Phase 4 — Multiple "$@" in one quoted word
# ===========================================================================

class TestMultipleAtExpansion:
    """Multiple "$@" occurrences in a single word should each splice
    positional params independently.
    """

    def test_double_at_in_quoted_word(self):
        """'a$@b$@c' with params (1 2) → a1 2b1 2c."""
        result = _psh("set -- 1 2; printf '<%s>\\n' \"a$@b$@c\"")
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert lines == ['<a1>', '<2b1>', '<2c>']

    def test_single_at_still_works(self):
        """Basic "$@" splitting with prefix/suffix still works."""
        result = _psh("set -- x y; printf '<%s>\\n' \"pre$@post\"")
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert lines == ['<prex>', '<ypost>']

    def test_at_with_no_params_produces_nothing(self):
        """Multiple "$@" with no params produces just surrounding text."""
        result = _psh("set --; printf '<%s>\\n' \"a$@b$@c\"")
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert lines == ['<abc>']

    def test_at_single_param(self):
        """Multiple "$@" with single param concatenates."""
        result = _psh("set -- X; printf '<%s>\\n' \"a$@b$@c\"")
        assert result.returncode == 0
        lines = result.stdout.strip().split('\n')
        assert lines == ['<aXbXc>']


# ===========================================================================
# Phase 4 — Quote-aware scanners
# ===========================================================================

class TestQuoteAwareScanners:
    """Parentheses and braces inside quotes should not confuse the
    expansion scanners.
    """

    def test_command_sub_with_quoted_paren(self):
        """$(...) scanner handles quoted parentheses."""
        result = _psh("echo $(echo 'hello)')")
        assert result.returncode == 0
        # The ) inside single quotes should not close the $(
        assert 'hello)' in result.stdout

    def test_braces_in_quoted_default(self):
        """${var:-default} with braces in default value."""
        result = _psh('unset x; echo "${x:-{hello}}"')
        assert result.returncode == 0
        assert result.stdout.strip() == '{hello}'
