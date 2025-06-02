#!/usr/bin/env python3
"""Test multi-line command detection."""

import sys
from pathlib import Path

# Add psh to path
sys.path.insert(0, str(Path(__file__).parent))

from psh.multiline_handler import MultiLineInputHandler
from psh.shell import Shell
from psh.line_editor import LineEditor
from unittest.mock import Mock

def test_multiline_detection():
    """Test multi-line command detection logic."""
    shell = Shell()
    line_editor = Mock(spec=LineEditor)
    handler = MultiLineInputHandler(line_editor, shell)
    
    # Test cases: (command, is_complete)
    test_cases = [
        # Simple commands
        ("echo hello", True),
        ("ls -la", True),
        ("", True),
        ("   ", True),
        
        # Line continuation
        ("echo hello \\", False),
        ("echo \\", False), 
        ("echo hello \\\\", True),  # Escaped backslash
        
        # Unclosed quotes
        ('echo "hello', False),
        ("echo 'hello", False),
        ('echo "hello"', True),
        ("echo 'hello'", True),
        
        # If statements
        ("if true", False),
        ("if true; then", False),
        ("if true; then\necho hello", False),
        ("if true; then echo hello; fi", True),
        ("if true; then\necho hello\nfi", True),
        
        # While loops
        ("while true", False),
        ("while true; do", False),
        ("while true; do\necho hello", False),
        ("while true; do echo hello; done", True),
        
        # For loops
        ("for i in 1 2 3", False),
        ("for i in 1 2 3; do", False),
        ("for i in 1 2 3; do echo $i; done", True),
        
        # Functions
        ("hello() {", False),
        ("hello() {\necho hello", False),
        ("hello() { echo hello; }", True),
        
        # Case statements
        ("case $x in", False),
        ("case $x in\n1)", False),
        ("case $x in\n1) echo one;;\nesac", True),
        
        # Heredocs
        ("cat <<EOF", False),
        ("cat <<EOF\nline1", False),
        ("cat <<EOF\nline1\nEOF", True),
        ("cat <<-EOF", False),
        ("cat <<-EOF\n\tline1\nEOF", True),
        ("cat <<'EOF'", False),
        ("cat <<'EOF'\nline\nEOF", True),
    ]
    
    print("Testing command completion detection:")
    for command, expected_complete in test_cases:
        result = handler._is_complete_command(command)
        status = "✓" if result == expected_complete else "✗"
        display_cmd = repr(command)
        if len(display_cmd) > 50:
            display_cmd = display_cmd[:47] + "..."
        print(f"{status} {display_cmd:50} -> {'complete' if result else 'incomplete':10} (expected {'complete' if expected_complete else 'incomplete'})")

if __name__ == "__main__":
    test_multiline_detection()