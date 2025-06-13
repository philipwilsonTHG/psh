#!/usr/bin/env python3
"""
Proof of concept for multi-line command support in psh.

This example shows how to integrate multi-line editing with the existing
psh architecture without modifying the core LineEditor class.
"""

import re
from typing import Optional, List
from psh.state_machine_lexer import tokenize
from psh.token_types import TokenType
from psh.parser import parse, ParseError


class MultiLineInputHandler:
    """Handles multi-line command input for interactive mode."""
    
    def __init__(self, line_editor, shell):
        self.line_editor = line_editor
        self.shell = shell
        self.buffer: List[str] = []
        self.in_heredoc = False
        self.heredoc_delimiter = None
        self.heredoc_indent = False  # For <<- style
        
    def read_command(self) -> Optional[str]:
        """Read a complete command, possibly spanning multiple lines."""
        self.buffer = []
        
        while True:
            # Determine prompt
            prompt = self._get_prompt()
            
            # Read one line
            line = self.line_editor.read_line(prompt)
            if line is None:  # EOF
                if self.buffer:
                    print("\npsh: syntax error: unexpected end of file")
                    self.reset()
                return None
            
            # Add line to buffer
            self.buffer.append(line)
            
            # Check if we're in a heredoc
            if self.in_heredoc:
                if self._is_heredoc_end(line):
                    self.in_heredoc = False
                    self.heredoc_delimiter = None
                continue
            else:
                # Check for new heredoc
                delimiter = self._detect_heredoc(line)
                if delimiter:
                    self.in_heredoc = True
                    self.heredoc_delimiter = delimiter
                    continue
            
            # Check if command is complete
            full_command = '\n'.join(self.buffer)
            if self._is_complete_command(full_command):
                self.reset()
                return full_command
    
    def reset(self):
        """Reset multi-line state."""
        self.buffer = []
        self.in_heredoc = False
        self.heredoc_delimiter = None
        self.heredoc_indent = False
    
    def _get_prompt(self) -> str:
        """Get the appropriate prompt based on current state."""
        if not self.buffer:
            # Primary prompt
            ps1 = self.shell.variables.get('PS1', 'psh$ ')
            return self.shell.expand_prompt(ps1)
        else:
            # Continuation prompt
            ps2 = self.shell.variables.get('PS2', '> ')
            return self.shell.expand_prompt(ps2)
    
    def _detect_heredoc(self, line: str) -> Optional[str]:
        """Detect heredoc in line and return delimiter if found."""
        # Match << or <<- followed by optional quotes and delimiter
        match = re.search(r'<<(-?)\s*([\'"]?)(\w+)\2', line)
        if match:
            self.heredoc_indent = bool(match.group(1))  # True if <<-
            return match.group(3)
        return None
    
    def _is_heredoc_end(self, line: str) -> bool:
        """Check if line ends the current heredoc."""
        if not self.heredoc_delimiter:
            return False
        
        check_line = line
        if self.heredoc_indent:
            # <<- strips leading tabs
            check_line = line.lstrip('\t')
        
        return check_line.rstrip('\n') == self.heredoc_delimiter
    
    def _is_complete_command(self, command: str) -> bool:
        """Check if command is syntactically complete."""
        if not command.strip():
            return True
        
        # Check for explicit line continuation
        if self._has_line_continuation(command):
            return False
        
        # Try to tokenize and parse
        try:
            tokens = tokenize(command)
            if not tokens:
                return True
            
            # Try parsing
            parse(tokens)
            return True
            
        except SyntaxError as e:
            # Unterminated string or other tokenization error
            if "Unterminated" in str(e):
                return False
            # Other tokenization errors are complete but invalid
            return True
            
        except ParseError as e:
            # Check for incomplete constructs
            error_msg = str(e)
            incomplete_patterns = [
                "Expected DO",
                "Expected DONE", 
                "Expected FI",
                "Expected ELSE",
                "Expected THEN",
                "Expected ESAC",
                "Expected closing",
                "Unexpected EOF"
            ]
            
            for pattern in incomplete_patterns:
                if pattern in error_msg:
                    return False
            
            # Other parse errors mean command is complete but invalid
            return True
    
    def _has_line_continuation(self, command: str) -> bool:
        """Check if command ends with line continuation."""
        lines = command.split('\n')
        if not lines:
            return False
        
        # Check if last line ends with backslash (not escaped)
        last_line = lines[-1].rstrip()
        if last_line.endswith('\\'):
            # Count preceding backslashes
            count = 0
            for i in range(len(last_line) - 2, -1, -1):
                if last_line[i] == '\\':
                    count += 1
                else:
                    break
            # Odd number means the last backslash is not escaped
            return count % 2 == 0
        
        return False


def demo_prompt_expansion(shell):
    """Demo of prompt expansion capabilities."""
    import pwd
    import socket
    import time
    import os
    
    def expand_prompt(prompt_string: str) -> str:
        """Expand prompt escape sequences."""
        if not prompt_string:
            return ''
        
        # Get user info
        try:
            username = pwd.getpwuid(os.getuid()).pw_name
        except:
            username = 'user'
        
        # Get hostname
        try:
            hostname = socket.gethostname().split('.')[0]
        except:
            hostname = 'localhost'
        
        # Basic expansions
        expansions = {
            '\\u': username,
            '\\h': hostname,
            '\\H': socket.getfqdn(),
            '\\w': os.getcwd().replace(os.path.expanduser('~'), '~'),
            '\\W': os.path.basename(os.getcwd()) or '/',
            '\\$': '#' if os.getuid() == 0 else '$',
            '\\n': '\n',
            '\\t': time.strftime('%H:%M:%S'),
            '\\d': time.strftime('%a %b %d'),
            '\\!': str(len(shell.history) + 1),
            '\\?': str(shell.last_exit_code),
            '\\\\': '\\',  # Literal backslash
        }
        
        result = prompt_string
        for escape, value in expansions.items():
            result = result.replace(escape, value)
        
        return result
    
    # Example prompts
    examples = [
        ('\\u@\\h:\\w\\$ ', "Classic bash prompt"),
        ('[\\t] \\u@\\h:\\W\\$ ', "With timestamp"),
        '\\w\\n\\$ ', "Two-line prompt",
        'psh[\\?]\\$ ', "With exit status",
        '\\! \\$ ', "With history number",
    ]
    
    print("Prompt Expansion Examples:")
    print("-" * 50)
    for prompt, description in examples:
        expanded = expand_prompt(prompt)
        print(f"{description}:")
        print(f"  PS1='{prompt}'")
        print(f"  Result: {repr(expanded)}")
        print()


if __name__ == "__main__":
    # Demo the concepts
    print("Multi-line Command Support Architecture Demo")
    print("=" * 50)
    print()
    
    # Show incomplete detection examples
    print("Incomplete Command Detection Examples:")
    print("-" * 50)
    
    test_cases = [
        ("if true; then", False, "Missing 'fi'"),
        ("if true; then echo hi; fi", True, "Complete if statement"),
        ("while true; do", False, "Missing 'done'"),
        ('echo "unterminated', False, "Unterminated string"),
        ("echo hello \\", False, "Line continuation"),
        ("{ echo hello", False, "Missing closing brace"),
        ("case $x in", False, "Missing 'esac'"),
        ("cat << EOF", False, "Heredoc not terminated"),
    ]
    
    handler = type('obj', (object,), {
        'shell': type('obj', (object,), {'history': [], 'last_exit_code': 0})(),
        'buffer': [],
        'in_heredoc': False,
        'heredoc_delimiter': None
    })()
    
    for command, expected_complete, description in test_cases:
        handler.__class__ = MultiLineInputHandler
        is_complete = handler._is_complete_command(handler, command)
        status = "✓" if is_complete == expected_complete else "✗"
        print(f"{status} {description}: {repr(command)}")
        print(f"  Complete: {is_complete}")
    
    print()
    print("Prompt Expansion Demo:")
    print("=" * 50)
    mock_shell = type('obj', (object,), {
        'history': ['cmd1', 'cmd2', 'cmd3'],
        'last_exit_code': 0
    })()
    demo_prompt_expansion(mock_shell)