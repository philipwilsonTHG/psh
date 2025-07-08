"""
Unit tests for tilde expansion in PSH.

Tests cover:
- Basic home directory expansion (~)
- User home directory expansion (~user)
- Tilde in various positions
- Multiple tildes
- Tilde with paths
- Quoted tildes (no expansion)
- Special cases
"""

import pytest
import os
import pwd


class TestBasicTildeExpansion:
    """Test basic tilde expansion."""
    
    def test_simple_tilde(self, shell, capsys):
        """Test ~ expands to home directory."""
        shell.run_command('echo ~')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    def test_tilde_with_slash(self, shell, capsys):
        """Test ~/ expands correctly."""
        shell.run_command('echo ~/')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home + '/'
    
    def test_tilde_with_path(self, shell, capsys):
        """Test ~/path expansion."""
        shell.run_command('echo ~/Documents')
        captured = capsys.readouterr()
        expected = os.path.expanduser('~/Documents')
        assert captured.out.strip() == expected
    
    def test_tilde_in_variable(self, shell, capsys):
        """Test tilde expansion in variable assignment."""
        shell.run_command('DIR=~')
        shell.run_command('echo "$DIR"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    @pytest.mark.xfail(reason="PSH doesn't support ~+ expansion")
    def test_tilde_plus(self, shell, capsys):
        """Test ~+ (current directory)."""
        shell.run_command('echo ~+')
        captured = capsys.readouterr()
        # Should expand to PWD
        cwd = os.getcwd()
        assert captured.out.strip() == cwd
    
    @pytest.mark.xfail(reason="PSH doesn't support ~- expansion")
    def test_tilde_minus(self, shell, capsys):
        """Test ~- (previous directory)."""
        # Set up OLDPWD
        shell.run_command('cd /tmp')
        shell.run_command('cd -')  # This should set OLDPWD
        shell.run_command('echo ~-')
        captured = capsys.readouterr()
        # Should expand to OLDPWD
        assert "/tmp" in captured.out


class TestUserTildeExpansion:
    """Test ~username expansion."""
    
    def test_current_user(self, shell, capsys):
        """Test ~username for current user."""
        # Get current username
        import getpass
        username = getpass.getuser()
        
        shell.run_command(f'echo ~{username}')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    def test_valid_user(self, shell, capsys):
        """Test ~username for valid user."""
        # Try to find a valid username
        try:
            # Get first user from passwd
            users = pwd.getpwall()
            if users:
                test_user = users[0].pw_name
                test_home = users[0].pw_dir
                
                shell.run_command(f'echo ~{test_user}')
                captured = capsys.readouterr()
                # Should expand to that user's home
                assert test_home in captured.out
        except:
            pytest.skip("Cannot access user database")
    
    def test_invalid_user(self, shell, capsys):
        """Test ~username for invalid user."""
        shell.run_command('echo ~nonexistentuser12345')
        captured = capsys.readouterr()
        # Should not expand
        assert captured.out.strip() == "~nonexistentuser12345"


class TestTildePosition:
    """Test tilde expansion in different positions."""
    
    def test_tilde_at_start(self, shell, capsys):
        """Test tilde only expands at start of word."""
        shell.run_command('echo ~/dir')
        captured = capsys.readouterr()
        assert captured.out.strip().startswith(os.path.expanduser('~'))
        
        shell.run_command('echo dir/~')
        captured = capsys.readouterr()
        # Should not expand
        assert captured.out.strip() == "dir/~"
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde after colon")
    def test_tilde_after_colon(self, shell, capsys):
        """Test tilde expansion after colon (PATH-like)."""
        shell.run_command('echo PATH=/bin:~/bin:/usr/bin')
        captured = capsys.readouterr()
        # Tilde after colon should expand
        home = os.path.expanduser('~')
        assert f":{home}/bin:" in captured.out
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde after equals")
    def test_tilde_after_equals(self, shell, capsys):
        """Test tilde expansion after equals."""
        shell.run_command('echo VAR=~')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert f"VAR={home}" in captured.out
    
    def test_multiple_tildes(self, shell, capsys):
        """Test multiple tildes in one command."""
        shell.run_command('echo ~ ~/dir ~')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        parts = captured.out.strip().split()
        assert parts[0] == home
        assert parts[1] == f"{home}/dir"
        assert parts[2] == home


class TestTildeQuoting:
    """Test tilde expansion with quotes."""
    
    def test_single_quoted_tilde(self, shell, capsys):
        """Test tilde in single quotes (no expansion)."""
        shell.run_command("echo '~'")
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
        
        shell.run_command("echo '~/dir'")
        captured = capsys.readouterr()
        assert captured.out.strip() == "~/dir"
    
    def test_double_quoted_tilde(self, shell, capsys):
        """Test tilde in double quotes (no expansion)."""
        shell.run_command('echo "~"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
        
        shell.run_command('echo "~/dir"')
        captured = capsys.readouterr()
        assert captured.out.strip() == "~/dir"
    
    def test_escaped_tilde(self, shell, capsys):
        """Test escaped tilde."""
        shell.run_command('echo \\~')
        captured = capsys.readouterr()
        assert captured.out.strip() == "~"
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde when part of word is quoted")
    def test_partial_quoting(self, shell, capsys):
        """Test partial quoting with tilde."""
        shell.run_command('echo ~/"my dir"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == f'{home}/my dir'


class TestTildeInContext:
    """Test tilde expansion in various contexts."""
    
    def test_tilde_in_cd(self, shell, capsys):
        """Test tilde expansion with cd command."""
        shell.run_command('cd ~')
        shell.run_command('pwd')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    def test_tilde_in_assignment(self, shell, capsys):
        """Test tilde in variable assignment."""
        shell.run_command('MYDIR=~/test')
        shell.run_command('echo "$MYDIR"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == f"{home}/test"
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde in array contexts")
    def test_tilde_in_array(self, shell, capsys):
        """Test tilde in array assignment."""
        shell.run_command('dirs=(~ ~/bin ~/lib)')
        shell.run_command('echo "${dirs[0]}"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde in for loop contexts")
    def test_tilde_in_for_loop(self, shell, capsys):
        """Test tilde in for loop."""
        cmd = '''
        for dir in ~ ~/test; do
            echo "Dir: $dir"
        done
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert f"Dir: {home}" in captured.out
        assert f"Dir: {home}/test" in captured.out
    
    @pytest.mark.xfail(reason="PSH doesn't expand tilde in case patterns")
    def test_tilde_in_case(self, shell, capsys):
        """Test tilde in case pattern."""
        cmd = '''
        FILE=~/test.txt
        case "$FILE" in
            ~/*) echo "Home path" ;;
            *) echo "Other path" ;;
        esac
        '''
        shell.run_command(cmd)
        captured = capsys.readouterr()
        assert "Home path" in captured.out


class TestTildeEdgeCases:
    """Test edge cases in tilde expansion."""
    
    def test_tilde_only_in_assignment(self, shell, capsys):
        """Test VAR=~ assignment."""
        shell.run_command('VAR=~')
        shell.run_command('echo "$VAR"')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == home
    
    def test_empty_tilde_user(self, shell, capsys):
        """Test ~/ with no username."""
        shell.run_command('echo ~/')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        assert captured.out.strip() == f"{home}/"
    
    def test_tilde_with_spaces(self, shell, capsys):
        """Test tilde with spaces around it."""
        shell.run_command('echo ~ /other')
        captured = capsys.readouterr()
        home = os.path.expanduser('~')
        parts = captured.out.strip().split()
        assert parts[0] == home
        assert parts[1] == "/other"
    
    def test_tilde_in_glob(self, shell, capsys):
        """Test tilde with glob patterns."""
        # This is tricky - tilde should expand before globbing
        shell.run_command('echo ~/.*')
        captured = capsys.readouterr()
        # Should expand ~ then glob for hidden files
        home = os.path.expanduser('~')
        output = captured.out.strip()
        # Should find some hidden files in home
        assert home in output or f"{home}/" in output


@pytest.mark.xfail(reason="PSH doesn't support ~+/~- expansion")
class TestTildeWithPWD:
    """Test tilde expansion with PWD variables."""
    
    def test_tilde_plus_pwd(self, shell, capsys):
        """Test ~+ expands to PWD."""
        shell.run_command('cd /tmp')
        shell.run_command('echo ~+')
        captured = capsys.readouterr()
        assert captured.out.strip() == "/tmp"
        
        shell.run_command('cd /usr')
        shell.run_command('echo ~+')
        captured = capsys.readouterr()
        assert captured.out.strip() == "/usr"
    
    def test_tilde_minus_oldpwd(self, shell, capsys):
        """Test ~- expands to OLDPWD."""
        # Navigate to set OLDPWD
        original = os.getcwd()
        shell.run_command('cd /tmp')
        shell.run_command('cd /usr')
        shell.run_command('echo ~-')
        captured = capsys.readouterr()
        assert captured.out.strip() == "/tmp"
        
        # Return to original directory
        shell.run_command(f'cd {original}')
    
    def test_tilde_when_pwd_unset(self, shell, capsys):
        """Test ~+ when PWD is unset."""
        shell.run_command('unset PWD')
        shell.run_command('echo ~+')
        captured = capsys.readouterr()
        # Should still work (fallback to getcwd)
        assert len(captured.out.strip()) > 0