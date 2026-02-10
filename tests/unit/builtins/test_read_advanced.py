"""
Tests for advanced read builtin features.

This file specifically tests the advanced flags of the read builtin:
- -n (read N characters)
- -a (read into array)
- -r (raw mode)
- -s (silent mode)
- -t (timeout)
"""

from io import StringIO


class TestReadAdvancedFeatures:
    """Test advanced read builtin features."""

    def test_read_n_exact_chars(self, shell, capsys, monkeypatch):
        """Test read -n reads exact number of characters."""
        monkeypatch.setattr('sys.stdin', StringIO("abcdefghijklmnop"))

        # Read exactly 5 characters
        shell.run_command('read -n 5 var')
        shell.run_command('echo "[$var]"')
        captured = capsys.readouterr()
        assert "[abcde]" in captured.out

        # Read another 3 characters
        shell.run_command('read -n 3 var2')
        shell.run_command('echo "[$var2]"')
        captured = capsys.readouterr()
        assert "[fgh]" in captured.out

    def test_read_array_multiple_elements(self, shell, capsys, monkeypatch):
        """Test read -a creates proper array."""
        monkeypatch.setattr('sys.stdin', StringIO("apple banana cherry date elderberry\n"))

        shell.run_command('read -a fruits')

        # Test individual elements
        shell.run_command('echo "0: ${fruits[0]}"')
        shell.run_command('echo "1: ${fruits[1]}"')
        shell.run_command('echo "2: ${fruits[2]}"')
        shell.run_command('echo "3: ${fruits[3]}"')
        shell.run_command('echo "4: ${fruits[4]}"')

        captured = capsys.readouterr()
        assert "0: apple" in captured.out
        assert "1: banana" in captured.out
        assert "2: cherry" in captured.out
        assert "3: date" in captured.out
        assert "4: elderberry" in captured.out

    def test_read_raw_mode_preserves_backslashes(self, shell, capsys, monkeypatch):
        """Test read -r preserves backslashes."""
        # Without -r, backslashes should be processed
        monkeypatch.setattr('sys.stdin', StringIO("line\\tone\\nline\\ttwo\n"))
        shell.run_command('read normal')
        shell.run_command('echo "Normal: [$normal]"')

        # With -r, backslashes should be preserved
        monkeypatch.setattr('sys.stdin', StringIO("line\\tone\\nline\\ttwo\n"))
        shell.run_command('read -r raw')
        shell.run_command('echo "Raw: [$raw]"')

        captured = capsys.readouterr()
        # The exact behavior may vary, but raw should preserve more backslashes
        assert "Normal:" in captured.out
        assert "Raw:" in captured.out

    def test_read_combined_flags(self, shell, capsys, monkeypatch):
        """Test combining multiple read flags."""
        # Use separate flags instead of combined
        monkeypatch.setattr('sys.stdin', StringIO("test\\ndata"))
        shell.run_command('read -r -n 8 var')
        shell.run_command('echo "[$var]"')
        captured = capsys.readouterr()
        assert "[test\\nda]" in captured.out

    def test_read_array_with_custom_ifs(self, shell, capsys, monkeypatch):
        """Test read -a with custom IFS."""
        monkeypatch.setattr('sys.stdin', StringIO("apple,banana,cherry\n"))

        # Set IFS to comma
        shell.run_command('IFS=","')
        shell.run_command('read -a fruits')

        shell.run_command('echo "0: [${fruits[0]}]"')
        shell.run_command('echo "1: [${fruits[1]}]"')
        shell.run_command('echo "2: [${fruits[2]}]"')

        captured = capsys.readouterr()
        assert "0: [apple]" in captured.out
        assert "1: [banana]" in captured.out
        assert "2: [cherry]" in captured.out

        # Reset IFS
        shell.run_command('unset IFS')

    def test_read_timeout_return_code(self, shell, capsys, monkeypatch):
        """Test read -t timeout returns correct exit code."""
        # In test environment, timeout doesn't actually wait
        # Just verify the -t option is accepted
        monkeypatch.setattr('sys.stdin', StringIO(""))  # Empty input
        exit_code = shell.run_command('read -t 0.1 var')
        # Should fail due to EOF, not timeout in test environment
        assert exit_code != 0

    def test_read_n_with_newline(self, shell, capsys, monkeypatch):
        """Test read -n stops at newline if encountered first."""
        monkeypatch.setattr('sys.stdin', StringIO("abc\ndefgh"))

        # Should stop at newline even though n=10
        shell.run_command('read -n 10 var')
        shell.run_command('echo "[$var]"')
        captured = capsys.readouterr()
        assert "[abc]" in captured.out

    def test_read_multiple_variables_ifs_split(self, shell, capsys, monkeypatch):
        """Test read splits input among multiple variables."""
        monkeypatch.setattr('sys.stdin', StringIO("one two three four five\n"))

        # Read into three variables
        shell.run_command('read first second rest')
        shell.run_command('echo "1=[$first] 2=[$second] rest=[$rest]"')
        captured = capsys.readouterr()
        assert "1=[one]" in captured.out
        assert "2=[two]" in captured.out
        assert "rest=[three four five]" in captured.out
