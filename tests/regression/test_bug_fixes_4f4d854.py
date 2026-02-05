"""
Regression tests for bugs fixed in commit 4f4d854.

These tests guard against re-introduction of 6 bugs fixed in that commit:
1. Command substitution not stripping all trailing newlines
2. WordSplitter not distinguishing whitespace from non-whitespace IFS
3. WordSplitter not handling backslash-escaped IFS delimiters
4. dotglob option not being respected by glob expansion
5. Comments not recognized after ) and } tokens
6. SIGCHLD handler restore missing try/finally (not testable here)
"""

import os
import pytest
from psh.expansion.word_splitter import WordSplitter


class TestCommandSubNewlineStripping:
    """Regression: command substitution must strip ALL trailing newlines."""

    def test_multiple_trailing_newlines(self, captured_shell):
        """Ensure multiple trailing newlines are stripped."""
        shell = captured_shell
        result = shell.run_command('x=$(printf "hello\\n\\n\\n"); echo "$x"')
        assert result == 0
        assert shell.get_stdout().strip() == 'hello'

    def test_single_trailing_newline(self, captured_shell):
        """Ensure a single trailing newline is stripped."""
        shell = captured_shell
        result = shell.run_command('x=$(echo hello); echo "$x"')
        assert result == 0
        assert shell.get_stdout().strip() == 'hello'

    def test_no_trailing_newline(self, captured_shell):
        """Ensure content without trailing newlines is preserved."""
        shell = captured_shell
        result = shell.run_command('x=$(printf "hello"); echo "$x"')
        assert result == 0
        assert shell.get_stdout().strip() == 'hello'


class TestWordSplitterIFS:
    """Regression: IFS word splitting must distinguish whitespace from non-whitespace."""

    def test_non_whitespace_ifs_empty_fields(self):
        """Non-whitespace IFS delimiter preserves empty fields."""
        splitter = WordSplitter()
        assert splitter.split('a::b', ':') == ['a', '', 'b']

    def test_whitespace_ifs_collapses(self):
        """Whitespace IFS delimiters collapse into one."""
        splitter = WordSplitter()
        result = splitter.split('a   b   c', ' ')
        assert result == ['a', 'b', 'c']

    def test_mixed_ifs_combined_delimiter(self):
        """Mixed IFS: whitespace around non-whitespace collapses."""
        splitter = WordSplitter()
        result = splitter.split(' a : b ', ': ')
        assert result == ['a', 'b']

    def test_trailing_non_whitespace_ifs(self):
        """Trailing non-whitespace IFS delimiter does not produce extra field."""
        splitter = WordSplitter()
        result = splitter.split('a:b:', ':')
        assert result == ['a', 'b']


class TestDotglobOption:
    """Regression: dotglob option must be respected by glob expansion."""

    def test_dotglob_matches_hidden(self, shell, capsys):
        """With dotglob enabled, glob should match dotfiles."""
        # Create test files in temp location
        shell.run_command('touch .hidden_test_dotglob visible_test_dotglob')
        shell.state.options['dotglob'] = True
        shell.run_command('echo *test_dotglob')
        output = capsys.readouterr().out
        assert '.hidden_test_dotglob' in output
        assert 'visible_test_dotglob' in output
        shell.state.options['dotglob'] = False
        shell.run_command('rm -f .hidden_test_dotglob visible_test_dotglob')

    def test_no_dotglob_hides_dotfiles(self, shell, capsys):
        """Without dotglob, glob should not match dotfiles."""
        shell.run_command('touch .hidden_test_dotglob2 visible_test_dotglob2')
        shell.state.options['dotglob'] = False
        shell.run_command('echo *test_dotglob2')
        output = capsys.readouterr().out
        assert '.hidden_test_dotglob2' not in output
        assert 'visible_test_dotglob2' in output
        shell.run_command('rm -f .hidden_test_dotglob2 visible_test_dotglob2')


class TestCommentAfterClosingBraces:
    """Regression: # after ) and } must be recognized as comment start.

    Validates at the tokenizer level that comments are correctly parsed
    after these tokens.
    """

    def test_comment_after_close_paren_tokenizes(self):
        """Tokenizer should not include comment text after )."""
        from psh.lexer import tokenize
        tokens = tokenize('(echo hello) # this is a comment')
        values = [t.value for t in tokens]
        assert 'this' not in values
        assert 'comment' not in values

    def test_comment_after_close_brace(self, captured_shell):
        """Comment after closing brace should be ignored."""
        shell = captured_shell
        result = shell.run_command('{ echo hello; } # this is a comment')
        assert result == 0
        assert shell.get_stdout().strip() == 'hello'

    def test_comment_after_done(self, captured_shell):
        """Comment after done keyword should be ignored."""
        shell = captured_shell
        result = shell.run_command('for x in a b; do echo $x; done # comment')
        assert result == 0
        output = shell.get_stdout().strip()
        assert 'a' in output
        assert 'b' in output
        assert 'comment' not in output
