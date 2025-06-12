"""I/O related builtins (echo, pwd)."""

import os
import sys
import re
from typing import List, Tuple, TYPE_CHECKING
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
        # Debug: log arguments
        # print(f"DEBUG: echo args = {args}", file=sys.stderr)
        
        # Parse flags
        suppress_newline, interpret_escapes, start_idx = self._parse_flags(args)
        
        # Get output text
        output = ' '.join(args[start_idx:]) if len(args) > start_idx else ''
        
        
        # Process escape sequences if needed
        if interpret_escapes:
            output, terminate = self._process_escapes(output)
            if terminate:
                suppress_newline = True
        
        # Write output
        self._write_output(output, suppress_newline, shell)
        return 0
    
    def _parse_flags(self, args: List[str]) -> Tuple[bool, bool, int]:
        """Parse echo flags and return (suppress_newline, interpret_escapes, start_index)."""
        suppress_newline = False
        interpret_escapes = False
        arg_index = 1
        
        while arg_index < len(args):
            arg = args[arg_index]
            if arg == '--':
                arg_index += 1
                break
            elif arg.startswith('-') and len(arg) > 1 and all(c in 'neE' for c in arg[1:]):
                # Process flag characters
                for flag in arg[1:]:
                    if flag == 'n':
                        suppress_newline = True
                    elif flag == 'e':
                        interpret_escapes = True
                    elif flag == 'E':
                        interpret_escapes = False
                arg_index += 1
            else:
                # Not a flag, stop parsing
                break
        
        return suppress_newline, interpret_escapes, arg_index
    
    def _process_escapes(self, text: str) -> Tuple[str, bool]:
        """Process escape sequences. Returns (processed_text, terminate_output)."""
        # Check for \c first (terminates output)
        if '\\c' in text:
            text = text[:text.index('\\c')]
            return text, True
        
        # First, protect double backslashes by replacing them temporarily
        # Use a placeholder that won't appear in normal text
        text = text.replace('\\\\', '\x01BACKSLASH\x01')
        
        # Process escape sequences
        # Use a function to handle replacements to avoid conflicts
        replacements = [
            ('\\n', '\n'),
            ('\\t', '\t'),
            ('\\r', '\r'),
            ('\\b', '\b'),
            ('\\f', '\f'),
            ('\\a', '\a'),
            ('\\v', '\v'),
            ('\\e', '\x1b'),  # Escape character
            ('\\E', '\x1b'),  # Escape character (alternative)
        ]
        
        # Apply simple replacements
        for old, new in replacements:
            text = text.replace(old, new)
        
        # Handle hex sequences \xhh
        def replace_hex(match):
            hex_str = match.group(1)
            try:
                return chr(int(hex_str, 16))
            except ValueError:
                return match.group(0)
        text = re.sub(r'\\x([0-9a-fA-F]{1,2})', replace_hex, text)
        
        # Handle unicode sequences \uhhhh
        def replace_unicode4(match):
            hex_str = match.group(1)
            try:
                return chr(int(hex_str, 16))
            except ValueError:
                return match.group(0)
        text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode4, text)
        
        # Handle unicode sequences \Uhhhhhhhh
        def replace_unicode8(match):
            hex_str = match.group(1)
            try:
                return chr(int(hex_str, 16))
            except ValueError:
                return match.group(0)
        text = re.sub(r'\\U([0-9a-fA-F]{8})', replace_unicode8, text)
        
        # Handle octal sequences \nnn
        def replace_octal(match):
            octal_str = match.group(1)
            try:
                value = int(octal_str, 8)
                if value <= 255:  # Octal values should be in byte range
                    return chr(value)
                else:
                    return match.group(0)
            except ValueError:
                return match.group(0)
        # Match \0nnn format (with explicit 0) - up to 3 octal digits after \0
        # or \nnn where n starts with 0-3 (for values 0-255 in octal)
        text = re.sub(r'\\(0[0-7]{1,3}|[0-3][0-7]{2})', replace_octal, text)
        
        # Finally restore protected backslashes
        text = text.replace('\x01BACKSLASH\x01', '\\')
        
        return text, False
    
    def _write_output(self, text: str, suppress_newline: bool, shell: 'Shell'):
        """Write output to appropriate file descriptor."""
        # Add newline if not suppressed
        if not suppress_newline:
            text += '\n'
        
        # Check if we're in a child process (forked for pipeline/background)
        if hasattr(shell, '_in_forked_child') and shell._in_forked_child:
            # In child process, write directly to fd 1
            output_bytes = text.encode('utf-8', errors='replace')
            os.write(1, output_bytes)
        else:
            # In parent process, use shell.stdout to respect redirections
            output = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            output.write(text)
            output.flush()
    
    @property
    def help(self) -> str:
        return """echo: echo [-neE] [arg ...]
    
    Display arguments separated by spaces, followed by a newline.
    If no arguments are given, print a blank line.
    
    Options:
        -n    Do not output the trailing newline
        -e    Enable interpretation of backslash escape sequences
        -E    Disable interpretation of backslash escapes (default)
    
    Escape sequences (with -e):
        \\a    Alert (bell)
        \\b    Backspace
        \\c    Suppress further output
        \\e    Escape character
        \\f    Form feed
        \\n    New line
        \\r    Carriage return
        \\t    Horizontal tab
        \\v    Vertical tab
        \\\\    Backslash
        \\0nnn Character with octal value nnn (0 prefix required)
        \\xhh  Character with hex value hh (1 to 2 digits)
        \\uhhhh    Unicode character with hex value hhhh (4 digits)
        \\Uhhhhhhhh Unicode character with hex value hhhhhhhh (8 digits)"""


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