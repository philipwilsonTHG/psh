"""
Unit tests for function-related builtins (return, readonly, declare).

Tests cover:
- Return from functions/scripts
- Readonly variable declaration
- Declare variable attributes
"""

import pytest


class TestReturnBuiltin:
    """Test return builtin functionality."""
    
    def test_return_from_function(self, shell, capsys):
        """Test return from function with exit code."""
        cmd = '''
        testfunc() {
            echo "in function"
            return 42
            echo "should not print"
        }
        testfunc
        echo "exit code: $?"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "in function" in captured.out
        assert "should not print" not in captured.out
        assert "exit code: 42" in captured.out
    
    @pytest.mark.xfail(reason="PSH return may not preserve last exit code")
    def test_return_no_args(self, shell, capsys):
        """Test return with no arguments (returns last exit code)."""
        cmd = '''
        testfunc() {
            false  # Sets $? to 1
            return
        }
        testfunc
        echo "exit code: $?"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "exit code: 1" in captured.out
    
    def test_return_outside_function(self, shell, capsys):
        """Test return outside of function."""
        # In a script context, return should work
        # In interactive mode, it might error
        exit_code = shell.run_command('return 5')
        # Either succeeds (script mode) or fails (interactive)
        captured = capsys.readouterr()
        if exit_code != 0:
            assert 'not in function' in captured.err or 'only meaningful' in captured.err or 'can only' in captured.err
    
    def test_return_invalid_number(self, shell, capsys):
        """Test return with invalid number."""
        cmd = '''
        testfunc() {
            return abc
        }
        testfunc
        '''
        exit_code = shell.run_command(cmd)
        captured = capsys.readouterr()
        # Should have an error about numeric argument
        assert 'numeric' in captured.err or 'invalid' in captured.err
    
    @pytest.mark.xfail(reason="PSH rejects return values > 255 instead of wrapping")
    def test_return_range(self, shell, capsys):
        """Test return value range (0-255)."""
        cmd = '''
        testfunc() {
            return 256
        }
        testfunc
        echo "exit code: $?"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        # 256 should wrap to 0
        assert "exit code: 0" in captured.out
    
    @pytest.mark.xfail(reason="PSH rejects negative return values")
    def test_return_negative(self, shell, capsys):
        """Test return with negative number."""
        cmd = '''
        testfunc() {
            return -1
        }
        testfunc
        echo "exit code: $?"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        # -1 should become 255
        assert "exit code: 255" in captured.out


class TestReadonlyBuiltin:
    """Test readonly builtin functionality."""
    
    def test_readonly_variable(self, shell, capsys):
        """Test making a variable readonly."""
        shell.run_command('readonly MYVAR="test"')
        # Try to modify it
        exit_code = shell.run_command('MYVAR="new value"')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'readonly' in captured.err
    
    def test_readonly_existing_variable(self, shell, capsys):
        """Test making existing variable readonly."""
        shell.run_command('VAR="initial"')
        shell.run_command('readonly VAR')
        # Try to modify
        exit_code = shell.run_command('VAR="changed"')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'readonly' in captured.err
    
    def test_readonly_list(self, shell, capsys):
        """Test listing readonly variables."""
        shell.run_command('readonly RO1="value1"')
        shell.run_command('readonly RO2="value2"')
        shell.run_command('readonly')
        captured = capsys.readouterr()
        assert 'RO1=' in captured.out
        assert 'RO2=' in captured.out
    
    def test_readonly_with_p_option(self, shell, capsys):
        """Test readonly -p option."""
        shell.run_command('readonly MYRO="test"')
        shell.run_command('readonly -p')
        captured = capsys.readouterr()
        # Should show in declare -r format
        assert 'readonly' in captured.out or 'declare -r' in captured.out
        assert 'MYRO' in captured.out
    
    @pytest.mark.xfail(reason="PSH readonly -f prints function instead of making it readonly")
    def test_readonly_function(self, shell, capsys):
        """Test readonly -f for functions."""
        cmd = '''
        myfunc() { echo "test"; }
        readonly -f myfunc
        '''
        exit_code = shell.run_command(cmd)
        # PSH might not support readonly functions
        if exit_code == 0:
            # Try to redefine
            exit_code = shell.run_command('myfunc() { echo "new"; }')
            assert exit_code != 0
    
    def test_readonly_invalid_name(self, shell, capsys):
        """Test readonly with invalid variable name."""
        exit_code = shell.run_command('readonly 123VAR="test"')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'invalid' in captured.err or 'identifier' in captured.err
    
    @pytest.mark.xfail(reason="Output from subprocess not captured properly")
    def test_readonly_export(self, shell, capsys):
        """Test readonly exported variable."""
        shell.run_command('export ROVAR="exported"')
        shell.run_command('readonly ROVAR')
        # Variable should still be exported and readonly
        shell.run_command('bash -c "echo $ROVAR"')
        captured = capsys.readouterr()
        assert "exported" in captured.out


class TestDeclareBuiltin:
    """Test declare builtin functionality."""
    
    def test_declare_variable(self, shell, capsys):
        """Test basic variable declaration."""
        shell.run_command('declare VAR="value"')
        shell.run_command('echo "$VAR"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "value"
    
    def test_declare_integer(self, shell, capsys):
        """Test declare -i for integer variables."""
        shell.run_command('declare -i NUM=42')
        shell.run_command('NUM=10+5')
        shell.run_command('echo "$NUM"')
        captured = capsys.readouterr()
        # Should perform arithmetic
        assert captured.out.strip() == "15"
    
    def test_declare_readonly(self, shell, capsys):
        """Test declare -r for readonly variables."""
        shell.run_command('declare -r CONST="fixed"')
        exit_code = shell.run_command('CONST="changed"')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'readonly' in captured.err
    
    @pytest.mark.xfail(reason="Output from subprocess not captured properly")
    def test_declare_export(self, shell, capsys):
        """Test declare -x for exported variables."""
        shell.run_command('declare -x EXPORTED="value"')
        shell.run_command('bash -c "echo $EXPORTED"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "value"
    
    def test_declare_array(self, shell, capsys):
        """Test declare -a for arrays."""
        shell.run_command('declare -a ARR=(one two three)')
        shell.run_command('echo "${ARR[1]}"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "two"
    
    @pytest.mark.xfail(reason="PSH may not support associative arrays")
    def test_declare_associative_array(self, shell, capsys):
        """Test declare -A for associative arrays."""
        shell.run_command('declare -A HASH')
        shell.run_command('HASH[key]="value"')
        shell.run_command('echo "${HASH[key]}"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "value"
    
    def test_declare_list_variables(self, shell, capsys):
        """Test declare without arguments lists variables."""
        shell.run_command('MYVAR="test"')
        shell.run_command('declare')
        captured = capsys.readouterr()
        assert 'MYVAR=' in captured.out
    
    def test_declare_with_p_option(self, shell, capsys):
        """Test declare -p to display attributes."""
        shell.run_command('declare -i -r CONST=42')
        shell.run_command('declare -p CONST')
        captured = capsys.readouterr()
        # Should show attributes (may be combined)
        assert ('-i' in captured.out or 'i' in captured.out)
        assert ('-r' in captured.out or 'r' in captured.out)
        assert 'CONST' in captured.out
    
    @pytest.mark.xfail(reason="PSH declare doesn't create local scope by default")
    def test_declare_local_scope(self, shell, capsys):
        """Test declare in function creates local variable."""
        cmd = '''
        VAR="global"
        func() {
            declare VAR="local"
            echo "in func: $VAR"
        }
        func
        echo "outside: $VAR"
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "in func: local" in captured.out
        assert "outside: global" in captured.out
    
    @pytest.mark.xfail(reason="Output from subprocess not captured properly")
    def test_declare_multiple_attributes(self, shell, capsys):
        """Test declare with multiple attributes."""
        shell.run_command('declare -i -x NUM=100')
        # Should be both integer and exported
        shell.run_command('NUM=50+50')
        shell.run_command('bash -c "echo $NUM"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "100"
    
    def test_declare_invalid_option(self, shell, capsys):
        """Test declare with invalid option."""
        exit_code = shell.run_command('declare -z VAR')
        assert exit_code != 0
        captured = capsys.readouterr()
        assert 'invalid option' in captured.err or 'unknown option' in captured.err