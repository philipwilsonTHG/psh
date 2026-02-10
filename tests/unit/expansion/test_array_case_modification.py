"""Test array case modification parameter expansion."""



class TestArrayCaseModification:
    """Test case modification on arrays."""

    def test_array_uppercase_all(self, shell):
        """Test ${arr[@]^^} - uppercase all elements."""
        shell.run_command('arr=("hello" "WORLD" "Test")')
        shell.run_command('result="${arr[@]^^}"')
        output = shell.state.get_variable('result')
        assert output == "HELLO WORLD TEST"

    def test_array_lowercase_all(self, shell):
        """Test ${arr[@],,} - lowercase all elements."""
        shell.run_command('arr=("hello" "WORLD" "Test")')
        shell.run_command('result="${arr[@],,}"')
        output = shell.state.get_variable('result')
        assert output == "hello world test"

    def test_array_uppercase_first(self, shell):
        """Test ${arr[@]^} - uppercase first char of each element."""
        shell.run_command('arr=("hello" "world" "test")')
        shell.run_command('result="${arr[@]^}"')
        output = shell.state.get_variable('result')
        assert output == "Hello World Test"

    def test_array_lowercase_first(self, shell):
        """Test ${arr[@],} - lowercase first char of each element."""
        shell.run_command('arr=("HELLO" "WORLD" "TEST")')
        shell.run_command('result="${arr[@],}"')
        output = shell.state.get_variable('result')
        assert output == "hELLO wORLD tEST"

    def test_array_pattern_uppercase(self, shell):
        """Test ${arr[@]^^[pattern]} - pattern-based uppercase."""
        shell.run_command('arr=("hello" "world" "test")')
        shell.run_command('result="${arr[@]^^[aeiou]}"')
        output = shell.state.get_variable('result')
        assert output == "hEllO wOrld tEst"

    def test_array_pattern_lowercase(self, shell):
        """Test ${arr[@],,[pattern]} - pattern-based lowercase."""
        shell.run_command('arr=("HELLO" "WORLD" "TEST")')
        shell.run_command('result="${arr[@],,[AEIOU]}"')
        output = shell.state.get_variable('result')
        assert output == "HeLLo WoRLD TeST"

    def test_array_star_index(self, shell):
        """Test case modification with * index."""
        shell.run_command('arr=("one" "two" "three")')
        shell.run_command('IFS="-"')
        shell.run_command('result="${arr[*]^^}"')
        output = shell.state.get_variable('result')
        assert output == "ONE-TWO-THREE"

    def test_empty_array(self, shell):
        """Test case modification on empty array."""
        shell.run_command('arr=()')
        shell.run_command('result="${arr[@]^^}"')
        output = shell.state.get_variable('result')
        assert output == ""

    def test_mixed_case_elements(self, shell):
        """Test with mixed case elements."""
        shell.run_command('arr=("hElLo" "WoRlD" "TeSt123")')
        shell.run_command('upper="${arr[@]^^}"')
        shell.run_command('lower="${arr[@],,}"')
        assert shell.state.get_variable('upper') == "HELLO WORLD TEST123"
        assert shell.state.get_variable('lower') == "hello world test123"

    def test_array_pattern_complex(self, shell):
        """Test complex pattern-based case modification."""
        shell.run_command('arr=("hello123" "WORLD456" "Test789")')
        # Uppercase only letters a-m
        shell.run_command('result="${arr[@]^^[a-m]}"')
        output = shell.state.get_variable('result')
        assert output == "HELLo123 WORLD456 TEst789"

    def test_array_in_command_substitution(self, shell):
        """Test array case modification in command substitution."""
        shell.run_command('arr=("one" "two" "three")')
        shell.run_command('result=$(echo "${arr[@]^^}")')
        output = shell.state.get_variable('result')
        assert output == "ONE TWO THREE"

    def test_array_case_with_assignment(self, shell, capsys):
        """Test creating new array from case-modified array."""
        shell.run_command('arr=("hello" "world")')
        shell.run_command('new_arr=(${arr[@]^^})')
        # Verify array was created correctly by checking output
        shell.run_command('echo "${new_arr[0]}"')
        shell.run_command('echo "${new_arr[1]}"')
        shell.run_command('echo "${#new_arr[@]}"')  # Number of elements
        captured = capsys.readouterr()
        lines = captured.out.strip().split('\n')
        assert lines[0] == "HELLO"
        assert lines[1] == "WORLD"
        assert lines[2] == "2"  # Should have 2 elements

    def test_array_single_element(self, shell):
        """Test case modification on single-element array."""
        shell.run_command('arr=("hello")')
        shell.run_command('result="${arr[@]^^}"')
        output = shell.state.get_variable('result')
        assert output == "HELLO"

    def test_unicode_case_modification(self, shell):
        """Test case modification with unicode characters."""
        shell.run_command('arr=("café" "naïve")')
        shell.run_command('upper="${arr[@]^^}"')
        shell.run_command('lower="${arr[@],,}"')
        # Basic ASCII case modification should work
        assert "CAF" in shell.state.get_variable('upper')
        assert "caf" in shell.state.get_variable('lower')

    def test_array_case_with_spaces(self, shell):
        """Test case modification with elements containing spaces."""
        shell.run_command('arr=("hello world" "TEST CASE")')
        shell.run_command('result="${arr[@]^^}"')
        output = shell.state.get_variable('result')
        assert output == "HELLO WORLD TEST CASE"

    def test_associative_array_case(self, shell):
        """Test case modification on associative arrays."""
        shell.run_command('declare -A assoc')
        shell.run_command('assoc[one]="hello"')
        shell.run_command('assoc[two]="WORLD"')
        # Associative arrays should also support case modification
        shell.run_command('result="${assoc[@]^^}"')
        output = shell.state.get_variable('result')
        # Order may vary, but both should be uppercase
        assert "HELLO" in output
        assert "WORLD" in output

    def test_nested_expansion_with_case(self, shell):
        """Test nested parameter expansion with case modification."""
        shell.run_command('prefix="pre"')
        shell.run_command('arr=("${prefix}_one" "${prefix}_two")')
        shell.run_command('result="${arr[@]^^}"')
        output = shell.state.get_variable('result')
        assert output == "PRE_ONE PRE_TWO"
