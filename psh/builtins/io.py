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
    
    @property
    def synopsis(self) -> str:
        return "echo [-neE] [arg ...]"
    
    @property
    def description(self) -> str:
        return "Display text"
    
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
        
        # DEBUG: Log output method
        if shell.state.options.get('debug-exec'):
            print(f"DEBUG EchoBuiltin: _in_forked_child={getattr(shell.state, '_in_forked_child', False)}", file=sys.stderr)
            print(f"DEBUG EchoBuiltin: shell.stdout={getattr(shell, 'stdout', 'N/A')}", file=sys.stderr)
            print(f"DEBUG EchoBuiltin: shell.state.stdout={getattr(shell.state, 'stdout', 'N/A')}", file=sys.stderr)
            print(f"DEBUG EchoBuiltin: sys.stdout={sys.stdout}", file=sys.stderr)
            print(f"DEBUG EchoBuiltin: Writing text: {repr(text[:50])}", file=sys.stderr)
        
        # Check if we're in a child process (forked for pipeline/background)
        if hasattr(shell.state, '_in_forked_child') and shell.state._in_forked_child:
            # In child process, write directly to fd 1
            output_bytes = text.encode('utf-8', errors='replace')
            os.write(1, output_bytes)
        else:
            # In parent process, use shell.stdout to respect redirections
            output = shell.stdout if hasattr(shell, 'stdout') else sys.stdout
            # DEBUG: Log actual output stream
            if shell.state.options.get('debug-exec'):
                print(f"DEBUG EchoBuiltin: Using output stream: {output}", file=sys.stderr)
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
class PrintfBuiltin(Builtin):
    """Format and print data."""
    
    @property
    def name(self) -> str:
        return "printf"
    
    @property
    def synopsis(self) -> str:
        return "printf format [arguments ...]"
    
    @property
    def description(self) -> str:
        return "Format and print data according to the format string"
    
    def execute(self, args: List[str], shell: 'Shell') -> int:
        """Format and print data according to the format string."""
        if len(args) < 2:
            self.error("usage: printf format [arguments ...]", shell)
            return 2
        
        format_str = args[1]
        arguments = args[2:]
        
        
        try:
            # Handle the most common case needed for array sorting: %s\n
            # Note: format_str might be '%s\\n' due to shell escaping
            if format_str == '%s\n' or format_str == '%s\\n':
                # Simple case: print each argument on a new line
                for arg in arguments:
                    self._write_output(arg + '\n', shell)
            else:
                # For other format strings, we need to cycle through arguments
                # if format specifiers exceed available arguments
                output = self._process_format_string(format_str, arguments)
                self._write_output(output, shell)
            
            return 0
        except Exception as e:
            self.error(f"printf: {str(e)}", shell)
            return 1
    
    def _process_format_string(self, format_str: str, arguments: list) -> str:
        """Process a format string with arguments."""
        result = []
        arg_index = 0
        i = 0
        
        while i < len(format_str):
            if format_str[i] == '%' and i + 1 < len(format_str):
                if format_str[i + 1] == '%':
                    # Literal %
                    result.append('%')
                    i += 2
                elif format_str[i + 1] == 's':
                    # String format
                    if arg_index < len(arguments):
                        result.append(arguments[arg_index])
                        arg_index += 1
                    else:
                        result.append('')  # No more arguments
                    i += 2
                elif format_str[i + 1] == 'd':
                    # Integer format
                    if arg_index < len(arguments):
                        try:
                            value = int(arguments[arg_index])
                            result.append(str(value))
                        except ValueError:
                            result.append('0')  # Default for invalid numbers
                        arg_index += 1
                    else:
                        result.append('0')  # No more arguments
                    i += 2
                elif format_str[i + 1] == 'c':
                    # Character format
                    if arg_index < len(arguments):
                        arg = arguments[arg_index]
                        if arg:
                            result.append(arg[0])  # First character
                        else:
                            result.append('')
                        arg_index += 1
                    else:
                        result.append('')  # No more arguments
                    i += 2
                else:
                    # Unknown format specifier, treat as literal
                    result.append(format_str[i])
                    i += 1
            elif format_str[i] == '\\' and i + 1 < len(format_str):
                # Handle escape sequences
                next_char = format_str[i + 1]
                if next_char == 'n':
                    result.append('\n')
                elif next_char == 't':
                    result.append('\t')
                elif next_char == 'r':
                    result.append('\r')
                elif next_char == '\\':
                    result.append('\\')
                else:
                    result.append(next_char)
                i += 2
            else:
                result.append(format_str[i])
                i += 1
        
        return ''.join(result)
    
    def _write_output(self, text: str, shell: 'Shell'):
        """Write output to appropriate file descriptor."""
        # Check if we're in a child process (forked for pipeline/background)
        if hasattr(shell.state, '_in_forked_child') and shell.state._in_forked_child:
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
        return """printf: printf format [arguments ...]
    
    Format and print data according to the format string.
    
    Format specifiers:
        %s    String
        %d    Integer
        %c    Character
        %%    Literal %
    
    Escape sequences:
        \\n    Newline
        \\t    Tab
        \\r    Carriage return
        \\\\    Backslash
    
    Exit Status:
    Returns 0 on success, 1 on format error, 2 on usage error."""


@builtin
class PwdBuiltin(Builtin):
    """Print working directory."""
    
    @property
    def name(self) -> str:
        return "pwd"
    
    @property
    def synopsis(self) -> str:
        return "pwd"
    
    @property
    def description(self) -> str:
        return "Print the current working directory"
    
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
    Print the current working directory.
    
    Display the full pathname of the current working directory.
    
    Exit Status:
    Returns 0 unless an error occurs while reading the pathname of the
    current directory."""