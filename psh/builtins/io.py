"""I/O related builtins (echo, pwd)."""

import os
import sys
from typing import List, TYPE_CHECKING
from .base import Builtin
from .registry import builtin

if TYPE_CHECKING:
    from ..shell import Shell


@builtin
class EchoBuiltin(Builtin):
    """Echo arguments to stdout."""
    
    @property
    def name(self) -> str:
        return "echo"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Echo arguments to stdout."""
        # Check for -e flag
        interpret_escapes = False
        start_idx = 1
        
        if len(args) > 1 and args[1] == '-e':
            interpret_escapes = True
            start_idx = 2
        
        # Join remaining arguments
        if len(args) > start_idx:
            output = ' '.join(args[start_idx:])
        else:
            output = ''
        
        # Process escape sequences if -e flag is present
        if interpret_escapes:
            # Replace common escape sequences
            output = output.replace('\\n', '\n')
            output = output.replace('\\t', '\t')
            output = output.replace('\\r', '\r')
            output = output.replace('\\b', '\b')
            output = output.replace('\\f', '\f')
            output = output.replace('\\a', '\a')
            output = output.replace('\\v', '\v')
            output = output.replace('\\\\', '\\')
            # Handle octal sequences \nnn
            import re
            def replace_octal(match):
                octal_str = match.group(1)
                try:
                    return chr(int(octal_str, 8))
                except ValueError:
                    return match.group(0)
            output = re.sub(r'\\([0-7]{1,3})', replace_octal, output)
        
        # Check if we're in a child process (forked for pipeline/background)
        # In child processes after fork, we need to write to fd 1 directly
        # because shell.stdout still points to the original stdout
        if hasattr(shell, '_in_forked_child') and shell._in_forked_child:
            # Write directly to file descriptor in child process
            os.write(1, (output + '\n').encode())
        else:
            # Use normal print in parent process to respect redirections
            print(output, file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
        return 0
    
    @property
    def help(self) -> str:
        return """echo: echo [-e] [arg ...]
    
    Display arguments separated by spaces, followed by a newline.
    If no arguments are given, print a blank line.
    
    Options:
        -e    Enable interpretation of backslash escape sequences:
              \\n  newline       \\t  tab
              \\r  carriage return  \\b  backspace
              \\f  form feed     \\a  alert (bell)
              \\v  vertical tab  \\\\  backslash
              \\nnn  character with octal value nnn"""


@builtin
class PwdBuiltin(Builtin):
    """Print working directory."""
    
    @property
    def name(self) -> str:
        return "pwd"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Print the current working directory."""
        try:
            cwd = os.getcwd()
            # Check if we're in a child process (forked for pipeline/background)
            if hasattr(shell, '_in_forked_child') and shell._in_forked_child:
                # Write directly to file descriptor in child process
                os.write(1, (cwd + '\n').encode())
            else:
                # Use normal print in parent process to respect redirections
                print(cwd, file=shell.stdout if hasattr(shell, 'stdout') else sys.stdout)
            return 0
        except OSError as e:
            self.error(str(e), shell)
            return 1
    
    @property
    def help(self) -> str:
        return """pwd: pwd
    
    Print the current working directory."""