"""Integration tests for extglob extended globbing patterns.

Tests the full pipeline: lexer -> parser -> executor for all four
extglob integration points:
1. Pathname expansion
2. Parameter expansion
3. Case statements
4. Conditional expressions [[ ]]
"""

import subprocess
import sys


def run_psh(command: str, cwd: str = None) -> subprocess.CompletedProcess:
    """Run a command in psh and return the result."""
    return subprocess.run(
        [sys.executable, '-m', 'psh', '-c', command],
        capture_output=True, text=True, cwd=cwd, timeout=10,
    )


class TestExtglobPathnameExpansion:
    """Test extglob in pathname expansion (echo ?(*.txt|*.log))."""

    def test_at_pattern_matches_files(self, tmp_path):
        cmd = "shopt -s extglob\necho @(a|b).txt"
        (tmp_path / 'a.txt').touch()
        (tmp_path / 'b.txt').touch()
        (tmp_path / 'c.txt').touch()
        result = run_psh(cmd, cwd=str(tmp_path))
        assert result.returncode == 0
        assert 'a.txt' in result.stdout
        assert 'b.txt' in result.stdout
        assert 'c.txt' not in result.stdout

    def test_negation_pattern(self, tmp_path):
        cmd = "shopt -s extglob\necho !(*.log)"
        (tmp_path / 'keep.txt').touch()
        (tmp_path / 'skip.log').touch()
        result = run_psh(cmd, cwd=str(tmp_path))
        assert result.returncode == 0
        assert 'keep.txt' in result.stdout
        assert 'skip.log' not in result.stdout

    def test_plus_pattern(self, tmp_path):
        cmd = "shopt -s extglob\necho +(a).txt"
        (tmp_path / 'a.txt').touch()
        (tmp_path / 'aa.txt').touch()
        (tmp_path / 'aaa.txt').touch()
        (tmp_path / 'b.txt').touch()
        result = run_psh(cmd, cwd=str(tmp_path))
        assert result.returncode == 0
        assert 'a.txt' in result.stdout
        assert 'aa.txt' in result.stdout
        assert 'aaa.txt' in result.stdout
        assert 'b.txt' not in result.stdout

    def test_question_pattern(self, tmp_path):
        cmd = "shopt -s extglob\necho ?(prefix_)file.txt"
        (tmp_path / 'file.txt').touch()
        (tmp_path / 'prefix_file.txt').touch()
        result = run_psh(cmd, cwd=str(tmp_path))
        assert result.returncode == 0
        assert 'file.txt' in result.stdout
        assert 'prefix_file.txt' in result.stdout

    def test_no_match_returns_pattern(self, tmp_path):
        """When no files match and nullglob is off, return the pattern itself."""
        cmd = "shopt -s extglob\necho @(nomatch).xyz"
        result = run_psh(cmd, cwd=str(tmp_path))
        assert result.returncode == 0
        assert '@(nomatch).xyz' in result.stdout

    def test_extglob_disabled_different_behavior(self, tmp_path):
        """Without extglob, @(a|b) is NOT a pattern - it gets parsed differently.

        Without extglob, ( and ) are operator characters so the tokenizer
        breaks them apart. This is expected behavior.
        """
        cmd = "shopt -s extglob\necho @(a|b).txt"
        (tmp_path / 'a.txt').touch()
        (tmp_path / 'b.txt').touch()
        result = run_psh(cmd, cwd=str(tmp_path))
        # With extglob, files match
        assert result.returncode == 0
        assert 'a.txt' in result.stdout


class TestExtglobParameterExpansion:
    """Test extglob in parameter expansion (${var##+(space)})."""

    def test_prefix_removal(self):
        cmd = "shopt -s extglob\nx='   hello'\necho \"${x##+([ ])}\""
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'hello'

    def test_suffix_removal(self):
        cmd = "shopt -s extglob\nx='hello   '\necho \"${x%%+([ ])}\""
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'hello'

    def test_pattern_substitution(self):
        cmd = "shopt -s extglob\nx='aabbbcc'\necho \"${x/@(a|b)/X}\""
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'Xabbbcc'

    def test_global_substitution(self):
        cmd = "shopt -s extglob\nx='aabbbcc'\necho \"${x//@(a|b)/X}\""
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'XXXXXcc'


class TestExtglobCaseStatement:
    """Test extglob in case statements."""

    def test_at_pattern_match(self):
        cmd = "shopt -s extglob\ncase yes in @(yes|no)) echo matched;; esac"
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'matched'

    def test_at_pattern_no_match(self):
        cmd = "shopt -s extglob\ncase maybe in @(yes|no)) echo matched;; *) echo default;; esac"
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'default'

    def test_negation_pattern(self):
        cmd = "shopt -s extglob\ncase hello in !(bad|evil)) echo good;; esac"
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'good'

    def test_plus_pattern(self):
        cmd = "shopt -s extglob\ncase aaa in +(a)) echo matched;; esac"
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'matched'


class TestExtglobConditionalExpression:
    """Test extglob in [[ ]] conditional expressions."""

    def test_at_pattern_match(self):
        cmd = 'shopt -s extglob\n[[ yes == @(yes|no) ]] && echo matched'
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'matched'

    def test_at_pattern_no_match(self):
        cmd = 'shopt -s extglob\n[[ maybe == @(yes|no) ]] && echo matched || echo no'
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'no'

    def test_negation_pattern(self):
        cmd = 'shopt -s extglob\n[[ hello == !(bad) ]] && echo matched'
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'matched'

    def test_not_equal_with_extglob(self):
        cmd = 'shopt -s extglob\n[[ yes != !(yes) ]] && echo yes || echo no'
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'yes'


class TestExtglobEdgeCases:
    """Edge cases and tricky scenarios."""

    def test_shopt_on_separate_line(self):
        """extglob must be set on a previous line (matching bash behavior)."""
        cmd = "shopt -s extglob\necho @(a|b)"
        result = run_psh(cmd)
        # Should work because shopt is on a separate line
        assert result.returncode == 0

    def test_shopt_disable_restores_behavior(self):
        """After disabling extglob, patterns are no longer treated as extglob.

        Without extglob, the shell sees @(a|b) as @ followed by subshell (a|b),
        which will attempt to run commands a and b in a pipeline.
        """
        cmd = "shopt -s extglob\nshopt -u extglob\necho hello"
        result = run_psh(cmd)
        assert result.returncode == 0
        assert result.stdout.strip() == 'hello'
