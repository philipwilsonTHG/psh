"""
Integration tests for case statements.

Tests cover:
- Basic case statements
- Multiple patterns
- Wildcards and glob patterns
- Fall-through behavior
- Complex patterns
"""



class TestCaseStatements:
    """Test case statement functionality."""

    def test_basic_case(self, shell, capsys):
        """Test basic case statement."""
        cmd = '''
        VAR="apple"
        case $VAR in
            apple)
                echo "It's an apple"
                ;;
            banana)
                echo "It's a banana"
                ;;
            *)
                echo "Unknown fruit"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert captured.out.strip() == "It's an apple"

    def test_case_with_multiple_patterns(self, shell, capsys):
        """Test case with multiple patterns per branch."""
        cmd = '''
        for fruit in apple orange banana grape; do
            case $fruit in
                apple|orange)
                    echo "$fruit is citrus or pomaceous"
                    ;;
                banana|grape)
                    echo "$fruit is tropical or vine"
                    ;;
            esac
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "apple is citrus or pomaceous" in captured.out
        assert "orange is citrus or pomaceous" in captured.out
        assert "banana is tropical or vine" in captured.out
        assert "grape is tropical or vine" in captured.out

    def test_case_with_wildcards(self, shell, capsys):
        """Test case with wildcard patterns."""
        cmd = '''
        for file in test.txt image.jpg script.sh data.csv; do
            case $file in
                *.txt)
                    echo "$file is a text file"
                    ;;
                *.jpg|*.png)
                    echo "$file is an image"
                    ;;
                *.sh)
                    echo "$file is a shell script"
                    ;;
                *)
                    echo "$file is something else"
                    ;;
            esac
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "test.txt is a text file" in captured.out
        assert "image.jpg is an image" in captured.out
        assert "script.sh is a shell script" in captured.out
        assert "data.csv is something else" in captured.out

    def test_case_with_character_classes(self, shell, capsys):
        """Test case with character class patterns."""
        cmd = '''
        for char in a 1 Z @ _; do
            case $char in
                [a-z])
                    echo "$char is lowercase"
                    ;;
                [A-Z])
                    echo "$char is uppercase"
                    ;;
                [0-9])
                    echo "$char is a digit"
                    ;;
                *)
                    echo "$char is special"
                    ;;
            esac
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "a is lowercase" in captured.out
        assert "1 is a digit" in captured.out
        assert "Z is uppercase" in captured.out
        assert "@ is special" in captured.out
        assert "_ is special" in captured.out

    def test_case_no_match(self, shell, capsys):
        """Test case with no matching pattern."""
        cmd = '''
        VAR="unknown"
        case $VAR in
            yes)
                echo "affirmative"
                ;;
            no)
                echo "negative"
                ;;
        esac
        echo "done"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "affirmative" not in captured.out
        assert "negative" not in captured.out
        assert "done" in captured.out

    def test_case_empty_variable(self, shell, capsys):
        """Test case with empty variable."""
        cmd = '''
        VAR=""
        case $VAR in
            "")
                echo "empty"
                ;;
            *)
                echo "not empty"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert captured.out.strip() == "empty"

    def test_case_with_quotes(self, shell, capsys):
        """Test case with quoted patterns."""
        cmd = '''
        VAR="hello world"
        case "$VAR" in
            "hello world")
                echo "matched with spaces"
                ;;
            hello*)
                echo "matched prefix"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert captured.out.strip() == "matched with spaces"

    def test_case_with_command_substitution(self, shell, capsys):
        """Test case with command substitution."""
        cmd = '''
        case $(echo "test") in
            test)
                echo "command substitution works"
                ;;
            *)
                echo "failed"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert captured.out.strip() == "command substitution works"

    def test_case_fallthrough(self, shell, capsys):
        """Test case with fall-through behavior."""
        cmd = '''
        VAR="test"
        case $VAR in
            test)
                echo "matched test"
                ;&  # Fall through
            *)
                echo "also in default"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "matched test" in captured.out
        assert "also in default" in captured.out

    def test_nested_case(self, shell, capsys):
        """Test nested case statements."""
        cmd = '''
        TYPE="file"
        EXT="txt"

        case $TYPE in
            file)
                case $EXT in
                    txt)
                        echo "text file"
                        ;;
                    jpg)
                        echo "image file"
                        ;;
                esac
                ;;
            dir)
                echo "directory"
                ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert captured.out.strip() == "text file"

    def test_case_with_glob_patterns(self, shell, capsys):
        """Test case with various glob patterns."""
        cmd = '''
        for pattern in abc a1c aXc a12c; do
            case $pattern in
                a?c)
                    echo "$pattern matches a?c"
                    ;;
                a*c)
                    echo "$pattern matches a*c"
                    ;;
                *)
                    echo "$pattern no match"
                    ;;
            esac
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "abc matches a?c" in captured.out
        assert "a1c matches a?c" in captured.out
        assert "aXc matches a?c" in captured.out
        assert "a12c matches a*c" in captured.out

    def test_case_with_function(self, shell, capsys):
        """Test case calling functions."""
        cmd = '''
        handle_text() { echo "Processing text file: $1"; }
        handle_image() { echo "Processing image file: $1"; }
        handle_other() { echo "Processing other file: $1"; }

        for file in doc.txt pic.jpg data.bin; do
            case $file in
                *.txt)
                    handle_text "$file"
                    ;;
                *.jpg|*.png)
                    handle_image "$file"
                    ;;
                *)
                    handle_other "$file"
                    ;;
            esac
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "Processing text file: doc.txt" in captured.out
        assert "Processing image file: pic.jpg" in captured.out
        assert "Processing other file: data.bin" in captured.out

    def test_case_oneline(self, shell, capsys):
        """Test case on single line (semicolon separated)."""
        shell.run_command('X=yes; case $X in yes) echo "YES";; no) echo "NO";; esac')
        captured = capsys.readouterr()
        assert captured.out.strip() == "YES"
