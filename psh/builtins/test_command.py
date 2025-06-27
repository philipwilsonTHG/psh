"""Test command builtin for conditionals."""
import os
import stat
import sys
from typing import List, TYPE_CHECKING

from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class TestBuiltin(Builtin):
    """Test command for conditionals."""
    
    @property
    def name(self) -> str:
        return "test"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the test builtin."""
        # Remove 'test' from args
        test_args = args[1:]
        return self._evaluate_test(test_args)
    
    def _evaluate_test(self, args: List[str]) -> int:
        """Evaluate test expression."""
        if len(args) == 0:
            return 1  # False
        
        # Check for leading ! (negation)
        negate = False
        if args[0] == '!':
            negate = True
            args = args[1:]  # Remove the !
            if len(args) == 0:
                return 1  # ! with no args is false
        
        # Evaluate the expression
        result = self._evaluate_expression(args)
        
        # Apply negation if needed
        if negate:
            result = 0 if result != 0 else 1
        
        return result
    
    def _evaluate_expression(self, args: List[str]) -> int:
        """Evaluate test expression without negation."""
        if len(args) == 0:
            return 1  # False
        
        if len(args) == 1:
            # Single argument - true if non-empty string
            return 0 if args[0] else 1
        
        if len(args) == 2:
            # Unary operators
            op, arg = args
            return self._evaluate_unary(op, arg)
        
        if len(args) == 3:
            # Binary operators
            arg1, op, arg2 = args
            return self._evaluate_binary(arg1, op, arg2)
        
        # More complex expressions not implemented yet
        return 2
    
    def _evaluate_unary(self, op: str, arg: str) -> int:
        """Evaluate unary operators."""
        if op == '-z':
            # True if string is empty
            return 0 if not arg else 1
        elif op == '-n':
            # True if string is non-empty
            return 0 if arg else 1
        elif op == '-f':
            # True if file exists and is regular file
            return 0 if os.path.isfile(arg) else 1
        elif op == '-d':
            # True if file exists and is directory
            return 0 if os.path.isdir(arg) else 1
        elif op == '-e':
            # True if file exists
            return 0 if os.path.exists(arg) else 1
        elif op == '-r':
            # True if file is readable
            return 0 if os.path.isfile(arg) and os.access(arg, os.R_OK) else 1
        elif op == '-w':
            # True if file is writable
            return 0 if os.path.isfile(arg) and os.access(arg, os.W_OK) else 1
        elif op == '-x':
            # True if file is executable
            return 0 if os.path.isfile(arg) and os.access(arg, os.X_OK) else 1
        elif op == '-s':
            # True if file exists and has size > 0
            try:
                return 0 if os.path.isfile(arg) and os.path.getsize(arg) > 0 else 1
            except (OSError, IOError):
                return 1
        elif op == '-L' or op == '-h':
            # True if file exists and is a symbolic link
            return 0 if os.path.islink(arg) else 1
        elif op == '-b':
            # True if file exists and is a block device
            try:
                st = os.stat(arg)
                return 0 if stat.S_ISBLK(st.st_mode) else 1
            except (OSError, IOError):
                return 1
        elif op == '-c':
            # True if file exists and is a character device
            try:
                st = os.stat(arg)
                return 0 if stat.S_ISCHR(st.st_mode) else 1
            except (OSError, IOError):
                return 1
        elif op == '-p':
            # True if file exists and is a named pipe (FIFO)
            try:
                st = os.stat(arg)
                return 0 if stat.S_ISFIFO(st.st_mode) else 1
            except (OSError, IOError):
                return 1
        elif op == '-S':
            # True if file exists and is a socket
            try:
                st = os.stat(arg)
                return 0 if stat.S_ISSOCK(st.st_mode) else 1
            except (OSError, IOError):
                return 1
        elif op == '-k':
            # True if file has sticky bit set
            try:
                st = os.stat(arg)
                return 0 if st.st_mode & stat.S_ISVTX else 1
            except (OSError, IOError):
                return 1
        elif op == '-u':
            # True if file has setuid bit set
            try:
                st = os.stat(arg)
                return 0 if st.st_mode & stat.S_ISUID else 1
            except (OSError, IOError):
                return 1
        elif op == '-g':
            # True if file has setgid bit set
            try:
                st = os.stat(arg)
                return 0 if st.st_mode & stat.S_ISGID else 1
            except (OSError, IOError):
                return 1
        elif op == '-O':
            # True if file is owned by effective user ID
            try:
                st = os.stat(arg)
                return 0 if st.st_uid == os.geteuid() else 1
            except (OSError, IOError):
                return 1
        elif op == '-G':
            # True if file is owned by effective group ID
            try:
                st = os.stat(arg)
                return 0 if st.st_gid == os.getegid() else 1
            except (OSError, IOError):
                return 1
        elif op == '-N':
            # True if file was modified since it was last read
            try:
                st = os.stat(arg)
                return 0 if st.st_mtime > st.st_atime else 1
            except (OSError, IOError):
                return 1
        elif op == '-t':
            # True if file descriptor is open and refers to a terminal
            try:
                fd = int(arg)
                return 0 if os.isatty(fd) else 1
            except (ValueError, OSError):
                return 1
        elif op == '-v':
            # True if variable is set (bash nameref support)
            # This requires access to shell state to check variables
            # For now, we'll need to handle this specially in the shell
            return 2  # Indicate special handling needed
        else:
            return 2  # Unknown operator
    
    def _evaluate_binary(self, arg1: str, op: str, arg2: str) -> int:
        """Evaluate binary operators."""
        if op == '=':
            return 0 if arg1 == arg2 else 1
        elif op == '!=':
            return 0 if arg1 != arg2 else 1
        elif op == '-eq':
            try:
                return 0 if int(arg1) == int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-ne':
            try:
                return 0 if int(arg1) != int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-lt':
            try:
                return 0 if int(arg1) < int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-le':
            try:
                return 0 if int(arg1) <= int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-gt':
            try:
                return 0 if int(arg1) > int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-ge':
            try:
                return 0 if int(arg1) >= int(arg2) else 1
            except ValueError:
                return 2
        elif op == '-nt':
            # True if file1 is newer than file2 (modification time)
            try:
                stat1 = os.stat(arg1)
                stat2 = os.stat(arg2)
                return 0 if stat1.st_mtime > stat2.st_mtime else 1
            except (OSError, IOError):
                return 1
        elif op == '-ot':
            # True if file1 is older than file2 (modification time)
            try:
                stat1 = os.stat(arg1)
                stat2 = os.stat(arg2)
                return 0 if stat1.st_mtime < stat2.st_mtime else 1
            except (OSError, IOError):
                return 1
        elif op == '-ef':
            # True if file1 and file2 refer to the same file (same device and inode)
            try:
                stat1 = os.stat(arg1)
                stat2 = os.stat(arg2)
                return 0 if (stat1.st_dev == stat2.st_dev and stat1.st_ino == stat2.st_ino) else 1
            except (OSError, IOError):
                return 1
        else:
            return 2  # Unknown operator


@builtin
class BracketBuiltin(Builtin):
    """[ command (alias for test)."""
    
    @property
    def name(self) -> str:
        return "["
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Execute the [ builtin."""
        # For [ command, last argument must be ]
        if len(args) < 2 or args[-1] != ']':
            return 2  # Syntax error
        
        # Remove [ and ], then evaluate as test
        test_args = args[1:-1]
        test_builtin = TestBuiltin()
        return test_builtin._evaluate_test(test_args)